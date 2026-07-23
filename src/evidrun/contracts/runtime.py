from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import Field, computed_field, field_validator, model_validator

from evidrun.contracts.authoring import (
    AgentInventorySpec,
    BudgetSpec,
    CapturePolicySpec,
    CheckpointPolicySpec,
    EvaluationDimension,
    EvaluationPlanSpec,
    EvaluationStage,
    GoalSpec,
    InputBinding,
    InteractionProtocolSpec,
    ScenarioSpec,
    StopCondition,
    WorkspaceTemplateSpec,
)
from evidrun.contracts.base import (
    ArtifactRef,
    CapabilityDescriptorRef,
    ContractModel,
    ContractRef,
    ContractType,
    Digest,
    EvidenceRef,
    ExtensionRef,
    KeyValue,
    NonEmptyStr,
    UtcDateTime,
    semantic_model_dump,
)
from evidrun.experiments.models import ContextPolicySpec
from evidrun.shared.types import sha256_json


class RunSpec(ContractModel):
    schema_version: Literal["1"] = "1"
    study_ref: ContractRef
    scenario_ref: ContractRef
    variant_id: NonEmptyStr
    repetition_index: int = Field(gt=0)
    seed: int | None = None
    goal_ref: ContractRef
    goal: GoalSpec
    scenario: ScenarioSpec
    agent_inventory_ref: ContractRef
    agent_inventory: AgentInventorySpec
    workspace_template_ref: ContractRef
    workspace: WorkspaceTemplateSpec
    interaction_protocol_ref: ContractRef
    interaction_protocol: InteractionProtocolSpec
    evaluation_plan_ref: ContractRef
    evaluation_plan: EvaluationPlanSpec
    checkpoint_policy_ref: ContractRef | None = None
    checkpoint_policy: CheckpointPolicySpec | None = None
    context_policy: ContextPolicySpec | None = None
    budgets: BudgetSpec
    stop_conditions: tuple[StopCondition, ...]
    capture_policy: CapturePolicySpec
    extensions: tuple[ExtensionRef, ...] = ()
    limitations: tuple[NonEmptyStr, ...] = ()

    @model_validator(mode="after")
    def validate_checkpoint_pair(self) -> RunSpec:
        if (self.checkpoint_policy_ref is None) != (self.checkpoint_policy is None):
            raise ValueError("checkpoint policy ref and payload must be present together")
        if self.goal.mode == "bounded_exploration":
            terminal_kinds = {
                item.kind for item in self.stop_conditions if item.action == "terminal"
            }
            if terminal_kinds == {"goal_complete"} or not terminal_kinds:
                raise ValueError("bounded exploration requires a bounded terminal stop condition")
        if not self.stop_conditions:
            raise ValueError("RunSpec requires at least one stop condition")
        expected_refs = (
            (self.study_ref, ContractType.STUDY),
            (self.scenario_ref, ContractType.SCENARIO),
            (self.goal_ref, ContractType.GOAL),
            (self.agent_inventory_ref, ContractType.AGENT_INVENTORY),
            (self.workspace_template_ref, ContractType.WORKSPACE_TEMPLATE),
            (self.interaction_protocol_ref, ContractType.INTERACTION_PROTOCOL),
            (self.evaluation_plan_ref, ContractType.EVALUATION_PLAN),
        )
        if any(reference.contract_type != expected for reference, expected in expected_refs):
            raise ValueError("RunSpec contains a reference in the wrong contract slot")
        if (
            self.checkpoint_policy_ref is not None
            and self.checkpoint_policy_ref.contract_type != ContractType.CHECKPOINT_POLICY
        ):
            raise ValueError("RunSpec checkpoint slot requires a checkpoint_policy ref")
        return self

    @computed_field
    @property
    def digest(self) -> str:
        return sha256_json(semantic_model_dump(self))


class ResolutionReason(ContractModel):
    code: Literal["unsupported", "denied", "unavailable", "digest_mismatch"]
    detail: NonEmptyStr


