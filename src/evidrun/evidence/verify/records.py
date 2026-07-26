"""Validation of a single evaluation or checkpoint record against the ledger.

A record is only valid against the events that actually exist in the bundle, so both
validators read from a `LedgerIndex` built once per bundle. Evidence may never point
past the record's own boundary: that is what keeps an evaluation from citing an event
it could not have seen.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from evidrun.contracts import (
    CheckpointRecord,
    EvaluationRecord,
    EvaluationValidator,
    RunSpec,
    semantic_model_dump,
)
from evidrun.contracts.authoring import EvaluationStage
from evidrun.infrastructure.database.ledger.transitions import TERMINAL_EVENT_TYPES
from evidrun.shared.types import sha256_json

__all__ = [
    "HUMAN_SOURCE_TYPES",
    "TERMINAL_EVENT_TYPES",
    "LedgerIndex",
    "build_ledger_index",
    "checkpoint_record_valid",
    "evaluation_record_valid",
    "run_members",
    "strip",
]

HUMAN_SOURCE_TYPES = frozenset({"human_reviewer", "human_adjudicator"})


def run_members(run_id: str) -> set[str]:
    """The members every auditable bundle carries per Run, in both v2 and v3."""

    return {
        f"runs/{run_id}.json",
        f"events/{run_id}.jsonl",
        f"evaluations/{run_id}.json",
        f"checkpoints/{run_id}.json",
    }


@dataclass(frozen=True, slots=True)
class LedgerIndex:
    """Per-run views of the events and checkpoints a bundle carries.

    Built once from the archive and read by every record validator, so a record is
    always checked against the same ledger the bundle actually ships.
    """

    event_boundaries: dict[str, dict[int, str]]
    event_types: dict[str, dict[int, str]]
    event_sequences_by_id: dict[str, dict[str, int]]
    events_by_run: dict[str, list[dict[str, Any]]]
    checkpoint_ids: dict[str, set[str]]
    checkpoint_sequences: dict[str, dict[str, int]]
    checkpoint_definitions: dict[str, dict[str, str]]

    def event_hash(self, run_id: str, sequence: int) -> str | None:
        return self.event_boundaries.get(run_id, {}).get(sequence)

    def event_type(self, run_id: str, sequence: int) -> str | None:
        return self.event_types.get(run_id, {}).get(sequence)

    def checkpoint_sequence(self, run_id: str, checkpoint_id: str) -> int | None:
        return self.checkpoint_sequences.get(run_id, {}).get(checkpoint_id)

    def has_checkpoint(self, run_id: str, checkpoint_id: str) -> bool:
        return checkpoint_id in self.checkpoint_ids.get(run_id, set())

    def events(self, run_id: str) -> list[dict[str, Any]]:
        return self.events_by_run.get(run_id, [])

    def terminal_event(self, run_id: str) -> dict[str, Any] | None:
        events = self.events(run_id)
        return events[-1] if events else None


def strip(document: dict[str, Any], digest_field: str) -> dict[str, Any]:
    return {key: value for key, value in document.items() if key != digest_field}


def build_ledger_index(
    events_by_run: dict[str, list[dict[str, Any]]],
    checkpoints_by_run: dict[str, list[dict[str, Any]]],
) -> LedgerIndex:
    """Indexa eventos e checkpoints de todo run presente no bundle."""

    return LedgerIndex(
        events_by_run=events_by_run,
        event_boundaries={
            run_id: {int(event["sequence"]): str(event["event_hash"]) for event in events}
            for run_id, events in events_by_run.items()
        },
        event_types={
            run_id: {int(event["sequence"]): str(event["type"]) for event in events}
            for run_id, events in events_by_run.items()
        },
        event_sequences_by_id={
            run_id: {str(event["event_id"]): int(event["sequence"]) for event in events}
            for run_id, events in events_by_run.items()
        },
        checkpoint_ids={
            run_id: {str(item["checkpoint_id"]) for item in documents}
            for run_id, documents in checkpoints_by_run.items()
        },
        checkpoint_sequences={
            run_id: {
                str(item["checkpoint_id"]): int(item["up_to_event_sequence"])
                for item in documents
            }
            for run_id, documents in checkpoints_by_run.items()
        },
        checkpoint_definitions={
            run_id: {
                str(item["checkpoint_id"]): str(item["definition_id"]) for item in documents
            }
            for run_id, documents in checkpoints_by_run.items()
        },
    )


def evaluation_record_valid(
    document: dict[str, Any],
    *,
    run_id: str,
    spec: RunSpec | None,
    index: LedgerIndex,
    records_by_id: dict[str, dict[str, Any]],
) -> bool:
    expected = document["digest"]
    record = EvaluationRecord.model_validate(strip(document, "digest"))
    if (
        spec is None
        or record.digest != expected
        or record.run_id != run_id
        or record.plan_ref != spec.evaluation_plan_ref
    ):
        return False
    try:
        EvaluationValidator.validate(spec.evaluation_plan, record)
    except ValueError:
        return False
    if not _human_authority_valid(record, run_id=run_id, spec=spec, records_by_id=records_by_id):
        return False
    boundary = record.boundary
    if (
        boundary.up_to_event_sequence is not None
        and index.event_hash(run_id, boundary.up_to_event_sequence) != boundary.event_hash
    ):
        return False
    if boundary.checkpoint_id is not None and not index.has_checkpoint(
        run_id, boundary.checkpoint_id
    ):
        return False
    boundary_sequence = boundary.up_to_event_sequence
    if boundary.checkpoint_id is not None:
        boundary_sequence = index.checkpoint_sequence(run_id, boundary.checkpoint_id)
    if boundary_sequence is None:
        return False
    if record.source_type in HUMAN_SOURCE_TYPES and not _human_relation_boundary_valid(
        record,
        run_id=run_id,
        index=index,
        records_by_id=records_by_id,
        boundary_sequence=boundary_sequence,
    ):
        return False
    stage = next(item for item in spec.evaluation_plan.stages if item.id == record.stage_id)
    if not _trigger_valid(stage, record, run_id=run_id, index=index):
        return False
    return _evidence_within_boundary(
        record, run_id=run_id, index=index, boundary_sequence=boundary_sequence
    )


def _human_authority_valid(
    record: EvaluationRecord,
    *,
    run_id: str,
    spec: RunSpec,
    records_by_id: dict[str, dict[str, Any]],
) -> bool:
    """Human adjudication and review need declared authority, never an actor field."""

    if record.source_type == "human_adjudicator":
        policy = spec.evaluation_plan.human_adjudication_policy
        if (
            not policy.required
            or record.stage_id not in policy.adjudicable_stage_ids
            or record.evaluator_ref != policy.adjudicator_ref
            or record.human_attestation is None
            or record.human_attestation.verifier_ref != policy.attestation_verifier_ref
            or record.relation is None
            or record.relation.kind != "adjudicates"
        ):
            return False
        adjudications_for_stage = [
            item
            for item in records_by_id.values()
            if item.get("source_type") == "human_adjudicator"
            and item.get("stage_id") == record.stage_id
        ]
        if len(adjudications_for_stage) != 1:
            return False
        for target_ref in record.relation.target_record_refs:
            target_document = records_by_id.get(target_ref)
            if target_document is None:
                return False
            target = EvaluationRecord.model_validate(strip(target_document, "digest"))
            if (
                target.run_id != run_id
                or target.plan_ref != record.plan_ref
                or target.stage_id != record.stage_id
            ):
                return False
    if record.source_type == "human_reviewer":
        if record.relation is None or record.relation.kind != "independent_review":
            return False
        for considered_ref in record.relation.considers_record_refs:
            considered = records_by_id.get(considered_ref)
            if considered is None or considered.get("run_id") != run_id:
                return False
    return True


def _human_relation_boundary_valid(
    record: EvaluationRecord,
    *,
    run_id: str,
    index: LedgerIndex,
    records_by_id: dict[str, dict[str, Any]],
    boundary_sequence: int,
) -> bool:
    relation = record.relation
    if relation is None:
        return False
    related_refs = (
        relation.target_record_refs
        if relation.kind == "adjudicates"
        else relation.considers_record_refs
    )
    related_records: list[tuple[EvaluationRecord, int]] = []
    for related_ref in related_refs:
        related_document = records_by_id.get(related_ref)
        if related_document is None:
            return False
        related_record = EvaluationRecord.model_validate(strip(related_document, "digest"))
        related_sequence = related_record.boundary.up_to_event_sequence
        if related_record.boundary.checkpoint_id is not None:
            related_sequence = index.checkpoint_sequence(
                run_id, related_record.boundary.checkpoint_id
            )
        if related_sequence is None:
            return False
        related_records.append((related_record, related_sequence))
    try:
        EvaluationValidator.validate_human_relation_boundary(
            record,
            boundary_sequence=boundary_sequence,
            related_records=related_records,
        )
    except ValueError:
        return False
    return True


def _trigger_valid(
    stage: EvaluationStage, record: EvaluationRecord, *, run_id: str, index: LedgerIndex
) -> bool:
    """The record boundary must match the stage's declared trigger."""

    boundary = record.boundary
    sequence = boundary.up_to_event_sequence
    if stage.trigger.kind == "event":
        return (
            sequence is not None
            and index.event_type(run_id, sequence) == stage.trigger.reference
        )
    if stage.trigger.kind == "checkpoint":
        return boundary.checkpoint_id is not None and (
            stage.trigger.reference is None
            or index.checkpoint_definitions.get(run_id, {}).get(boundary.checkpoint_id)
            == stage.trigger.reference
        )
    if stage.trigger.kind == "run_terminal":
        return sequence is not None and index.event_type(run_id, sequence) in TERMINAL_EVENT_TYPES
    return True


