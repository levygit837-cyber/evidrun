"""Factual event payloads, and what decides event validity per Run phase."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator

from evidrun.contracts.base import (
    ArtifactRef,
    CapabilityDescriptorRef,
    ContractModel,
    ContractRef,
    Digest,
    EvidenceRef,
    KeyValue,
    NonEmptyStr,
    semantic_model_dump,
)


class RunQueuedPayload(ContractModel):
    run_id: NonEmptyStr
    variant_id: NonEmptyStr
    run_spec_digest: Digest
    admission_digest: Digest


class RunPreparingPayload(ContractModel):
    scenario_ref: ContractRef


class RunLifecyclePayload(ContractModel):
    from_status: Literal["queued", "preparing", "running", "paused", "evaluating"]
    reason: NonEmptyStr


class ContextComposedPayload(ContractModel):
    snapshot_id: NonEmptyStr
    policy_id: NonEmptyStr
    strategy: Literal["head", "tail", "full"]
    source_chars: int = Field(ge=0)
    selected_chars: int = Field(ge=0)
    omitted: bool
    content_hash: Digest


class SubjectInvokedPayload(ContractModel):
    runner: NonEmptyStr
    network: Literal["disabled", "provider_only", "allowlist"]
    subject_envelope_digest: Digest
    evaluation_guidance_digest: Digest | None = None
    provider_profile_id: NonEmptyStr | None = None
    provider_model: NonEmptyStr | None = None
    provider_reasoning_effort: NonEmptyStr | None = None
    provider_adapter: NonEmptyStr | None = None

    @model_validator(mode="after")
    def validate_provider_resolution(self) -> SubjectInvokedPayload:
        provider_fields = (
            self.provider_profile_id,
            self.provider_model,
            self.provider_reasoning_effort,
            self.provider_adapter,
        )
        if any(item is not None for item in provider_fields) and any(
            item is None for item in provider_fields
        ):
            raise ValueError("Subject invocation provider resolution must be all-or-none")
        return self


class SubjectRespondedPayload(ContractModel):
    output: str | None = None
    output_ref: ArtifactRef | None = None
    output_digest: Digest
    capture_mode: Literal["metadata", "redacted", "raw_encrypted", "disabled"]
    evidence: tuple[str, ...] = ()
    metadata: tuple[KeyValue, ...] = ()

    @model_validator(mode="after")
    def validate_capture_shape(self) -> SubjectRespondedPayload:
        if self.capture_mode == "redacted" and (
            self.output != "[REDACTED]" or self.output_ref is not None or self.evidence
        ):
            raise ValueError(
                "redacted Subject capture requires the redaction marker and no raw evidence"
            )
        if self.capture_mode == "metadata" and (
            self.output is not None or self.output_ref is not None or self.evidence
        ):
            raise ValueError("metadata Subject capture cannot contain output or raw evidence")
        if self.capture_mode == "disabled" and (
            self.output is not None
            or self.output_ref is not None
            or self.evidence
            or self.metadata
        ):
            raise ValueError("disabled Subject capture cannot contain captured content")
        if self.capture_mode == "raw_encrypted" and (
            self.output is not None
            or self.output_ref is None
            or self.output_ref.classification.value != "sensitive"
            or any(not item.startswith("artifact:") for item in self.evidence)
        ):
            raise ValueError(
                "raw encrypted Subject capture requires a sensitive output artifact ref"
            )
        return self


class EvaluationCompletedPayload(ContractModel):
    evaluation_record_id: NonEmptyStr
    evaluation_record_digest: Digest
    gate_status: Literal["passed", "failed", "not_applicable"]


class CapabilityOfferedPayload(ContractModel):
    capability_ref: CapabilityDescriptorRef
    required: bool
    exposure: Literal["schema_only", "instructions", "instructions_and_schema"]
    effective_permissions: tuple[NonEmptyStr, ...] = ()


class SkillLoadedPayload(ContractModel):
    capability_ref: CapabilityDescriptorRef
    instruction_refs: tuple[ArtifactRef, ...] = ()


class CapabilityInvocationPayload(ContractModel):
    capability_ref: CapabilityDescriptorRef
    invocation_id: NonEmptyStr


class CapabilityResultPayload(ContractModel):
    capability_ref: CapabilityDescriptorRef
    invocation_id: NonEmptyStr
    result_ref: ArtifactRef | None = None
    reason: NonEmptyStr | None = None


class ToolCalledPayload(ContractModel):
    capability_ref: CapabilityDescriptorRef
    call_id: NonEmptyStr
    input_digest: Digest
    arguments_ref: ArtifactRef | None = None


class ToolDecisionPayload(ContractModel):
    call_id: NonEmptyStr
    decided_by: NonEmptyStr
    rationale: NonEmptyStr


class ToolResultPayload(ContractModel):
    capability_ref: CapabilityDescriptorRef
    call_id: NonEmptyStr
    result_ref: ArtifactRef | None = None
    reason: NonEmptyStr | None = None


class CheckpointValidationFailedPayload(ContractModel):
    checkpoint_definition_id: NonEmptyStr
    validator_ref: CapabilityDescriptorRef
    rationale: NonEmptyStr
    evidence_refs: tuple[EvidenceRef, ...] = ()


class ProgressObserverStartedPayload(ContractModel):
    attempt_id: NonEmptyStr
    policy_ref: ContractRef
    definition_id: NonEmptyStr
    up_to_event_sequence: int = Field(gt=0)
    event_hash: Digest
    summarizer_ref: CapabilityDescriptorRef


class ProgressArtifactCreatedPayload(ContractModel):
    attempt_id: NonEmptyStr
    progress_record_id: NonEmptyStr
    progress_record_digest: Digest
    artifact_ref: ArtifactRef
    up_to_event_sequence: int = Field(gt=0)
    event_hash: Digest


class ProgressObserverFailedPayload(ContractModel):
    attempt_id: NonEmptyStr
    policy_ref: ContractRef
    definition_id: NonEmptyStr
    up_to_event_sequence: int = Field(gt=0)
    event_hash: Digest
    phase: Literal[
        "input_materialization",
        "summarizer_resolution",
        "invocation",
        "output_validation",
        "artifact_write",
        "record_persistence",
    ]
    reason_code: NonEmptyStr
    retryable: bool = False


class GoalStateTerminalResult(ContractModel):
    goal_mode: Literal["goal_state"] = "goal_state"
    state: Literal["achieved", "partially_achieved", "not_achieved", "not_assessable"]


class BoundedExplorationTerminalResult(ContractModel):
    goal_mode: Literal["bounded_exploration"] = "bounded_exploration"
    disposition: Literal["concluded", "incomplete", "not_assessable"]
    stop_reason: Literal[
        "evidence_saturation",
        "bounded_completion",
        "budget_limit",
        "time_limit",
        "turn_limit",
        "human_stop",
        "guardrail",
        "provider_failure",
    ]
    stop_condition_kind: NonEmptyStr
    learning_summary_ref: ArtifactRef | None = None
    evidence_refs: tuple[EvidenceRef, ...] = ()


TerminalGoalResult = Annotated[
    GoalStateTerminalResult | BoundedExplorationTerminalResult,
    Field(discriminator="goal_mode"),
]


class RunTerminalPayload(ContractModel):
    status: Literal["completed", "failed", "cancelled", "budget_exhausted", "guardrail_stopped"]
    goal_result: TerminalGoalResult
    terminal_cause: NonEmptyStr
    evaluation_record_refs: tuple[NonEmptyStr, ...] = ()
    checkpoint_refs: tuple[NonEmptyStr, ...] = ()

    @model_validator(mode="after")
    def validate_unique_record_refs(self) -> RunTerminalPayload:
        if len(self.evaluation_record_refs) != len(set(self.evaluation_record_refs)):
            raise ValueError("terminal evaluation record refs must be unique")
        if len(self.checkpoint_refs) != len(set(self.checkpoint_refs)):
            raise ValueError("terminal checkpoint refs must be unique")
        return self


EVENT_ALLOWED_RUN_STATUSES: dict[str, frozenset[str]] = {
    "context.composed": frozenset({"preparing"}),
    "capability.offered": frozenset({"preparing", "running"}),
    "skill.loaded": frozenset({"preparing", "running"}),
    "subject.invoked": frozenset({"running"}),
    "subject.responded": frozenset({"running"}),
    "skill.invoked": frozenset({"running"}),
    "skill.completed": frozenset({"running"}),
    "skill.failed": frozenset({"running"}),
    "tool.called": frozenset({"running"}),
    "tool.approved": frozenset({"running"}),
    "tool.denied": frozenset({"running"}),
    "tool.completed": frozenset({"running"}),
    "tool.failed": frozenset({"running"}),
    "checkpoint.validation_failed": frozenset({"running", "paused", "evaluating"}),
    "evaluation.completed": frozenset({"evaluating"}),
}

UNSUPPORTED_RUNTIME_EVENT_TYPES = frozenset(
    {
        "run.paused",
        "run.resumed",
        "skill.loaded",
        "skill.invoked",
        "skill.completed",
        "skill.failed",
        "tool.approved",
        "checkpoint.validation_failed",
        "progress.observer_started",
        "progress.artifact_created",
        "progress.observer_failed",
    }
)


EVENT_PAYLOAD_MODELS: dict[str, type[ContractModel]] = {
    "run.queued": RunQueuedPayload,
    "run.preparing": RunPreparingPayload,
    "run.running": RunLifecyclePayload,
    "run.paused": RunLifecyclePayload,
    "run.resumed": RunLifecyclePayload,
    "run.evaluating": RunLifecyclePayload,
    "context.composed": ContextComposedPayload,
    "subject.invoked": SubjectInvokedPayload,
    "subject.responded": SubjectRespondedPayload,
    "evaluation.completed": EvaluationCompletedPayload,
    "capability.offered": CapabilityOfferedPayload,
    "skill.loaded": SkillLoadedPayload,
    "skill.invoked": CapabilityInvocationPayload,
    "skill.completed": CapabilityResultPayload,
    "skill.failed": CapabilityResultPayload,
    "tool.called": ToolCalledPayload,
    "tool.approved": ToolDecisionPayload,
    "tool.denied": ToolDecisionPayload,
    "tool.completed": ToolResultPayload,
    "tool.failed": ToolResultPayload,
    "checkpoint.validation_failed": CheckpointValidationFailedPayload,
    "progress.observer_started": ProgressObserverStartedPayload,
    "progress.artifact_created": ProgressArtifactCreatedPayload,
    "progress.observer_failed": ProgressObserverFailedPayload,
    "run.completed": RunTerminalPayload,
    "run.failed": RunTerminalPayload,
    "run.cancelled": RunTerminalPayload,
    "run.budget_exhausted": RunTerminalPayload,
    "run.guardrail_stopped": RunTerminalPayload,
}

RunEventPayload = (
    RunQueuedPayload
    | RunPreparingPayload
    | RunLifecyclePayload
    | ContextComposedPayload
    | SubjectInvokedPayload
    | SubjectRespondedPayload
    | EvaluationCompletedPayload
    | CapabilityOfferedPayload
    | SkillLoadedPayload
    | CapabilityInvocationPayload
    | CapabilityResultPayload
    | ToolCalledPayload
    | ToolDecisionPayload
    | ToolResultPayload
    | CheckpointValidationFailedPayload
    | ProgressObserverStartedPayload
    | ProgressArtifactCreatedPayload
    | ProgressObserverFailedPayload
    | RunTerminalPayload
)


def normalize_event_payload(event_type: str, payload: object) -> dict[str, object]:
    model = EVENT_PAYLOAD_MODELS.get(event_type)
    if model is None:
        raise ValueError(f"unregistered Run Event payload type: {event_type}")
    return semantic_model_dump(model.model_validate(payload))