class ResolvedCapability(ContractModel):
    kind: Literal["tool", "skill"]
    requested_ref: CapabilityDescriptorRef
    required: bool
    status: Literal["resolved", "unsupported", "denied", "unavailable"]
    resolved_ref: CapabilityDescriptorRef | None = None
    adapter: NonEmptyStr | None = None
    effective_permissions: tuple[NonEmptyStr, ...] = ()
    context_refs: tuple[ArtifactRef, ...] = ()
    reason: ResolutionReason | None = None

    @model_validator(mode="after")
    def validate_resolution(self) -> ResolvedCapability:
        if self.status == "resolved" and (self.resolved_ref is None or self.adapter is None):
            raise ValueError("resolved capability requires an exact ref and adapter")
        if self.status == "resolved" and self.reason is not None:
            raise ValueError("resolved capability cannot contain an unresolved reason")
        if self.status != "resolved" and self.reason is None:
            raise ValueError("unresolved capability requires a reason")
        if self.status != "resolved" and (
            self.resolved_ref is not None or self.adapter is not None or self.effective_permissions
        ):
            raise ValueError("unresolved capability cannot expose an effective resolution")
        return self
class AdmissionIssue(ContractModel):
    category: Literal[
        "runner", "provider", "capability", "runtime", "workspace", "interaction", "policy"
    ]
    subject_ref: NonEmptyStr
    reason: ResolutionReason
    blocking: bool


class ResolvedAgentInventory(ContractModel):
    requirement_ref: ContractRef
    runner_ref: CapabilityDescriptorRef
    provider_profile_id: NonEmptyStr | None = None
    provider_profile_digest: Digest | None = None
    provider_model: NonEmptyStr | None = None
    provider_reasoning_effort: NonEmptyStr | None = None
    provider_adapter: NonEmptyStr | None = None
    capabilities: tuple[ResolvedCapability, ...] = ()
    runtime_capabilities: tuple[NonEmptyStr, ...] = ()

    @model_validator(mode="after")
    def validate_requirement_ref(self) -> ResolvedAgentInventory:
        if self.requirement_ref.contract_type != ContractType.AGENT_INVENTORY:
            raise ValueError("resolved inventory requires an agent_inventory ref")
        provider_fields = (
            self.provider_profile_digest,
            self.provider_model,
            self.provider_reasoning_effort,
            self.provider_adapter,
        )
        if self.provider_profile_id is None and any(item is not None for item in provider_fields):
            raise ValueError("offline inventory cannot contain provider resolution fields")
        if self.provider_profile_id is not None and any(
            item is None for item in provider_fields
        ):
            raise ValueError("provider inventory requires digest, model, reasoning, and adapter")
        return self

    @computed_field
    @property
    def digest(self) -> str:
        return sha256_json(semantic_model_dump(self))


class AdmissionRecord(ContractModel):
    schema_version: Literal["1"] = "1"
    run_spec_ref: NonEmptyStr
    run_spec_digest: Digest
    decision: Literal["admitted", "rejected"]
    resolved_inventory: ResolvedAgentInventory
    workspace_status: Literal["resolved", "unsupported", "denied", "unavailable"]
    interaction_status: Literal["resolved", "unsupported"]
    missing_requirements: tuple[NonEmptyStr, ...] = ()
    denied_policies: tuple[NonEmptyStr, ...] = ()
    issues: tuple[AdmissionIssue, ...] = ()
    warnings: tuple[NonEmptyStr, ...] = ()
    created_at_utc: UtcDateTime

    @model_validator(mode="after")
    def validate_decision(self) -> AdmissionRecord:
        if self.run_spec_ref != f"run-spec:{self.run_spec_digest}":
            raise ValueError("admission RunSpec ref must be content-addressed by its digest")
        blocked = bool(self.missing_requirements or self.denied_policies)
        blocked = blocked or self.workspace_status != "resolved"
        blocked = blocked or self.interaction_status != "resolved"
        blocked = blocked or any(item.blocking for item in self.issues)
        blocked = blocked or any(
            item.required and item.status != "resolved"
            for item in self.resolved_inventory.capabilities
        )
        if self.decision == "admitted" and blocked:
            raise ValueError("admitted record cannot contain blocking resolution failures")
        if self.decision == "rejected" and not blocked:
            raise ValueError("rejected admission requires a blocking reason")
        return self

    @computed_field
    @property
    def digest(self) -> str:
        return sha256_json(semantic_model_dump(self))


class SubjectWorkspace(ContractModel):
    runtime_kind: NonEmptyStr
    mounts: tuple[NonEmptyStr, ...] = ()
    write_zones: tuple[NonEmptyStr, ...] = ()
    network_mode: Literal["disabled", "provider_only", "allowlist"]
    external_effect_mode: Literal["denied", "approval_required", "allowlist"]