def _evidence_within_boundary(
    record: EvaluationRecord, *, run_id: str, index: LedgerIndex, boundary_sequence: int
) -> bool:
    """Evidence points at this Run and never past the boundary being evaluated."""

    for dimension in record.dimension_values:
        for evidence_ref in dimension.evidence_refs:
            scheme, target = evidence_ref.ref.split(":", 1)
            if scheme == "run" and target != run_id:
                return False
            if scheme == "event":
                sequence = index.event_sequences_by_id.get(run_id, {}).get(target)
                if sequence is None or sequence > boundary_sequence:
                    return False
    return True


def checkpoint_record_valid(
    document: dict[str, Any],
    *,
    run_id: str,
    spec: RunSpec | None,
    index: LedgerIndex,
) -> bool:
    expected = document["checkpoint_hash"]
    record = CheckpointRecord.model_validate(strip(document, "checkpoint_hash"))
    if (
        spec is None
        or spec.checkpoint_policy is None
        or spec.checkpoint_policy_ref != record.policy_ref
    ):
        return False
    definition = next(
        (item for item in spec.checkpoint_policy.definitions if item.id == record.definition_id),
        None,
    )
    if (
        definition is None
        or record.definition_digest != sha256_json(semantic_model_dump(definition))
        or set(item.validator_ref for item in record.validations)
        != set(definition.validator_refs)
    ):
        return False
    capture = definition.capture
    captures_match = all(
        requested == present
        for requested, present in (
            (capture.context_snapshot, bool(record.context_snapshot_refs)),
            (capture.protocol_state, record.protocol_state_ref is not None),
            (capture.artifact_manifest, record.artifact_manifest_ref is not None),
            (capture.workspace_snapshot, record.workspace_snapshot_ref is not None),
            (capture.evaluation_records, bool(record.evaluation_record_refs)),
            (
                capture.provider_resolution or capture.agent_inventory,
                record.admission_record_id is not None,
            ),
        )
    )
    trigger = definition.trigger
    if trigger.kind == "event" and (
        index.event_type(run_id, record.up_to_event_sequence) != trigger.event_type
    ):
        return False
    if trigger.kind not in {"manual", "event"}:
        return False
    return (
        captures_match
        and record.replayability != "deterministic"
        and record.checkpoint_hash == expected
        and record.run_id == run_id
        and index.event_hash(run_id, record.up_to_event_sequence) == record.event_hash
    )
