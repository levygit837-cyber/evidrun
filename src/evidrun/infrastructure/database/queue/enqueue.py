"""Admitting a Run into the execution queue.

One `BEGIN IMMEDIATE` transaction writes the RunRow, its `run.queued` ledger event
and the execution job together. `idempotency_key` makes a replayed request return
the original Run instead of creating a second one, and the eager lock is what makes
that check safe against a concurrent caller.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import select

from evidrun.contracts import (
    AdmissionRecord,
    RunExecutionJob,
    RunSpec,
    normalize_event_payload,
)
from evidrun.infrastructure.database import clock
from evidrun.infrastructure.database.models import (
    AdmissionRecordRow,
    RunEventRow,
    RunExecutionJobRow,
    RunRow,
    RunSpecRow,
)
from evidrun.infrastructure.database.queue.models import execution_job_model
from evidrun.infrastructure.database.unit_of_work import UnitOfWork
from evidrun.shared.types import canonical_json, new_id, sha256_json

__all__ = ["EnqueueStore"]


class EnqueueStore:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self.unit_of_work = unit_of_work

    def enqueue_run(
        self,
        *,
        run_spec_id: str,
        admission_id: str,
        idempotency_key: str,
        retry_of: str | None = None,
        experiment_revision_id: str | None = None,
        now: datetime | None = None,
    ) -> tuple[RunRow, RunExecutionJob]:
        if not idempotency_key.strip():
            raise ValueError("idempotency key cannot be empty")
        requested_at = now or clock.utc_now()
        request_digest = sha256_json(
            {
                "run_spec_id": run_spec_id,
                "admission_id": admission_id,
                "retry_of": retry_of,
                "experiment_revision_id": experiment_revision_id,
            }
        )
        with self.unit_of_work.immediate() as session:
            existing = session.scalar(
                select(RunExecutionJobRow).where(
                    RunExecutionJobRow.idempotency_key == idempotency_key
                )
            )
            if existing is not None:
                if existing.request_digest != request_digest:
                    raise ValueError("idempotency key was already used for another request")
                run = session.get(RunRow, existing.run_id)
                if run is None:
                    raise ValueError("idempotent execution job references a missing Run")
                session.expunge(run)
                return run, execution_job_model(existing)

            spec, admission, admission_row = _load_admitted_contracts(
                session, run_spec_id=run_spec_id, admission_id=admission_id
            )
            if retry_of is not None:
                experiment_revision_id = _validate_retry(
                    session,
                    retry_of=retry_of,
                    run_spec_id=run_spec_id,
                    admission_id=admission_id,
                    admission_created_at=admission_row.created_at,
                    experiment_revision_id=experiment_revision_id,
                )

            run = RunRow(
                id=new_id("run"),
                experiment_revision_id=experiment_revision_id,
                variant_id=spec.variant_id,
                repetition=spec.repetition_index,
                status="queued",
                runner=spec.agent_inventory.runner_ref.name,
                objective=spec.goal.instruction,
                run_spec_id=run_spec_id,
                admission_id=admission_id,
                retry_of=retry_of,
                created_at=requested_at,
            )
            session.add(run)
            session.flush()
            _append_queued_event(session, run=run, spec=spec, admission=admission,
                                 requested_at=requested_at)
            job_row = RunExecutionJobRow(
                id=new_id("job"),
                run_id=run.id,
                status="queued",
                idempotency_key=idempotency_key,
                request_digest=request_digest,
                available_at=requested_at,
                active_attempt_id=None,
                lease_generation=0,
                created_at=requested_at,
                finished_at=None,
                rejection_code=None,
            )
            session.add(job_row)
            session.commit()
            session.expunge(run)
            return run, execution_job_model(job_row)


def _load_admitted_contracts(
    session: Any, *, run_spec_id: str, admission_id: str
) -> tuple[RunSpec, AdmissionRecord, AdmissionRecordRow]:
    """No Run exists before an admitted record for the exact RunSpec."""
    spec_row = session.get(RunSpecRow, run_spec_id)
    admission_row = session.get(AdmissionRecordRow, admission_id)
    if spec_row is None or admission_row is None:
        raise ValueError("RunSpec or AdmissionRecord does not exist")
    spec = RunSpec.model_validate(json.loads(spec_row.spec_json))
    admission = AdmissionRecord.model_validate(json.loads(admission_row.record_json))
    if spec.digest != spec_row.digest or admission.digest != admission_row.digest:
        raise ValueError("Run contracts failed stored digest verification")
    if (
        admission_row.run_spec_id != spec_row.id
        or admission_row.decision != "admitted"
        or admission.decision != "admitted"
        or admission.run_spec_digest != spec.digest
    ):
        raise ValueError("Run requires an admitted record for the exact RunSpec")
    return spec, admission, admission_row


def _validate_retry(
    session: Any,
    *,
    retry_of: str,
    run_spec_id: str,
    admission_id: str,
    admission_created_at: datetime,
    experiment_revision_id: str | None,
) -> str | None:
    """A retry needs an unsuccessful terminal source and a fresh admission after it."""
    source_run = session.get(RunRow, retry_of)
    if source_run is None:
        raise ValueError("retry_of must reference an existing Run")
    if source_run.status not in {
        "failed",
        "cancelled",
        "budget_exhausted",
        "guardrail_stopped",
    }:
        raise ValueError("only an unsuccessful terminal Run can be retried")
    if source_run.run_spec_id != run_spec_id:
        raise ValueError("retry admission must target the original RunSpec")
    if source_run.admission_id == admission_id:
        raise ValueError("retry requires a new AdmissionRecord")
    if source_run.completed_at is None or admission_created_at <= source_run.completed_at:
        raise ValueError("retry AdmissionRecord must be created after the source Run terminal")
    if experiment_revision_id is None:
        return source_run.experiment_revision_id
    return experiment_revision_id


def _append_queued_event(
    session: Any,
    *,
    run: RunRow,
    spec: RunSpec,
    admission: AdmissionRecord,
    requested_at: datetime,
) -> None:
    """`run.queued` opens the chain: sequence 1, no predecessor hash."""
    queued_payload = normalize_event_payload(
        "run.queued",
        {
            "run_id": run.id,
            "variant_id": spec.variant_id,
            "run_spec_digest": spec.digest,
            "admission_digest": admission.digest,
        },
    )
    event_id = new_id("evt")
    envelope = {
        "event_id": event_id,
        "schema_version": "1",
        "run_id": run.id,
        "sequence": 1,
        "type": "run.queued",
        "occurred_at_utc": requested_at.replace(tzinfo=None).isoformat(),
        "actor_type": "system",
        "actor_id": "evidrun",
        "classification": "internal",
        "payload": queued_payload,
        "correlation_id": run.id,
        "causation_id": None,
        "prev_event_hash": None,
    }
    session.add(
        RunEventRow(
            id=event_id,
            run_id=run.id,
            sequence=1,
            event_type="run.queued",
            occurred_at=requested_at,
            actor_type="system",
            actor_id="evidrun",
            classification="internal",
            payload_json=canonical_json(queued_payload),
            correlation_id=run.id,
            causation_id=None,
            prev_event_hash=None,
            event_hash=sha256_json(envelope),
            operation_key="run:queued",
        )
    )