class SubjectEnvelope(ContractModel):
    schema_version: Literal["1"] = "1"
    run_spec_digest: Digest
    goal: GoalSpec
    inputs: tuple[InputBinding, ...]
    interaction_protocol: InteractionProtocolSpec
    effective_capabilities: tuple[ResolvedCapability, ...]
    workspace: SubjectWorkspace
    budgets: BudgetSpec
    stop_conditions: tuple[StopCondition, ...]

    @computed_field
    @property
    def digest(self) -> str:
        return sha256_json(semantic_model_dump(self))


class EvaluatorEnvelope(ContractModel):
    schema_version: Literal["1"] = "1"
    run_spec_digest: Digest
    plan_ref: ContractRef
    stage: EvaluationStage
    dimensions: tuple[EvaluationDimension, ...]
    inputs: tuple[InputBinding, ...]
    hidden_input_refs: tuple[ArtifactRef, ...] = ()
    blinded_fields: tuple[NonEmptyStr, ...] = ()

    @model_validator(mode="after")
    def validate_plan_ref(self) -> EvaluatorEnvelope:
        if self.plan_ref.contract_type != ContractType.EVALUATION_PLAN:
            raise ValueError("evaluator envelope requires an evaluation_plan ref")
        if {item.id for item in self.dimensions} != set(self.stage.output_dimensions):
            raise ValueError("evaluator envelope dimensions must match its stage")
        return self

    @computed_field
    @property
    def digest(self) -> str:
        return sha256_json(semantic_model_dump(self))


class RunRecord(ContractModel):
    schema_version: Literal["1"] = "1"
    run_id: NonEmptyStr
    run_spec_id: NonEmptyStr
    run_spec_digest: Digest
    admission_id: NonEmptyStr
    admission_digest: Digest
    study_ref: ContractRef
    scenario_ref: ContractRef
    variant_id: NonEmptyStr
    repetition_index: int = Field(gt=0)
    retry_of: NonEmptyStr | None = None
    created_at_utc: UtcDateTime

    @model_validator(mode="after")
    def validate_lineage_and_refs(self) -> RunRecord:
        if self.study_ref.contract_type != ContractType.STUDY:
            raise ValueError("RunRecord requires a Study ref")
        if self.scenario_ref.contract_type != ContractType.SCENARIO:
            raise ValueError("RunRecord requires a Scenario ref")
        if self.retry_of == self.run_id:
            raise ValueError("Run cannot retry itself")
        return self

    @field_validator("run_id", "retry_of")
    @classmethod
    def validate_run_uuid7(cls, value: str | None) -> str | None:
        if value is None:
            return None
        raw = value.removeprefix("run_")
        try:
            identifier = UUID(raw)
        except ValueError as exc:
            raise ValueError("Run IDs must contain a UUIDv7") from exc
        if identifier.version != 7:
            raise ValueError("Run IDs must contain a UUIDv7")
        return value


class EvaluationBoundary(ContractModel):
    up_to_event_sequence: int | None = Field(default=None, gt=0)
    event_hash: Digest | None = None
    checkpoint_id: NonEmptyStr | None = None

    @model_validator(mode="after")
    def validate_boundary(self) -> EvaluationBoundary:
        has_event = self.up_to_event_sequence is not None or self.event_hash is not None
        if has_event and (self.up_to_event_sequence is None or self.event_hash is None):
            raise ValueError("evaluation event boundary requires both sequence and hash")
        if not has_event and self.checkpoint_id is None:
            raise ValueError("evaluation requires an event or checkpoint boundary")
        return self


class DimensionValue(ContractModel):
    dimension_id: NonEmptyStr
    value: str | int | float | bool
    rationale: NonEmptyStr
    confidence: float | None = Field(default=None, ge=0, le=1)
    evidence_refs: tuple[EvidenceRef, ...] = Field(min_length=1)


