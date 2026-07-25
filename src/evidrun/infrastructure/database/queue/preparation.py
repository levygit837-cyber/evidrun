"""Publishing the prepared Run boundary in one fenced transaction.

ContextSnapshot, SubjectEnvelope and the four preparation events
(`run.preparing`, `context.composed`, `capability.offered`, `run.running`) commit
together under the caller's lease fence. Splitting this into separate
transactions would let a crash leave a Run that is `running` without the envelope
the Subject was supposed to receive.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from sqlalchemy import select

from evidrun.contracts import (
    AdmissionRecord,
    RunSpec,
    SubjectEnvelope,
    SubjectEnvelopeRecord,
    semantic_model_dump,
)
from evidrun.infrastructure.database import clock
from evidrun.infrastructure.database.ledger.appender import append_event_once_in_session
from evidrun.infrastructure.database.models import (
    AdmissionRecordRow,
    ContextSnapshotRow,
    RunRow,
    RunSpecRow,
    SubjectEnvelopeRow,
)
from evidrun.infrastructure.database.queue.fencing import validate_optional_lease
from evidrun.infrastructure.database.timestamps import aware_utc
from evidrun.infrastructure.database.unit_of_work import LeaseFence, UnitOfWork
from evidrun.shared.types import canonical_json, new_id

__all__ = ["PreparationStore"]


class PreparationStore:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self.unit_of_work = unit_of_work

    def prepare_run_execution(
        self,
        *,
        run_id: str,
        spec: RunSpec,
        admission: AdmissionRecord,
        snapshot: Mapping[str, Any],
        envelope: SubjectEnvelope,
        lease: LeaseFence,
    ) -> tuple[ContextSnapshotRow, SubjectEnvelopeRecord]:
        """Publish the complete prepared Run boundary in one fenced transaction."""

        prepared_at = clock.utc_now()
        expected_snapshot = {
            "policy_id": str(snapshot["policy_id"]),
            "strategy": str(snapshot["strategy"]),
            "max_chars": int(snapshot["max_chars"]),
            "source_chars": int(snapshot["source_chars"]),
            "selected_chars": int(snapshot["selected_chars"]),
            "selected_content": str(snapshot["selected_content"]),
            "omitted_json": canonical_json(snapshot["omitted"]),
            "content_hash": str(snapshot["content_hash"]),
        }
        with self.unit_of_work.session() as session:
            validate_optional_lease(session, lease=lease, run_id=run_id)
            run = _load_prepared_run(
                session, run_id=run_id, spec=spec, admission=admission, envelope=envelope
            )

            snapshot_row = _upsert_context_snapshot(
                session, run_id=run_id, expected=expected_snapshot, prepared_at=prepared_at
            )
            envelope_row = _upsert_subject_envelope(
                session, run_id=run_id, envelope=envelope, prepared_at=prepared_at
            )

            _append_preparation_events(
                session,
                run=run,
                spec=spec,
                envelope=envelope,
                snapshot=snapshot,
                snapshot_id=snapshot_row.id,
                expected_snapshot=expected_snapshot,
            )
            run.context_hash = str(expected_snapshot["content_hash"])
            session.commit()
            return snapshot_row, SubjectEnvelopeRecord(
                run_id=run_id,
                envelope=envelope,
                created_at_utc=aware_utc(envelope_row.created_at),
            )


def _load_prepared_run(
    session: Any,
    *,
    run_id: str,
    spec: RunSpec,
    admission: AdmissionRecord,
    envelope: SubjectEnvelope,
) -> RunRow:
    """Every contract the prepared boundary rests on must match exactly."""
    run = session.get(RunRow, run_id)
    if run is None or run.run_spec_id is None or run.admission_id is None:
        raise ValueError("prepared Run requires canonical contracts")
    spec_row = session.get(RunSpecRow, run.run_spec_id)
    admission_row = session.get(AdmissionRecordRow, run.admission_id)
    if (
        spec_row is None
        or admission_row is None
        or spec_row.digest != spec.digest
        or admission_row.digest != admission.digest
        or admission.run_spec_digest != spec.digest
        or admission.decision != "admitted"
        or envelope.run_spec_digest != spec.digest
    ):
        raise ValueError("prepared Run contracts are not exact")
    return run


def _upsert_context_snapshot(
    session: Any, *, run_id: str, expected: Mapping[str, Any], prepared_at: datetime
) -> ContextSnapshotRow:
    """Idempotent: a replay must find the identical snapshot, never overwrite one."""
    snapshot_row = session.scalar(
        select(ContextSnapshotRow).where(ContextSnapshotRow.run_id == run_id)
    )
    if snapshot_row is None:
        snapshot_row = ContextSnapshotRow(
            id=new_id("ctx"),
            run_id=run_id,
            created_at=prepared_at,
            **expected,
        )
        session.add(snapshot_row)
        session.flush()
    elif {key: getattr(snapshot_row, key) for key in expected} != expected:
        raise ValueError("a different ContextSnapshot already exists for the Run")
    return snapshot_row


def _upsert_subject_envelope(
    session: Any, *, run_id: str, envelope: SubjectEnvelope, prepared_at: datetime
) -> SubjectEnvelopeRow:
    """The Subject sees one envelope per Run; a divergent one is a hard error."""
    envelope_row = session.get(SubjectEnvelopeRow, run_id)
    envelope_json = canonical_json(semantic_model_dump(envelope))
    if envelope_row is None:
        envelope_row = SubjectEnvelopeRow(
            run_id=run_id,
            envelope_json=envelope_json,
            digest=envelope.digest,
            created_at=prepared_at,
        )
        session.add(envelope_row)
    elif envelope_row.envelope_json != envelope_json or envelope_row.digest != envelope.digest:
        raise ValueError("a different SubjectEnvelope already exists for the Run")
    return envelope_row


def _append_preparation_events(
    session: Any,
    *,
    run: RunRow,
    spec: RunSpec,
    envelope: SubjectEnvelope,
    snapshot: Mapping[str, Any],
    snapshot_id: str,
    expected_snapshot: Mapping[str, Any],
) -> None:
    """The four facts that make a Run runnable, in ledger order, uncommitted."""
    append_event_once_in_session(
        session,
        run=run,
        event_type="run.preparing",
        payload={"scenario_ref": spec.scenario_ref.model_dump(mode="json")},
        operation_key="run:preparing",
        allowed_statuses={"queued"},
        next_status="preparing",
    )
    append_event_once_in_session(
        session,
        run=run,
        event_type="context.composed",
        payload={
            "snapshot_id": snapshot_id,
            "policy_id": expected_snapshot["policy_id"],
            "strategy": expected_snapshot["strategy"],
            "source_chars": expected_snapshot["source_chars"],
            "selected_chars": expected_snapshot["selected_chars"],
            "omitted": bool(snapshot["omitted"]),
            "content_hash": expected_snapshot["content_hash"],
        },
        operation_key="context:composed",
        allowed_statuses={"preparing"},
    )
    for capability in envelope.effective_capabilities:
        if capability.resolved_ref is None:
            raise ValueError("SubjectEnvelope contains an unresolved effective capability")
        append_event_once_in_session(
            session,
            run=run,
            event_type="capability.offered",
            payload={
                "capability_ref": capability.resolved_ref.model_dump(mode="json"),
                "required": capability.required,
                "exposure": capability.exposure,
                "effective_permissions": capability.effective_permissions,
            },
            operation_key=(
                "capability:"
                f"{capability.resolved_ref.namespace}:"
                f"{capability.resolved_ref.name}:"
                f"{capability.resolved_ref.version}:offered"
            ),
            allowed_statuses={"preparing"},
        )
    append_event_once_in_session(
        session,
        run=run,
        event_type="run.running",
        payload={
            "from_status": "preparing",
            "reason": "SubjectEnvelope materialized and runner adapter ready",
        },
        operation_key="run:running",
        allowed_statuses={"preparing"},
        next_status="running",
    )
