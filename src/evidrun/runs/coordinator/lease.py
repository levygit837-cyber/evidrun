"""Lease fencing: the guard every write in an attempt passes through.

A coordinator write is only legitimate while this worker still holds the lease at
the generation it claimed. `assert_held` runs before a write; `complete` closes the
attempt and tolerates exactly one race — another worker having already completed
the same job.
"""

from __future__ import annotations

from evidrun.contracts import RunExecutionAttempt, RunExecutionJob
from evidrun.infrastructure.database import LeaseLost, Repository

Lease = tuple[str, str, str, int]


def lease_of(job: RunExecutionJob, attempt: RunExecutionAttempt) -> Lease:
    """The fence a ledger write is stamped with."""

    return (
        job.job_id,
        attempt.attempt_id,
        attempt.worker_id,
        attempt.lease_generation,
    )


def assert_held(
    repository: Repository, job: RunExecutionJob, attempt: RunExecutionAttempt
) -> None:
    repository.lease.assert_lease(
        job_id=job.job_id,
        attempt_id=attempt.attempt_id,
        worker_id=attempt.worker_id,
        lease_generation=attempt.lease_generation,
    )


def complete(
    repository: Repository, job: RunExecutionJob, attempt: RunExecutionAttempt
) -> None:
    """Close the attempt; a lost lease is only tolerated if the job is complete.

    Losing the lease here means another worker took over. That is acceptable
    exclusively when it already drove the job to `completed`; otherwise the loss is
    real and must propagate.
    """

    try:
        repository.lease.complete_lease(
            job_id=job.job_id,
            attempt_id=attempt.attempt_id,
            worker_id=attempt.worker_id,
            lease_generation=attempt.lease_generation,
        )
    except LeaseLost:
        execution = repository.lease.get_run_execution(job.run_id)
        if execution is None or execution[0].status != "completed":
            raise
