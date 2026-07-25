"""Row-to-model conversion for execution jobs and attempts.

Pure translation: no query, no session. Kept beside the queue aggregate because
`lease_generation` and the fence tuple only mean something in its context.
"""

from __future__ import annotations

from typing import Any, cast

from evidrun.contracts import RunExecutionAttempt, RunExecutionJob
from evidrun.infrastructure.database.models import RunExecutionAttemptRow, RunExecutionJobRow
from evidrun.infrastructure.database.timestamps import aware_utc

__all__ = ["execution_attempt_model", "execution_job_model"]


def execution_job_model(row: RunExecutionJobRow) -> RunExecutionJob:
    return RunExecutionJob(
        job_id=row.id,
        run_id=row.run_id,
        status=cast(Any, row.status),
        idempotency_key=row.idempotency_key,
        request_digest=row.request_digest,
        available_at_utc=aware_utc(row.available_at),
        active_attempt_id=row.active_attempt_id,
        lease_generation=row.lease_generation,
        created_at_utc=aware_utc(row.created_at),
        finished_at_utc=(
            aware_utc(row.finished_at) if row.finished_at is not None else None
        ),
        rejection_code=row.rejection_code,
    )


def execution_attempt_model(row: RunExecutionAttemptRow) -> RunExecutionAttempt:
    return RunExecutionAttempt(
        attempt_id=row.id,
        job_id=row.job_id,
        ordinal=row.ordinal,
        worker_id=row.worker_id,
        lease_generation=row.lease_generation,
        status=cast(Any, row.status),
        leased_at_utc=aware_utc(row.leased_at),
        lease_expires_at_utc=aware_utc(row.lease_expires_at),
        last_heartbeat_at_utc=aware_utc(row.last_heartbeat_at),
        finished_at_utc=(
            aware_utc(row.finished_at) if row.finished_at is not None else None
        ),
        reason_code=row.reason_code,
    )
