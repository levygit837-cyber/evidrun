"""Reconcile a Run whose Subject already responded before this attempt started.

Two distinct recoveries live here, and they are not interchangeable:

- no evaluation record yet: re-evaluate from the persisted response artifact, which
  only works when capture stored one. Without it the Run ends `not_assessable`
  rather than being invented;
- records already exist: project them into grades and `evaluation.completed`
  events. The records are the authority; this never re-grades them.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from evidrun.contracts import (
    EvaluationRecord,
    GoalStateTerminalResult,
    RunExecutionAttempt,
    RunExecutionJob,
    RunSpec,
)
from evidrun.runs.coordinator.context import ExecutionContext
from evidrun.runs.coordinator.lease import lease_of
from evidrun.runs.coordinator.recovery import (
    load_subject_result,
    recoverable_output_ref,
)
from evidrun.runs.coordinator.response import persist_evaluation
from evidrun.runs.coordinator.terminal import terminal


def resume_after_response(
    context: ExecutionContext,
    job: RunExecutionJob,
    attempt: RunExecutionAttempt,
    spec: RunSpec,
) -> None:
    repository = context.repository
    records = repository.read_model.get_evaluation_records(job.run_id)
    _advance_to_evaluating(context, job, attempt)
    if records:
        _reconcile_existing_records(context, job, attempt, records)
        return
    _evaluate_persisted_response(context, job, attempt, spec)


def _advance_to_evaluating(
    context: ExecutionContext, job: RunExecutionJob, attempt: RunExecutionAttempt
) -> None:
    run = context.repository.read_model.get_run(job.run_id)
    if run.status != "running":
        return
    context.repository.ledger.append_event(
        run_id=job.run_id,
        event_type="run.evaluating",
        payload={
            "from_status": "running",
            "reason": "persisted Subject response is being reconciled",
        },
        operation_key="run:evaluating",
        lease=lease_of(job, attempt),
    )


def _evaluate_persisted_response(
    context: ExecutionContext,
    job: RunExecutionJob,
    attempt: RunExecutionAttempt,
    spec: RunSpec,
) -> None:
    """Grade the response the ledger kept, or end the Run as not assessable."""

    repository = context.repository
    events = repository.read_model.get_run_events(job.run_id)
    response_event = next(item for item in events if item["type"] == "subject.responded")
    output_ref = recoverable_output_ref(response_event)
    if output_ref is None:
        terminal(
            context,
            job,
            attempt,
            event_type="run.failed",
            goal_result=GoalStateTerminalResult(state="not_assessable"),
            cause="Subject response cannot be deterministically recovered for evaluation",
        )
        return
    result = load_subject_result(
        output_ref,
        artifact_store=context.artifact_store,
        project_id=context.project_id(job.run_id),
    )
    outcome = context.catalog.evaluator_for(spec).evaluate(
        run_id=job.run_id,
        spec=spec,
        result=result,
        response_event_id=str(response_event["event_id"]),
        response_sequence=int(response_event["sequence"]),
        response_event_hash=str(response_event["event_hash"]),
        tool_events=tuple(item for item in events if item["type"].startswith("tool.")),
        artifact_store=context.artifact_store,
        project_id=context.project_id(job.run_id),
    )
    persist_evaluation(context, job, attempt, outcome)
    terminal(
        context,
        job,
        attempt,
        event_type="run.completed",
        goal_result=outcome.goal_result,
        cause="persisted Subject response evaluated after recovery",
    )


def _reconcile_existing_records(
    context: ExecutionContext,
    job: RunExecutionJob,
    attempt: RunExecutionAttempt,
    records: Sequence[EvaluationRecord],
) -> None:
    """Project persisted records into grades; the records themselves are authority."""

    repository = context.repository
    for record in records:
        dimension = record.dimension_values[0]
        passed = bool(dimension.value)
        repository.evaluation.save_grade(
            run_id=record.run_id,
            grader_id=record.stage_id,
            score=1.0 if passed else 0.0,
            passed=passed,
            rationale=dimension.rationale,
            evidence=tuple(item.ref for item in dimension.evidence_refs),
            lease=lease_of(job, attempt),
        )
        repository.ledger.append_event(
            run_id=job.run_id,
            event_type="evaluation.completed",
            payload={
                "evaluation_record_id": record.record_id,
                "evaluation_record_digest": record.digest,
                "gate_status": record.gate_status,
            },
            operation_key=f"evaluation:{record.stage_id}:completed",
            lease=lease_of(job, attempt),
        )
    passed_all = all(record.gate_status != "failed" for record in records)
    terminal(
        context,
        job,
        attempt,
        event_type="run.completed",
        goal_result=GoalStateTerminalResult(
            state="achieved" if passed_all else "not_achieved"
        ),
        cause="persisted deterministic evaluation reconciled",
    )


def response_counts(events: tuple[Mapping[str, object], ...]) -> tuple[int, int]:
    """How many times the Subject was invoked, and how many times it answered."""

    invocations = sum(item["type"] == "subject.invoked" for item in events)
    responses = sum(item["type"] == "subject.responded" for item in events)
    return invocations, responses
