"""Fenced execution leases.

`claim_next_job` runs as one `BEGIN IMMEDIATE` transaction: it expires stale
leases, picks the next available job and installs a new attempt with an
incremented `lease_generation`, all under the same eager lock. That generation is
the fence — every later write by a worker re-checks it, so an expired worker
cannot commit after a newer attempt took the job over.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, select

from evidrun.contracts import RunExecutionAttempt, RunExecutionJob
from evidrun.infrastructure.database import clock
from evidrun.infrastructure.database.models import (
    RunEventRow,
    RunExecutionAttemptRow,
    RunExecutionJobRow,
)
from evidrun.infrastructure.database.queue.fencing import (
    require_active_lease,
    validate_reason_code,
)
from evidrun.infrastructure.database.queue.models import (
    execution_attempt_model,
    execution_job_model,
)
from evidrun.infrastructure.database.timestamps import naive_utc
from evidrun.infrastructure.database.unit_of_work import UnitOfWork
from evidrun.shared.types import new_id

__all__ = ["LeaseStore"]


class LeaseStore:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self.unit_of_work = unit_of_work

    def claim_next_job(
        self,
        *,
        worker_id: str,
        lease_seconds: float,
        job_id: str | None = None,
        now: datetime | None = None,
    ) -> tuple[RunExecutionJob, RunExecutionAttempt] | None:
        if not worker_id.strip():
            raise ValueError("worker_id cannot be empty")
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")
        claimed_at = now or clock.utc_now()
        comparable_now = claimed_at.replace(tzinfo=None)
        with self.unit_of_work.immediate() as session:
            leased_jobs = list(
                session.scalars(
                    select(RunExecutionJobRow).where(RunExecutionJobRow.status == "leased")
                )
            )
            for leased_job in leased_jobs:
                if leased_job.active_attempt_id is None:
                    raise ValueError("leased job has no active attempt")
                attempt = session.get(RunExecutionAttemptRow, leased_job.active_attempt_id)
                if attempt is None:
                    raise ValueError("leased job references a missing attempt")
                expires_at = naive_utc(attempt.lease_expires_at)
                if expires_at <= comparable_now:
                    attempt.status = "expired"
                    attempt.finished_at = claimed_at
                    attempt.reason_code = "lease_expired"
                    leased_job.status = "queued"
                    leased_job.active_attempt_id = None
                    leased_job.available_at = claimed_at

            query = select(RunExecutionJobRow).where(
                RunExecutionJobRow.status == "queued",
                RunExecutionJobRow.available_at <= comparable_now,
            )
            if job_id is not None:
                query = query.where(RunExecutionJobRow.id == job_id)
            job = session.scalar(
                query.order_by(
                    RunExecutionJobRow.available_at,
                    RunExecutionJobRow.created_at,
                    RunExecutionJobRow.id,
                ).limit(1)
            )
            if job is None:
                session.commit()
                return None
            ordinal = (
                session.scalar(
                    select(func.max(RunExecutionAttemptRow.ordinal)).where(
                        RunExecutionAttemptRow.job_id == job.id
                    )
                )
                or 0
            ) + 1
            generation = job.lease_generation + 1
            expires_at = claimed_at + timedelta(seconds=lease_seconds)
            attempt_row = RunExecutionAttemptRow(
                id=new_id("attempt"),
                job_id=job.id,
                ordinal=ordinal,
                worker_id=worker_id,
                lease_generation=generation,
                status="leased",
                leased_at=claimed_at,
                lease_expires_at=expires_at,
                last_heartbeat_at=claimed_at,
                finished_at=None,
                reason_code=None,
            )
            session.add(attempt_row)
            session.flush()
            job.status = "leased"
            job.active_attempt_id = attempt_row.id
            job.lease_generation = generation
            session.commit()
            return (
                execution_job_model(job),
                execution_attempt_model(attempt_row),
            )

    def heartbeat_lease(
        self,
        *,
        job_id: str,
        attempt_id: str,
        worker_id: str,
        lease_generation: int,
        lease_seconds: float,
        now: datetime | None = None,
    ) -> RunExecutionAttempt:
        heartbeat_at = now or clock.utc_now()
        with self.unit_of_work.session() as session:
            job, attempt = require_active_lease(
                session,
                job_id=job_id,
                attempt_id=attempt_id,
                worker_id=worker_id,
                lease_generation=lease_generation,
                now=heartbeat_at,
            )
            del job
            attempt.last_heartbeat_at = heartbeat_at
            attempt.lease_expires_at = heartbeat_at + timedelta(seconds=lease_seconds)
            session.commit()
            return execution_attempt_model(attempt)

    def assert_lease(
        self,
        *,
        job_id: str,
        attempt_id: str,
        worker_id: str,
        lease_generation: int,
        now: datetime | None = None,
    ) -> None:
        with self.unit_of_work.session() as session:
            require_active_lease(
                session,
                job_id=job_id,
                attempt_id=attempt_id,
                worker_id=worker_id,
                lease_generation=lease_generation,
                now=now or clock.utc_now(),
            )

    def release_lease(
        self,
        *,
        job_id: str,
        attempt_id: str,
        worker_id: str,
        lease_generation: int,
        reason_code: str = "released",
        available_at: datetime | None = None,
        now: datetime | None = None,
    ) -> RunExecutionJob:
        validate_reason_code(reason_code)
        released_at = now or clock.utc_now()
        with self.unit_of_work.session() as session:
            job, attempt = require_active_lease(
                session,
                job_id=job_id,
                attempt_id=attempt_id,
                worker_id=worker_id,
                lease_generation=lease_generation,
                now=released_at,
            )
            event_types = list(
                session.scalars(
                    select(RunEventRow.event_type).where(
                        RunEventRow.run_id == job.run_id,
                        RunEventRow.event_type.in_(("subject.invoked", "subject.responded")),
                    )
                )
            )
            if event_types.count("subject.invoked") > event_types.count("subject.responded"):
                raise ValueError("lease cannot be released while a Subject invocation is pending")
            attempt.status = "released"
            attempt.finished_at = released_at
            attempt.reason_code = reason_code
            job.status = "queued"
            job.active_attempt_id = None
            job.available_at = available_at or released_at
            session.commit()
            return execution_job_model(job)

    def reject_lease(
        self,
        *,
        job_id: str,
        attempt_id: str,
        worker_id: str,
        lease_generation: int,
        reason_code: str,
        now: datetime | None = None,
    ) -> RunExecutionJob:
        validate_reason_code(reason_code)
        rejected_at = now or clock.utc_now()
        with self.unit_of_work.session() as session:
            job, attempt = require_active_lease(
                session,
                job_id=job_id,
                attempt_id=attempt_id,
                worker_id=worker_id,
                lease_generation=lease_generation,
                now=rejected_at,
            )
            attempt.status = "rejected"
            attempt.finished_at = rejected_at
            attempt.reason_code = reason_code
            job.status = "rejected"
            job.active_attempt_id = None
            job.finished_at = rejected_at
            job.rejection_code = reason_code
            session.commit()
            return execution_job_model(job)

    def complete_lease(
        self,
        *,
        job_id: str,
        attempt_id: str,
        worker_id: str,
        lease_generation: int,
        now: datetime | None = None,
    ) -> RunExecutionJob:
        completed_at = now or clock.utc_now()
        with self.unit_of_work.session() as session:
            job, attempt = require_active_lease(
                session,
                job_id=job_id,
                attempt_id=attempt_id,
                worker_id=worker_id,
                lease_generation=lease_generation,
                now=completed_at,
            )
            attempt.status = "completed"
            attempt.finished_at = completed_at
            job.status = "completed"
            job.active_attempt_id = None
            job.finished_at = completed_at
            session.commit()
            return execution_job_model(job)

    def get_execution_job(self, job_id: str) -> RunExecutionJob:
        with self.unit_of_work.session() as session:
            row = session.get(RunExecutionJobRow, job_id)
            if row is None:
                raise KeyError(job_id)
            return execution_job_model(row)

    def get_run_execution(
        self, run_id: str
    ) -> tuple[RunExecutionJob, list[RunExecutionAttempt]] | None:
        with self.unit_of_work.session() as session:
            job = session.scalar(
                select(RunExecutionJobRow).where(RunExecutionJobRow.run_id == run_id)
            )
            if job is None:
                return None
            attempts = list(
                session.scalars(
                    select(RunExecutionAttemptRow)
                    .where(RunExecutionAttemptRow.job_id == job.id)
                    .order_by(RunExecutionAttemptRow.ordinal)
                )
            )
            return execution_job_model(job), [
                execution_attempt_model(item) for item in attempts
            ]
