"""Preparation: compile the SubjectEnvelope and materialize its inputs.

`prepare_run_execution` is a single fenced transaction in the queue aggregate, and
this phase must keep it that way: the snapshot, the envelope, and the preparation
events commit together or not at all. Nothing here opens a second session.

Preparation is idempotent. A Run whose envelope is already persisted skips straight
to materialization, which is what makes crash recovery return the same envelope.
"""

from __future__ import annotations

from evidrun.contracts import (
    AdmissionRecord,
    RunExecutionAttempt,
    RunExecutionJob,
    RunSpec,
    SubjectEnvelope,
)
from evidrun.contracts.authoring.scenario import InputBinding
from evidrun.contracts.compiler import SubjectEnvelopeCompiler
from evidrun.experiments.models import ContextPolicySpec
from evidrun.runs.coordinator.context import (
    PREPARABLE_RUN_STATUSES,
    ExecutionContext,
)
from evidrun.runs.coordinator.lease import assert_held, lease_of


def prepare(
    context: ExecutionContext,
    job: RunExecutionJob,
    attempt: RunExecutionAttempt,
    spec: RunSpec,
    admission: AdmissionRecord,
) -> tuple[SubjectEnvelope, dict[str, str]]:
    """Return the envelope and its materialized inputs, advancing to `running`."""

    repository = context.repository
    run = repository.read_model.get_run(job.run_id)
    if run.status not in PREPARABLE_RUN_STATUSES:
        raise ValueError(f"Run cannot be prepared while {run.status}")

    try:
        envelope = repository.read_model.get_subject_envelope(run.id).envelope
    except KeyError:
        envelope = _compile_and_persist(context, job, attempt, spec, admission)

    materialized_inputs = {
        item.id: context.artifact_store.get_verified(
            item.source, project_id=context.project_id(run.id)
        ).decode("utf-8")
        for item in envelope.inputs
    }
    _advance_to_running(context, job, attempt)
    return envelope, materialized_inputs


def _compile_and_persist(
    context: ExecutionContext,
    job: RunExecutionJob,
    attempt: RunExecutionAttempt,
    spec: RunSpec,
    admission: AdmissionRecord,
) -> SubjectEnvelope:
    """Compose context, store the materialized input, and commit the preparation."""

    repository = context.repository
    declared, context_policy = _single_visible_input(spec)
    if context.catalog.materializer is None:
        raise ValueError("active catalog has no ArtifactInputMaterializer") from None
    project_id = context.project_id(job.run_id)
    source = context.catalog.materializer.resolve_text(
        declared.source, project_id=project_id
    )
    snapshot = context.composer.compose(source, context_policy)
    selected = str(snapshot["selected_content"])
    materialized_ref = context.artifact_store.put_ref(
        selected.encode("utf-8"),
        project_id=project_id,
        media_type=declared.source.media_type,
        classification=declared.source.classification,
    )
    envelope = SubjectEnvelopeCompiler.compile(
        spec,
        admission,
        materialized_inputs=(declared.model_copy(update={"source": materialized_ref}),),
    )
    repository.preparation.prepare_run_execution(
        run_id=job.run_id,
        spec=spec,
        admission=admission,
        snapshot={
            **snapshot,
            "selected_content": _captured_content(selected, spec),
        },
        envelope=envelope,
        lease=lease_of(job, attempt),
    )
    return envelope


def _single_visible_input(
    spec: RunSpec,
) -> tuple[InputBinding, ContextPolicySpec]:
    """The active runtime materializes exactly one Subject-visible input.

    The ContextPolicy comes back with it so the caller keeps it narrowed: composing
    context without a policy is not a supported shape, and admission rejects it.
    """

    visible_inputs = tuple(
        item
        for item in spec.scenario.input_bindings
        if item.visibility in {"subject", "subject_and_evaluator"}
    )
    if len(visible_inputs) != 1 or spec.context_policy is None:
        raise ValueError("admitted deterministic Run has unsupported Subject inputs") from None
    return visible_inputs[0], spec.context_policy


def _captured_content(selected: str, spec: RunSpec) -> str:
    """Capture policy decides what the persisted snapshot may retain."""

    mode = spec.capture_policy.default_mode
    if mode == "redacted":
        return "[REDACTED]"
    if mode in {"metadata", "disabled"}:
        return ""
    return selected


def _advance_to_running(
    context: ExecutionContext, job: RunExecutionJob, attempt: RunExecutionAttempt
) -> None:
    run = context.repository.read_model.get_run(job.run_id)
    if run.status != "preparing":
        return
    assert_held(context.repository, job, attempt)
    context.repository.ledger.append_event(
        run_id=run.id,
        event_type="run.running",
        payload={
            "from_status": "preparing",
            "reason": "SubjectEnvelope materialized and runner adapter ready",
        },
        operation_key="run:running",
        lease=lease_of(job, attempt),
    )