class EvaluationRecord(ContractModel):
    schema_version: Literal["1"] = "1"
    record_id: NonEmptyStr
    run_id: NonEmptyStr
    plan_ref: ContractRef
    stage_id: NonEmptyStr
    source_type: Literal["deterministic_grader", "model_judge", "human_adjudicator"]
    evaluator_ref: CapabilityDescriptorRef
    provider_profile_id: NonEmptyStr | None = None
    provider_model: NonEmptyStr | None = None
    boundary: EvaluationBoundary
    dimension_values: tuple[DimensionValue, ...]
    gate_status: Literal["passed", "failed", "not_applicable"]
    status: Literal["provisional", "final"]
    supersedes_record_ref: NonEmptyStr | None = None
    created_at_utc: UtcDateTime

    @model_validator(mode="after")
    def validate_adjudication(self) -> EvaluationRecord:
        if self.plan_ref.contract_type != ContractType.EVALUATION_PLAN:
            raise ValueError("evaluation record requires an evaluation_plan ref")
        if self.source_type == "human_adjudicator" and self.status != "final":
            raise ValueError("human adjudication must be final")
        if self.source_type == "human_adjudicator" and self.supersedes_record_ref is None:
            raise ValueError("human adjudication must reference the prior record")
        if self.source_type != "human_adjudicator" and self.supersedes_record_ref is not None:
            raise ValueError("only human adjudication can supersede an evaluation record")
        if self.source_type == "model_judge" and self.status != "provisional":
            raise ValueError("model judge evaluations remain provisional")
        if self.source_type == "model_judge" and not (
            self.provider_profile_id and self.provider_model
        ):
            raise ValueError("model judge evaluation requires provider and model resolution")
        ids = [item.dimension_id for item in self.dimension_values]
        if len(ids) != len(set(ids)):
            raise ValueError("evaluation record dimensions must be unique")
        return self

    @computed_field
    @property
    def digest(self) -> str:
        return sha256_json(semantic_model_dump(self))


class CheckpointValidation(ContractModel):
    validator_ref: CapabilityDescriptorRef
    passed: bool
    rationale: NonEmptyStr
    evidence_refs: tuple[EvidenceRef, ...] = ()


class CheckpointRecord(ContractModel):
    schema_version: Literal["1"] = "1"
    checkpoint_id: NonEmptyStr
    run_id: NonEmptyStr
    policy_ref: ContractRef
    definition_id: NonEmptyStr
    definition_digest: Digest
    up_to_event_sequence: int = Field(gt=0)
    event_hash: Digest
    context_snapshot_refs: tuple[NonEmptyStr, ...] = ()
    protocol_state_ref: ArtifactRef | None = None
    artifact_manifest_ref: ArtifactRef | None = None
    workspace_snapshot_ref: ArtifactRef | None = None
    evaluation_record_refs: tuple[NonEmptyStr, ...] = ()
    validations: tuple[CheckpointValidation, ...]
    replayability: Literal["none", "partial", "deterministic"]
    replayability_limitations: tuple[NonEmptyStr, ...] = ()
    compatibility_tags: tuple[NonEmptyStr, ...] = ()
    created_at_utc: UtcDateTime

    @model_validator(mode="after")
    def validate_checkpoint(self) -> CheckpointRecord:
        if self.policy_ref.contract_type != ContractType.CHECKPOINT_POLICY:
            raise ValueError("checkpoint record requires a checkpoint_policy ref")
        if not self.validations or not all(item.passed for item in self.validations):
            raise ValueError("checkpoint records require successful validations")
        if self.replayability != "deterministic" and not self.replayability_limitations:
            raise ValueError("non-deterministic checkpoints require replayability limitations")
        return self

    @computed_field
    @property
    def checkpoint_hash(self) -> str:
        return sha256_json(semantic_model_dump(self))


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


class SubjectRespondedPayload(ContractModel):
    output: str
    evidence: tuple[str, ...] = ()
    metadata: tuple[KeyValue, ...] = ()


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


class RunTerminalPayload(ContractModel):
    status: Literal["completed", "failed", "cancelled", "budget_exhausted", "guardrail_stopped"]
    goal_state: Literal["achieved", "partially_achieved", "not_achieved", "not_assessable"]
    terminal_cause: NonEmptyStr
    evaluation_record_refs: tuple[NonEmptyStr, ...] = ()
    checkpoint_refs: tuple[NonEmptyStr, ...] = ()


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
    | RunTerminalPayload
)


def normalize_event_payload(event_type: str, payload: object) -> dict[str, object]:
    model = EVENT_PAYLOAD_MODELS.get(event_type)
    if model is None:
        raise ValueError(f"unregistered Run Event payload type: {event_type}")
    return semantic_model_dump(model.model_validate(payload))
