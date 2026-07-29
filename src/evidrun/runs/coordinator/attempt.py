"""Execute one attempt of a Run, from lease check to terminal event.

The order of the guards below is the recovery contract, not preference:

1. an already terminal Run just completes the lease;
2. stored contracts must still match the active catalog, or the attempt refuses;
3. an invocation without a response means a crash mid-turn — the Run fails as
   `not_assessable` rather than invoking the Subject twice;
4. a persisted response resumes instead of re-invoking;
5. an exhausted wall budget terminates before spending anything.

Only after all five does the Subject actually run.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import cast

from evidrun.contracts import (
    AdmissionRecord,
    CapabilityDescriptorRef,
    GoalStateTerminalResult,
    RunExecutionAttempt,
    RunExecutionJob,
    RunSpec,
    SubjectEnvelope,
)
from evidrun.infrastructure.providers import ProviderRequestError
from evidrun.runs.adapters import SubjectAdapter, SubjectBudgetExceeded
from evidrun.runs.coordinator.budget import remaining_wall_seconds
from evidrun.runs.coordinator.context import TERMINAL_RUN_STATUSES, ExecutionContext
from evidrun.runs.coordinator.lease import assert_held, complete, lease_of
from evidrun.runs.coordinator.prepare import prepare
from evidrun.runs.coordinator.response import persist_evaluation, persist_response
from evidrun.runs.coordinator.resume import response_counts, resume_after_response
from evidrun.runs.coordinator.terminal import terminal
from evidrun.runs.coordinator.tool_trace import PersistedToolTrace
from evidrun.shared.ports import SubjectResult

BUDGET_EXHAUSTED = "run.budget_exhausted"
WALL_BUDGET_CAUSE = "Run exceeded its max_wall_seconds budget"


async def execute_attempt(
    context: ExecutionContext,
    job: RunExecutionJob,
    attempt: RunExecutionAttempt,
) -> None:
    repository = context.repository
    assert_held(repository, job, attempt)
    run = repository.read_model.get_run(job.run_id)
    if run.status in TERMINAL_RUN_STATUSES:
        complete(repository, job, attempt)
        return
    spec, admission = _coherent_contracts(context, job)
    subject_adapter = context.catalog.subject_for(spec, admission)
    context.catalog.evaluator_for(spec)

    envelope, materialized_inputs = prepare(context, job, attempt, spec, admission)
    if repository.read_model.get_run(job.run_id).status in TERMINAL_RUN_STATUSES:
        complete(repository, job, attempt)
        return

    events = tuple(repository.read_model.get_run_events(job.run_id))
    invocations, responses = response_counts(events)
    if invocations > responses:
        _fail_indeterminate_invocation(context, job, attempt, events, subject_adapter)
        return
    if responses:
        resume_after_response(context, job, attempt, spec)
        return

    remaining = remaining_wall_seconds(repository, job.run_id, spec)
    if remaining <= 0:
        _terminate_budget(context, job, attempt, WALL_BUDGET_CAUSE)
        return
    result = await _invoke_subject(
        context,
        job,
        attempt,
        spec=spec,
        admission=admission,
        subject_adapter=subject_adapter,
        envelope=envelope,
        materialized_inputs=materialized_inputs,
        remaining=remaining,
    )
    if result is None:
        return
    _evaluate_and_close(context, job, attempt, spec, result)


def _coherent_contracts(
    context: ExecutionContext, job: RunExecutionJob
) -> tuple[RunSpec, AdmissionRecord]:
    """The stored admission must still be the decision this runtime would make."""

    contracts = context.repository.read_model.get_run_contracts(job.run_id)
    if contracts is None:
        raise ValueError("execution job references a legacy Run without contracts")
    spec, admission = contracts
    if admission.decision != "admitted" or admission.run_spec_digest != spec.digest:
        raise ValueError("execution job contracts are no longer coherent")
    if admission.execution_trust is None:
        raise ValueError("execution job admission has no execution trust")
    trust = context.repository.execution_trust.get_record(
        admission.execution_trust.trust_id
    )
    if trust.ref != admission.execution_trust:
        raise ValueError("execution job admission trust digest mismatch")
    active = context.catalog.admission_service().admit(spec, trust)
    if (
        active.decision != "admitted"
        or active.resolved_inventory != admission.resolved_inventory
        or active.workspace_status != admission.workspace_status
        or active.interaction_status != admission.interaction_status
    ):
        raise ValueError("stored admission no longer matches the active runtime catalog")
    return spec, admission


def _trace_sink(
    context: ExecutionContext,
    job: RunExecutionJob,
    attempt: RunExecutionAttempt,
    subject_adapter: SubjectAdapter,
) -> PersistedToolTrace:
    return PersistedToolTrace(
        repository=context.repository,
        artifact_store=context.artifact_store,
        run_id=job.run_id,
        project_id=context.project_id(job.run_id),
        actor_id=subject_adapter.name,
        lease=lease_of(job, attempt),
    )


def _fail_indeterminate_invocation(
    context: ExecutionContext,
    job: RunExecutionJob,
    attempt: RunExecutionAttempt,
    events: tuple[dict[str, object], ...],
    subject_adapter: SubjectAdapter,
) -> None:
    """A tool call with no durable outcome is recorded as failed before terminating."""

    settled = {
        _call_id(item)
        for item in events
        if item["type"] in {"tool.completed", "tool.denied", "tool.failed"}
    }
    trace_sink = _trace_sink(context, job, attempt, subject_adapter)
    for event in events:
        if event["type"] != "tool.called" or _call_id(event) in settled:
            continue
        payload = _payload(event)
        trace_sink.failed(
            capability_ref=CapabilityDescriptorRef.model_validate(
                payload["capability_ref"]
            ),
            call_id=_call_id(event),
            reason="prior tool execution ended without a durable result",
        )
    terminal(
        context,
        job,
        attempt,
        event_type="run.failed",
        goal_result=GoalStateTerminalResult(state="not_assessable"),
        cause="Prior Subject invocation ended without a durable response",
    )


def _payload(event: Mapping[str, object]) -> Mapping[str, object]:
    """A ledger event always carries a mapping payload; anything else is corrupt."""

    payload = event["payload"]
    if not isinstance(payload, Mapping):
        raise ValueError("ledger event payload is not a mapping")
    return cast(Mapping[str, object], payload)


def _call_id(event: Mapping[str, object]) -> str:
    return str(_payload(event)["call_id"])


def _terminate_budget(
    context: ExecutionContext,
    job: RunExecutionJob,
    attempt: RunExecutionAttempt,
    cause: str,
) -> None:
    terminal(
        context,
        job,
        attempt,
        event_type=BUDGET_EXHAUSTED,
        goal_result=GoalStateTerminalResult(state="not_assessable"),
        cause=cause,
    )


async def _invoke_subject(
    context: ExecutionContext,
    job: RunExecutionJob,
    attempt: RunExecutionAttempt,
    *,
    spec: RunSpec,
    admission: AdmissionRecord,
    subject_adapter: SubjectAdapter,
    envelope: SubjectEnvelope,
    materialized_inputs: dict[str, str],
    remaining: float,
):
    """Invoke the Subject under the remaining budget; `None` means already terminated.

    Every failure mode terminates the Run through the ledger rather than raising,
    so an attempt never ends with the Run left mid-flight.
    """

    assert_held(context.repository, job, attempt)
    _append_invoked(context, job, attempt, spec, admission, subject_adapter, envelope)
    trace_sink = _trace_sink(context, job, attempt, subject_adapter)
    try:
        return await asyncio.wait_for(
            subject_adapter.execute(
                envelope, materialized_inputs, trace_sink=trace_sink
            ),
            timeout=remaining,
        )
    except TimeoutError:
        assert_held(context.repository, job, attempt)
        _terminate_budget(context, job, attempt, WALL_BUDGET_CAUSE)
        return None
    except SubjectBudgetExceeded:
        assert_held(context.repository, job, attempt)
        _terminate_budget(
            context, job, attempt, "Run exceeded its max_tool_calls budget"
        )
        return None
    except ProviderRequestError as exc:
        assert_held(context.repository, job, attempt)
        _fail(context, job, attempt, f"Subject provider request failed: {exc.code}")
        return None
    except Exception:
        assert_held(context.repository, job, attempt)
        _fail(context, job, attempt, "Subject runner execution failed")
        return None


def _append_invoked(
    context: ExecutionContext,
    job: RunExecutionJob,
    attempt: RunExecutionAttempt,
    spec: RunSpec,
    admission: AdmissionRecord,
    subject_adapter: SubjectAdapter,
    envelope: SubjectEnvelope,
) -> None:
    inventory = admission.resolved_inventory
    context.repository.ledger.append_event(
        run_id=job.run_id,
        event_type="subject.invoked",
        payload={
            "runner": subject_adapter.name,
            "network": spec.workspace.network_policy.mode,
            "subject_envelope_digest": envelope.digest,
            "evaluation_guidance_digest": (
                envelope.evaluation_guidance.digest
                if envelope.evaluation_guidance is not None
                else None
            ),
            "provider_profile_id": inventory.provider_profile_id,
            "provider_model": inventory.provider_model,
            "provider_reasoning_effort": inventory.provider_reasoning_effort,
            "provider_adapter": inventory.provider_adapter,
        },
        operation_key="subject:invoked",
        lease=lease_of(job, attempt),
    )


def _fail(
    context: ExecutionContext,
    job: RunExecutionJob,
    attempt: RunExecutionAttempt,
    cause: str,
) -> None:
    terminal(
        context,
        job,
        attempt,
        event_type="run.failed",
        goal_result=GoalStateTerminalResult(state="not_assessable"),
        cause=cause,
    )


def _evaluate_and_close(
    context: ExecutionContext,
    job: RunExecutionJob,
    attempt: RunExecutionAttempt,
    spec: RunSpec,
    result: SubjectResult,
) -> None:
    assert_held(context.repository, job, attempt)
    response = persist_response(context, job, attempt, spec, result)
    outcome = context.catalog.evaluator_for(spec).evaluate(
        run_id=job.run_id,
        spec=spec,
        result=result,
        response_event_id=response.id,
        response_sequence=response.sequence,
        response_event_hash=response.event_hash,
        tool_events=tuple(
            item
            for item in context.repository.read_model.get_run_events(job.run_id)
            if item["type"].startswith("tool.")
        ),
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
        cause="terminal Subject response evaluated",
    )
