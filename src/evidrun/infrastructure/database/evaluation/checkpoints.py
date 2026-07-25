"""ContextSnapshots and CheckpointRecords.

A checkpoint is a derived summary anchored to a ledger position, not a second
source of truth: its boundary event must exist, its capture set must match the
definition exactly, and every ref it carries must belong to the same Run.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from sqlalchemy import select

from evidrun.contracts import CheckpointRecord, RunSpec, semantic_model_dump
from evidrun.infrastructure.database import clock
from evidrun.infrastructure.database.evidence_boundary import validate_evidence_boundary
from evidrun.infrastructure.database.models import (
    AdmissionRecordRow,
    CheckpointRecordRow,
    ContextSnapshotRow,
    EvaluationRecordRow,
    RunEventRow,
    RunRow,
    RunSpecRow,
)
from evidrun.infrastructure.database.queue.fencing import validate_optional_lease
from evidrun.infrastructure.database.unit_of_work import LeaseFence, UnitOfWork
from evidrun.shared.types import canonical_json, new_id, sha256_json

__all__ = ["CheckpointStore"]


class CheckpointStore:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self.unit_of_work = unit_of_work

    def save_snapshot(
        self,
        run_id: str,
        snapshot: Mapping[str, Any],
        *,
        lease: LeaseFence | None = None,
    ) -> ContextSnapshotRow:
        with self.unit_of_work.session() as session:
            validate_optional_lease(session, lease=lease, run_id=run_id)
            existing = session.scalar(
                select(ContextSnapshotRow).where(ContextSnapshotRow.run_id == run_id)
            )
            expected = {
                "policy_id": str(snapshot["policy_id"]),
                "strategy": str(snapshot["strategy"]),
                "max_chars": int(snapshot["max_chars"]),
                "source_chars": int(snapshot["source_chars"]),
                "selected_chars": int(snapshot["selected_chars"]),
                "selected_content": str(snapshot["selected_content"]),
                "omitted_json": canonical_json(snapshot["omitted"]),
                "content_hash": str(snapshot["content_hash"]),
            }
            if existing is not None:
                actual = {key: getattr(existing, key) for key in expected}
                if actual != expected:
                    raise ValueError("a different ContextSnapshot already exists for the Run")
                return existing
            row = ContextSnapshotRow(
                id=new_id("ctx"),
                run_id=run_id,
                created_at=clock.utc_now(),
                **expected,
            )
            session.add(row)
            session.commit()
        return row

    def save_checkpoint_record(self, record: CheckpointRecord) -> CheckpointRecordRow:
        validate_evidence_boundary(
            self.unit_of_work,
            run_id=record.run_id,
            sequence=record.up_to_event_sequence,
            event_hash=record.event_hash,
        )
        with self.unit_of_work.session() as session:
            run = session.get(RunRow, record.run_id)
            if run is None:
                raise KeyError(f"Run not found: {record.run_id}")
            if run.run_spec_id is None:
                raise ValueError("legacy Run does not have a checkpoint policy")
            spec_row = session.get(RunSpecRow, run.run_spec_id)
            if spec_row is None:
                raise ValueError("Run references a missing RunSpec")
            spec = RunSpec.model_validate(json.loads(spec_row.spec_json))
            if spec.checkpoint_policy_ref != record.policy_ref or spec.checkpoint_policy is None:
                raise ValueError("checkpoint policy does not belong to the RunSpec")
            definition = next(
                (
                    item
                    for item in spec.checkpoint_policy.definitions
                    if item.id == record.definition_id
                ),
                None,
            )
            if definition is None:
                raise ValueError("checkpoint definition does not belong to the RunSpec")
            if record.replayability == "deterministic":
                raise ValueError(
                    "deterministic checkpoint replayability is unsupported in this runtime"
                )
            expected_definition_digest = sha256_json(semantic_model_dump(definition))
            if record.definition_digest != expected_definition_digest:
                raise ValueError("checkpoint definition digest does not match the RunSpec")
            validation_refs = tuple(item.validator_ref for item in record.validations)
            if set(validation_refs) != set(definition.validator_refs) or len(
                validation_refs
            ) != len(definition.validator_refs):
                raise ValueError("checkpoint validations must match the definition validators")
            boundary_event = session.scalar(
                select(RunEventRow).where(
                    RunEventRow.run_id == record.run_id,
                    RunEventRow.sequence == record.up_to_event_sequence,
                )
            )
            if boundary_event is None:
                raise ValueError("checkpoint boundary event is missing")
            trigger = definition.trigger
            if trigger.kind == "event" and boundary_event.event_type != trigger.event_type:
                raise ValueError("checkpoint boundary does not satisfy its event trigger")
            if trigger.kind not in {"manual", "event"}:
                raise ValueError(
                    "checkpoint trigger is representable but unsupported by this runtime"
                )
            capture = definition.capture
            capture_pairs = (
                (capture.context_snapshot, bool(record.context_snapshot_refs), "context snapshot"),
                (capture.protocol_state, record.protocol_state_ref is not None, "protocol state"),
                (
                    capture.artifact_manifest,
                    record.artifact_manifest_ref is not None,
                    "artifact manifest",
                ),
                (
                    capture.workspace_snapshot,
                    record.workspace_snapshot_ref is not None,
                    "workspace snapshot",
                ),
                (
                    capture.evaluation_records,
                    bool(record.evaluation_record_refs),
                    "evaluation records",
                ),
            )
            for requested, present, label in capture_pairs:
                if requested != present:
                    raise ValueError(f"checkpoint {label} capture does not match its definition")
            admission_capture = capture.provider_resolution or capture.agent_inventory
            if admission_capture != (record.admission_record_id is not None):
                raise ValueError(
                    "checkpoint admission capture does not match provider/inventory request"
                )
            if record.admission_record_id is not None:
                admission_row = session.get(AdmissionRecordRow, record.admission_record_id)
                if (
                    admission_row is None
                    or admission_row.id != run.admission_id
                    or admission_row.digest != record.admission_record_digest
                ):
                    raise ValueError("checkpoint admission capture does not belong to the Run")
            for snapshot_id in record.context_snapshot_refs:
                snapshot = session.get(ContextSnapshotRow, snapshot_id)
                if snapshot is None or snapshot.run_id != record.run_id:
                    raise ValueError("checkpoint context snapshot does not belong to the Run")
            for evaluation_id in record.evaluation_record_refs:
                evaluation = session.get(EvaluationRecordRow, evaluation_id)
                if evaluation is None or evaluation.run_id != record.run_id:
                    raise ValueError("checkpoint evaluation record does not belong to the Run")
            existing = session.scalar(
                select(CheckpointRecordRow).where(
                    CheckpointRecordRow.checkpoint_hash == record.checkpoint_hash
                )
            )
            if existing is not None:
                return existing
            row = CheckpointRecordRow(
                id=record.checkpoint_id,
                run_id=record.run_id,
                definition_id=record.definition_id,
                up_to_event_sequence=record.up_to_event_sequence,
                record_json=canonical_json(semantic_model_dump(record)),
                checkpoint_hash=record.checkpoint_hash,
                created_at=record.created_at_utc,
            )
            session.add(row)
            session.commit()
            return row
