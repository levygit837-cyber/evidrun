"""Lease fencing, shared by every write that runs under a worker lease.

A fence is the tuple `(job_id, attempt_id, worker_id, lease_generation)`. Each
function below re-reads the live rows inside the caller's session and refuses the
write when any element disagrees, which is what stops an expired worker from
committing after a newer attempt took over. All of them take `session` so the
check and the write it guards stay in one transaction.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from evidrun.infrastructure.database import clock
from evidrun.infrastructure.database.models import RunExecutionAttemptRow, RunExecutionJobRow
from evidrun.infrastructure.database.timestamps import naive_utc
from evidrun.infrastructure.database.unit_of_work import LeaseFence, LeaseLost

__all__ = [
    "complete_active_lease",
    "reject_active_lease",
    "require_active_lease",
    "validate_optional_lease",
    "validate_reason_code",
]


def require_active_lease(
    session: Any,
    *,
    job_id: str,
    attempt_id: str,
    worker_id: str,
    lease_generation: int,
    now: datetime,
) -> tuple[RunExecutionJobRow, RunExecutionAttemptRow]:
    job = session.get(RunExecutionJobRow, job_id)
    attempt = session.get(RunExecutionAttemptRow, attempt_id)
    comparable_now = now.replace(tzinfo=None)
    if (
        job is None
        or attempt is None
        or job.status != "leased"
        or job.active_attempt_id != attempt_id
        or job.lease_generation != lease_generation
        or attempt.job_id != job_id
        or attempt.status != "leased"
        or attempt.worker_id != worker_id
        or attempt.lease_generation != lease_generation
        or naive_utc(attempt.lease_expires_at) <= comparable_now
    ):
        raise LeaseLost("execution lease is no longer active")
    return job, attempt


def validate_optional_lease(session: Any, *, lease: LeaseFence | None, run_id: str) -> None:
    if lease is None:
        return
    job_id, attempt_id, worker_id, lease_generation = lease
    job, _ = require_active_lease(
        session,
        job_id=job_id,
        attempt_id=attempt_id,
        worker_id=worker_id,
        lease_generation=lease_generation,
        now=clock.utc_now(),
    )
    if job.run_id != run_id:
        raise LeaseLost("execution lease does not own this Run")


def complete_active_lease(
    session: Any, *, lease: LeaseFence, run_id: str, completed_at: datetime
) -> None:
    job_id, attempt_id, worker_id, lease_generation = lease
    job, attempt = require_active_lease(
        session,
        job_id=job_id,
        attempt_id=attempt_id,
        worker_id=worker_id,
        lease_generation=lease_generation,
        now=completed_at,
    )
    if job.run_id != run_id:
        raise LeaseLost("execution lease does not own this Run")
    attempt.status = "completed"
    attempt.finished_at = completed_at
    job.status = "completed"
    job.active_attempt_id = None
    job.finished_at = completed_at


def reject_active_lease(
    session: Any,
    *,
    lease: LeaseFence,
    run_id: str,
    rejected_at: datetime,
    reason_code: str,
) -> None:
    job_id, attempt_id, worker_id, lease_generation = lease
    job, attempt = require_active_lease(
        session,
        job_id=job_id,
        attempt_id=attempt_id,
        worker_id=worker_id,
        lease_generation=lease_generation,
        now=rejected_at,
    )
    if job.run_id != run_id:
        raise LeaseLost("execution lease does not own this Run")
    attempt.status = "rejected"
    attempt.finished_at = rejected_at
    attempt.reason_code = reason_code
    job.status = "rejected"
    job.active_attempt_id = None
    job.finished_at = rejected_at
    job.rejection_code = reason_code


def validate_reason_code(value: str) -> None:
    if re.fullmatch(r"[a-z][a-z0-9_]{0,63}", value) is None:
        raise ValueError("execution reason code must be a sanitized identifier")
