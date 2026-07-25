"""EvaluationRecords and their Grade projection.

Records are append-only: a correction creates a new record, never an in-place
edit. A human-sourced record has its attestation verified before the persisting
transaction opens, so an unverifiable one never reaches a write. Inside that
transaction, `save_deterministic_evaluation` commits the record, the Grade
projection and the `evaluation.completed` event together.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select

from evidrun.contracts import (
    CheckpointRecord,
    EvaluationRecord,
    EvaluationValidator,
    RunSpec,
    semantic_model_dump,
)
from evidrun.contracts.authoring import EvaluationStage
from evidrun.contracts.authority import HumanAttestationVerifier
from evidrun.infrastructure.database import clock
from evidrun.infrastructure.database.evidence_boundary import (
    validate_evaluation_boundary,
    validate_evidence_boundary,
)
from evidrun.infrastructure.database.ledger.appender import append_event_once_in_session
from evidrun.infrastructure.database.ledger.transitions import TERMINAL_EVENT_TYPES
from evidrun.infrastructure.database.models import (
    CheckpointRecordRow,
    EvaluationRecordRow,
    GradeRow,
    RunEventRow,
    RunRow,
    RunSpecRow,
)
from evidrun.infrastructure.database.queue.fencing import validate_optional_lease
from evidrun.infrastructure.database.unit_of_work import LeaseFence, UnitOfWork
from evidrun.shared.types import canonical_json, new_id

__all__ = ["EvaluationStore"]


class EvaluationStore:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
        human_attestation_verifier: HumanAttestationVerifier,
    ) -> None:
        self.unit_of_work = unit_of_work
        self.human_attestation_verifier = human_attestation_verifier

    def save_grade(
        self,
        *,
        run_id: str,
        grader_id: str,
        score: float,
        passed: bool,
        rationale: str,
        evidence: Sequence[str],
        lease: LeaseFence | None = None,
    ) -> GradeRow:
        with self.unit_of_work.session() as session:
            validate_optional_lease(session, lease=lease, run_id=run_id)
            existing = session.scalar(
                select(GradeRow).where(GradeRow.run_id == run_id, GradeRow.grader_id == grader_id)
            )
            evidence_json = canonical_json(list(evidence))
            if existing is not None:
                if (
                    existing.score != score
                    or existing.passed != passed
                    or existing.rationale != rationale
                    or existing.evidence_json != evidence_json
                ):
                    raise ValueError("a different Grade already exists for this Run/grader")
                return existing
            row = GradeRow(
                id=new_id("grade"),
                run_id=run_id,
                grader_id=grader_id,
                score=score,
                passed=passed,
                rationale=rationale,
                evidence_json=evidence_json,
                created_at=clock.utc_now(),
            )
            session.add(row)
            session.commit()
        return row

    def save_evaluation_record(
        self,
        record: EvaluationRecord,
        *,
        lease: LeaseFence | None = None,
    ) -> EvaluationRecordRow:
        with self.unit_of_work.session() as session:
            validate_optional_lease(session, lease=lease, run_id=record.run_id)
            existing = session.scalar(
                select(EvaluationRecordRow).where(
                    EvaluationRecordRow.run_id == record.run_id,
                    EvaluationRecordRow.stage_id == record.stage_id,
                    EvaluationRecordRow.source_type == record.source_type,
                )
            )
            if existing is not None:
                if existing.id != record.record_id or existing.record_digest != record.digest:
                    raise ValueError(
                        "evaluation stage already has a different record from this source type"
                    )
                return existing
        if record.source_type in {"human_reviewer", "human_adjudicator"}:
            if record.human_attestation is None:
                raise ValueError("human evaluation requires attestation evidence")
            self.human_attestation_verifier.verify(
                record.human_attestation,
                expected_subject_digest=record.human_subject_digest(),
            )
        validate_evaluation_boundary(self.unit_of_work, record)
        validate_evidence_boundary(
            self.unit_of_work,
            run_id=record.run_id,
            sequence=record.boundary.up_to_event_sequence,
            event_hash=record.boundary.event_hash,
        )
        with self.unit_of_work.session() as session:
            validate_optional_lease(session, lease=lease, run_id=record.run_id)
            run = session.get(RunRow, record.run_id)
            if run is None:
                raise KeyError(f"Run not found: {record.run_id}")
            if run.run_spec_id is None:
                raise ValueError("legacy Run does not have an EvaluationPlanRevision")
            spec_row = session.get(RunSpecRow, run.run_spec_id)
            if spec_row is None:
                raise ValueError("Run references a missing RunSpec")
            spec = RunSpec.model_validate(json.loads(spec_row.spec_json))
            if spec.evaluation_plan_ref != record.plan_ref:
                raise ValueError("evaluation plan does not belong to the RunSpec")
            EvaluationValidator.validate(spec.evaluation_plan, record)
            stage = next(item for item in spec.evaluation_plan.stages if item.id == record.stage_id)
            max_evidence_sequence = _validate_trigger_boundary(session, record=record, stage=stage)
            _validate_evidence_refs(
                session, record=record, max_evidence_sequence=max_evidence_sequence
            )
            existing = session.scalar(
                select(EvaluationRecordRow).where(
                    EvaluationRecordRow.record_digest == record.digest
                )
            )
            if existing is not None:
                return existing
            related_records = _collect_related_records(session, record=record, spec=spec)
            EvaluationValidator.validate_human_relation_boundary(
                record,
                boundary_sequence=max_evidence_sequence,
                related_records=related_records,
            )
            _validate_stage_availability(session, record=record, spec=spec)
            row = EvaluationRecordRow(
                id=record.record_id,
                run_id=record.run_id,
                source_type=record.source_type,
                stage_id=record.stage_id,
                record_json=canonical_json(semantic_model_dump(record)),
                record_digest=record.digest,
                created_at=record.created_at_utc,
            )
            session.add(row)
            session.commit()
            return row

    def save_deterministic_evaluation(
        self,
        *,
        record: EvaluationRecord,
        score: float,
        passed: bool,
        rationale: str,
        evidence: Sequence[str],
        lease: LeaseFence,
    ) -> EvaluationRecordRow:
        """Persist the built-in evaluation, Grade projection and event atomically."""

        if record.source_type != "deterministic_grader":
            raise ValueError("atomic built-in evaluation requires a deterministic grader")
        evidence_json = canonical_json(list(evidence))
        with self.unit_of_work.session() as session:
            validate_optional_lease(session, lease=lease, run_id=record.run_id)
            run = session.get(RunRow, record.run_id)
            if run is None or run.run_spec_id is None or run.status != "evaluating":
                raise ValueError("deterministic evaluation requires an evaluating Run")
            spec_row = session.get(RunSpecRow, run.run_spec_id)
            if spec_row is None:
                raise ValueError("Run references a missing RunSpec")
            spec = RunSpec.model_validate(json.loads(spec_row.spec_json))
            if spec.digest != spec_row.digest or spec.evaluation_plan_ref != record.plan_ref:
                raise ValueError("evaluation plan does not belong to the RunSpec")
            EvaluationValidator.validate(spec.evaluation_plan, record)
            if record.boundary.up_to_event_sequence is None:
                raise ValueError("deterministic evaluation requires an event boundary")
            boundary = session.scalar(
                select(RunEventRow).where(
                    RunEventRow.run_id == record.run_id,
                    RunEventRow.sequence == record.boundary.up_to_event_sequence,
                )
            )
            stage = next(item for item in spec.evaluation_plan.stages if item.id == record.stage_id)
            if (
                boundary is None
                or boundary.event_hash != record.boundary.event_hash
                or stage.trigger.kind != "event"
                or boundary.event_type != stage.trigger.reference
            ):
                raise ValueError("evaluation boundary does not satisfy its event trigger")
            _validate_evidence_refs(
                session, record=record, max_evidence_sequence=boundary.sequence
            )

            evaluation_row = _upsert_deterministic_record(session, record=record)
            _upsert_grade(
                session,
                record=record,
                score=score,
                passed=passed,
                rationale=rationale,
                evidence_json=evidence_json,
            )

            append_event_once_in_session(
                session,
                run=run,
                event_type="evaluation.completed",
                payload={
                    "evaluation_record_id": record.record_id,
                    "evaluation_record_digest": record.digest,
                    "gate_status": record.gate_status,
                },
                operation_key=f"evaluation:{record.stage_id}:completed",
                allowed_statuses={"evaluating"},
            )
            session.commit()
            return evaluation_row


def _validate_trigger_boundary(
    session: Any, *, record: EvaluationRecord, stage: EvaluationStage
) -> int:
    """Check the boundary satisfies the stage trigger; return the evidence ceiling."""
    boundary_event: RunEventRow | None = None
    boundary_checkpoint: CheckpointRecordRow | None = None
    if record.boundary.up_to_event_sequence is not None:
        boundary_event = session.scalar(
            select(RunEventRow).where(
                RunEventRow.run_id == record.run_id,
                RunEventRow.sequence == record.boundary.up_to_event_sequence,
            )
        )
    if record.boundary.checkpoint_id is not None:
        boundary_checkpoint = session.get(CheckpointRecordRow, record.boundary.checkpoint_id)
    if stage.trigger.kind == "event":
        if boundary_event is None or boundary_event.event_type != stage.trigger.reference:
            raise ValueError("evaluation boundary does not satisfy its event trigger")
    elif stage.trigger.kind == "checkpoint":
        if boundary_checkpoint is None:
            raise ValueError("evaluation checkpoint trigger requires a checkpoint boundary")
        if stage.trigger.reference is not None:
            checkpoint = CheckpointRecord.model_validate(
                json.loads(boundary_checkpoint.record_json)
            )
            if checkpoint.definition_id != stage.trigger.reference:
                raise ValueError("evaluation boundary does not satisfy its checkpoint trigger")
    elif stage.trigger.kind == "run_terminal" and (
        boundary_event is None or boundary_event.event_type not in TERMINAL_EVENT_TYPES
    ):
        raise ValueError("run-terminal evaluation requires a terminal event boundary")
    return (
        boundary_event.sequence
        if boundary_event is not None
        else boundary_checkpoint.up_to_event_sequence
        if boundary_checkpoint is not None
        else 0
    )


def _validate_evidence_refs(
    session: Any, *, record: EvaluationRecord, max_evidence_sequence: int
) -> None:
    """No dimension may cite evidence from another Run or past its boundary."""
    for dimension in record.dimension_values:
        for evidence_ref in dimension.evidence_refs:
            scheme, target = evidence_ref.ref.split(":", 1)
            if scheme == "run" and target != record.run_id:
                raise ValueError("evaluation evidence references a different Run")
            if scheme == "event":
                evidence_event = session.get(RunEventRow, target)
                if (
                    evidence_event is None
                    or evidence_event.run_id != record.run_id
                    or evidence_event.sequence > max_evidence_sequence
                ):
                    raise ValueError(
                        "evaluation evidence event is outside its authorized boundary"
                    )


def _collect_related_records(
    session: Any, *, record: EvaluationRecord, spec: RunSpec
) -> list[tuple[EvaluationRecord, int]]:
    """Resolve the records a human adjudication or review is allowed to build on."""
    related_records: list[tuple[EvaluationRecord, int]] = []

    def related_boundary_sequence(related: EvaluationRecord) -> int:
        if related.boundary.up_to_event_sequence is not None:
            return related.boundary.up_to_event_sequence
        checkpoint_id = related.boundary.checkpoint_id
        checkpoint = (
            session.get(CheckpointRecordRow, checkpoint_id) if checkpoint_id is not None else None
        )
        if checkpoint is None or checkpoint.run_id != record.run_id:
            raise ValueError("related evaluation record has an unverifiable boundary")
        return checkpoint.up_to_event_sequence

    if record.source_type == "human_adjudicator":
        if record.relation is None or record.relation.kind != "adjudicates":
            raise ValueError("human adjudication requires explicit target records")
        adjudication_policy = spec.evaluation_plan.human_adjudication_policy
        if (
            not adjudication_policy.required
            or record.stage_id not in adjudication_policy.adjudicable_stage_ids
            or record.evaluator_ref != adjudication_policy.adjudicator_ref
            or record.human_attestation is None
            or record.human_attestation.verifier_ref
            != adjudication_policy.attestation_verifier_ref
        ):
            raise ValueError("human adjudication is not authorized by the EvaluationPlan")
        for target_ref in record.relation.target_record_refs:
            target = session.get(EvaluationRecordRow, target_ref)
            if target is None or target.run_id != record.run_id:
                raise ValueError("human adjudication target must belong to the same Run")
            target_record = EvaluationRecord.model_validate(json.loads(target.record_json))
            if (
                target_record.plan_ref != record.plan_ref
                or target_record.stage_id != record.stage_id
            ):
                raise ValueError("human adjudication target must use the same plan and stage")
            related_records.append((target_record, related_boundary_sequence(target_record)))
    if record.source_type == "human_reviewer":
        if record.relation is None or record.relation.kind != "independent_review":
            raise ValueError("human review requires an independent review relation")
        for considered_ref in record.relation.considers_record_refs:
            considered = session.get(EvaluationRecordRow, considered_ref)
            if considered is None or considered.run_id != record.run_id:
                raise ValueError("human review can only consider records from the same Run")
            considered_record = EvaluationRecord.model_validate(json.loads(considered.record_json))
            related_records.append(
                (considered_record, related_boundary_sequence(considered_record))
            )
    return related_records


def _validate_stage_availability(
    session: Any, *, record: EvaluationRecord, spec: RunSpec
) -> None:
    """A stage behind a failed hard gate, or already recorded, accepts nothing new."""
    prior_rows = list(
        session.scalars(
            select(EvaluationRecordRow)
            .where(EvaluationRecordRow.run_id == record.run_id)
            .order_by(EvaluationRecordRow.id)
        )
    )
    prior_records = [
        EvaluationRecord.model_validate(json.loads(prior.record_json)) for prior in prior_rows
    ]
    if record.source_type == "human_adjudicator" and any(
        prior.stage_id == record.stage_id and prior.source_type == "human_adjudicator"
        for prior in prior_records
    ):
        raise ValueError("v1 permits only one human adjudication per stage")
    prior_gate_results = EvaluationValidator.gate_results(spec.evaluation_plan, prior_records)
    visible_stages = EvaluationValidator.stages_visible_after_gates(
        spec.evaluation_plan, prior_gate_results
    )
    if record.stage_id not in visible_stages:
        raise ValueError("evaluation stage is blocked by a failed hard gate")
    if record.source_type != "human_adjudicator" and any(
        prior.stage_id == record.stage_id and prior.source_type == record.source_type
        for prior in prior_rows
    ):
        raise ValueError("evaluation stage already has a record from this source type")


def _upsert_deterministic_record(session: Any, *, record: EvaluationRecord) -> EvaluationRecordRow:
    """Insert the record, or return the identical one already stored for this stage."""
    evaluation_row = session.scalar(
        select(EvaluationRecordRow).where(
            EvaluationRecordRow.run_id == record.run_id,
            EvaluationRecordRow.stage_id == record.stage_id,
            EvaluationRecordRow.source_type == record.source_type,
        )
    )
    if evaluation_row is None:
        evaluation_row = EvaluationRecordRow(
            id=record.record_id,
            run_id=record.run_id,
            source_type=record.source_type,
            stage_id=record.stage_id,
            record_json=canonical_json(semantic_model_dump(record)),
            record_digest=record.digest,
            created_at=record.created_at_utc,
        )
        session.add(evaluation_row)
        session.flush()
    elif (
        evaluation_row.id != record.record_id
        or evaluation_row.record_digest != record.digest
        or evaluation_row.record_json != canonical_json(semantic_model_dump(record))
    ):
        raise ValueError("evaluation stage already has a different deterministic record")
    return evaluation_row


def _upsert_grade(
    session: Any,
    *,
    record: EvaluationRecord,
    score: float,
    passed: bool,
    rationale: str,
    evidence_json: str,
) -> None:
    """Write the Grade projection, refusing to overwrite a different one."""
    grade = session.scalar(
        select(GradeRow).where(
            GradeRow.run_id == record.run_id,
            GradeRow.grader_id == record.stage_id,
        )
    )
    if grade is None:
        session.add(
            GradeRow(
                id=new_id("grade"),
                run_id=record.run_id,
                grader_id=record.stage_id,
                score=score,
                passed=passed,
                rationale=rationale,
                evidence_json=evidence_json,
                created_at=clock.utc_now(),
            )
        )
    elif (
        grade.score != score
        or grade.passed != passed
        or grade.rationale != rationale
        or grade.evidence_json != evidence_json
    ):
        raise ValueError("a different Grade already exists for this Run/grader")
