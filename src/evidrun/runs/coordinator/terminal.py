"""Close a Run with exactly one terminal event.

Terminality is decided by the ledger, not by the coordinator's belief: if the Run
is already terminal, this completes the lease and writes nothing. That is what
makes a retried attempt idempotent instead of appending a second terminal event.
"""

from __future__ import annotations

from evidrun.contracts import (
    AdmissionRecord,
    GoalStateTerminalResult,
    RunExecutionAttempt,
    RunExecutionJob,
    RunSpec,
    semantic_model_dump,
)
from evidrun.runs.coordinator.context import TERMINAL_RUN_STATUSES, ExecutionContext
from evidrun.runs.coordinator.lease import assert_held, complete, lease_of


def terminal(
    context: ExecutionContext,
    job: RunExecutionJob,
    attempt: RunExecutionAttempt,
    *,
    event_type: str,
    goal_result: GoalStateTerminalResult,
    cause: str,
) -> None:
    repository = context.repository
    run = repository.read_model.get_run(job.run_id)
    if run.status in TERMINAL_RUN_STATUSES:
        complete(repository, job, attempt)
        return
    assert_held(repository, job, attempt)
    evaluations = repository.read_model.get_evaluation_records(run.id)
    repository.ledger.append_event(
        run_id=run.id,
        event_type=event_type,
        payload={
            "status": event_type.removeprefix("run."),
            "goal_result": semantic_model_dump(goal_result),
            "terminal_cause": cause,
            "evaluation_record_refs": [record.record_id for record in evaluations],
        },
        operation_key="run:terminal",
        lease=lease_of(job, attempt),
        complete_execution=True,
    )


def reject(
    context: ExecutionContext,
    job: RunExecutionJob,
    attempt: RunExecutionAttempt,
    *,
    reason_code: str,
) -> None:
    """Close a fatal operational job without exposing exception details.

    A Run with coherent contracts still gets a terminal `run.failed` event, because
    the ledger is the authority on why it ended. Only an incoherent or already
    terminal Run is rejected at the lease level instead.
    """

    repository = context.repository
    assert_held(repository, job, attempt)
    try:
        contracts = repository.read_model.get_run_contracts(job.run_id)
    except KeyError, ValueError:
        contracts = None
    run = repository.read_model.get_run(job.run_id)
    if _is_reportable(contracts, run.status):
        evaluations = repository.read_model.get_evaluation_records(run.id)
        repository.ledger.append_event(
            run_id=run.id,
            event_type="run.failed",
            payload={
                "status": "failed",
                "goal_result": semantic_model_dump(
                    GoalStateTerminalResult(state="not_assessable")
                ),
                "terminal_cause": "Runtime execution could not be completed safely",
                "evaluation_record_refs": [record.record_id for record in evaluations],
            },
            operation_key="run:terminal",
            lease=lease_of(job, attempt),
            reject_execution_code=reason_code,
        )
        return
    repository.lease.reject_lease(
        job_id=job.job_id,
        attempt_id=attempt.attempt_id,
        worker_id=attempt.worker_id,
        lease_generation=attempt.lease_generation,
        reason_code=reason_code,
    )


def _is_reportable(
    contracts: tuple[RunSpec, AdmissionRecord] | None, status: str
) -> bool:
    """A terminal event needs an admitted RunSpec that still matches its admission."""

    if contracts is None:
        return False
    spec, admission = contracts
    return (
        admission.decision == "admitted"
        and admission.run_spec_digest == spec.digest
        and status not in TERMINAL_RUN_STATUSES
    )
