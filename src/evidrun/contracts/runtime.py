from __future__ import annotations

from typing import Annotated, Literal
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
    ProgressArtifactPolicySpec,
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
    HumanAttestationRecord,
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
    progress_artifact_policy_ref: ContractRef | None = None
    progress_artifact_policy: ProgressArtifactPolicySpec | None = None
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
        if (self.progress_artifact_policy_ref is None) != (
            self.progress_artifact_policy is None
        ):
            raise ValueError(
                "progress artifact policy ref and payload must be present together"
            )
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
        if (
            self.progress_artifact_policy_ref is not None
            and self.progress_artifact_policy_ref.contract_type
            != ContractType.PROGRESS_ARTIFACT_POLICY
        ):
            raise ValueError(
                "RunSpec progress slot requires a progress_artifact_policy ref"
            )
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
    exposure: Literal["schema_only", "instructions", "instructions_and_schema"]
    status: Literal["resolved", "unsupported", "denied", "unavailable"]
    resolved_ref: CapabilityDescriptorRef | None = None
    adapter: NonEmptyStr | None = None
    effective_interface_version: NonEmptyStr | None = None
    effective_permissions: tuple[NonEmptyStr, ...] = ()
    satisfied_authority_constraints: tuple[NonEmptyStr, ...] = ()
    context_refs: tuple[ArtifactRef, ...] = ()
    reason: ResolutionReason | None = None

    @model_validator(mode="after")
    def validate_resolution(self) -> ResolvedCapability:
        if self.status == "resolved" and (
            self.resolved_ref is None
            or self.adapter is None
            or self.effective_interface_version is None
        ):
            raise ValueError(
                "resolved capability requires an exact ref, adapter, and interface version"
            )
        if self.status == "resolved" and self.reason is not None:
            raise ValueError("resolved capability cannot contain an unresolved reason")
        if self.status != "resolved" and self.reason is None:
            raise ValueError("unresolved capability requires a reason")
        if self.status != "resolved" and (
            self.resolved_ref is not None
            or self.adapter is not None
            or self.effective_interface_version is not None
            or self.effective_permissions
            or self.satisfied_authority_constraints
            or self.context_refs
        ):
            raise ValueError("unresolved capability cannot expose an effective resolution")
        if self.exposure == "schema_only" and self.context_refs:
            raise ValueError("schema-only capability cannot expose instruction context")
        return self


class AdmissionIssue(ContractModel):
    category: Literal[
        "runner",
        "provider",
        "capability",
        "runtime",
        "workspace",
        "interaction",
        "observer",
        "authority",
        "policy",
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


class SubjectEvaluationDimension(ContractModel):
    id: NonEmptyStr
    description: NonEmptyStr
    value_type: Literal["boolean", "number", "category"]
    minimum: float | None = None
    maximum: float | None = None
    anchors: tuple[KeyValue, ...] = ()


class SubjectEvaluationGuidance(ContractModel):
    mode: Literal["pre_run"] = "pre_run"
    plan_ref: ContractRef
    dimensions: tuple[SubjectEvaluationDimension, ...]

    @model_validator(mode="after")
    def validate_plan(self) -> SubjectEvaluationGuidance:
        if self.plan_ref.contract_type != ContractType.EVALUATION_PLAN:
            raise ValueError("Subject evaluation guidance requires an evaluation_plan ref")
        if not self.dimensions:
            raise ValueError("Subject evaluation guidance requires public dimensions")
        return self

    @computed_field
    @property
    def digest(self) -> str:
        return sha256_json(semantic_model_dump(self))


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
    evaluation_guidance: SubjectEvaluationGuidance | None = None

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
        if has_event and self.checkpoint_id is not None:
            raise ValueError("evaluation boundary must use either an event or a checkpoint")
        return self


class DimensionValue(ContractModel):
    dimension_id: NonEmptyStr
    value: str | int | float | bool
    rationale: NonEmptyStr
    confidence: float | None = Field(default=None, ge=0, le=1)
    evidence_refs: tuple[EvidenceRef, ...] = Field(min_length=1)


class AdjudicatesEvaluationRelation(ContractModel):
    kind: Literal["adjudicates"] = "adjudicates"
    target_record_refs: tuple[NonEmptyStr, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_targets(self) -> AdjudicatesEvaluationRelation:
        if len(self.target_record_refs) != len(set(self.target_record_refs)):
            raise ValueError("adjudication target records must be unique")
        return self


class IndependentHumanReviewRelation(ContractModel):
    kind: Literal["independent_review"] = "independent_review"
    considers_record_refs: tuple[NonEmptyStr, ...] = ()

    @model_validator(mode="after")
    def validate_considered_records(self) -> IndependentHumanReviewRelation:
        if len(self.considers_record_refs) != len(set(self.considers_record_refs)):
            raise ValueError("considered evaluation records must be unique")
        return self


HumanEvaluationRelation = Annotated[
    AdjudicatesEvaluationRelation | IndependentHumanReviewRelation,
    Field(discriminator="kind"),
]


class EvaluationRecord(ContractModel):
    schema_version: Literal["1"] = "1"
    record_id: NonEmptyStr
    run_id: NonEmptyStr
    plan_ref: ContractRef
    stage_id: NonEmptyStr
    source_type: Literal[
        "deterministic_grader",
        "model_judge",
        "human_reviewer",
        "human_adjudicator",
    ]
    evaluator_ref: CapabilityDescriptorRef
    provider_profile_id: NonEmptyStr | None = None
    provider_model: NonEmptyStr | None = None
    boundary: EvaluationBoundary
    dimension_values: tuple[DimensionValue, ...]
    gate_status: Literal["passed", "failed", "not_applicable"]
    status: Literal["provisional", "final"]
    relation: HumanEvaluationRelation | None = None
    human_attestation: HumanAttestationRecord | None = None
    created_at_utc: UtcDateTime

    @model_validator(mode="after")
    def validate_adjudication(self) -> EvaluationRecord:
        if self.plan_ref.contract_type != ContractType.EVALUATION_PLAN:
            raise ValueError("evaluation record requires an evaluation_plan ref")
        is_human = self.source_type in {"human_reviewer", "human_adjudicator"}
        if is_human and self.status != "final":
            raise ValueError("human evaluations must be final")
        if is_human and self.human_attestation is None:
            raise ValueError("human evaluations require verified attestation evidence")
        if not is_human and (self.human_attestation is not None or self.relation is not None):
            raise ValueError("automated evaluations cannot claim human authority or precedence")
        if self.source_type == "human_adjudicator" and (
            self.relation is None or self.relation.kind != "adjudicates"
        ):
            raise ValueError("human adjudication requires explicit target records")
        if self.source_type == "human_reviewer" and (
            self.relation is None or self.relation.kind != "independent_review"
        ):
            raise ValueError("human review requires an independent review relation")
        if self.source_type == "model_judge" and self.status != "provisional":
            raise ValueError("model judge evaluations remain provisional")
        if self.source_type == "model_judge" and not (
            self.provider_profile_id and self.provider_model
        ):
            raise ValueError("model judge evaluation requires provider and model resolution")
        if self.source_type != "model_judge" and (
            self.provider_profile_id is not None or self.provider_model is not None
        ):
            raise ValueError(
                "only model judge evaluations may declare provider and model resolution"
            )
        if is_human and self.human_attestation is not None:
            expected_action = (
                "evaluation.adjudicated"
                if self.source_type == "human_adjudicator"
                else "evaluation.reviewed"
            )
            if self.human_attestation.action != expected_action:
                raise ValueError("human attestation action does not match the evaluation role")
            if self.human_attestation.target_digest != self.plan_ref.digest:
                raise ValueError("human evaluation attestation must target the EvaluationPlan")
            if self.human_attestation.subject_digest != self.human_subject_digest():
                raise ValueError("human attestation does not cover the evaluation content")
            if self.created_at_utc != self.human_attestation.verified_at_utc:
                raise ValueError(
                    "human evaluation timestamp must be the verified attestation timestamp"
                )
        ids = [item.dimension_id for item in self.dimension_values]
        if len(ids) != len(set(ids)):
            raise ValueError("evaluation record dimensions must be unique")
        return self

    def human_subject_digest(self) -> str:
        return sha256_json(
            {
                "run_id": self.run_id,
                "plan_ref": self.plan_ref.model_dump(mode="json"),
                "stage_id": self.stage_id,
                "source_type": self.source_type,
                "evaluator_ref": self.evaluator_ref.model_dump(mode="json"),
                "boundary": self.boundary.model_dump(mode="json", exclude_none=True),
                "dimension_values": [
                    item.model_dump(mode="json", exclude_none=True)
                    for item in self.dimension_values
                ],
                "gate_status": self.gate_status,
                "status": self.status,
                "relation": (
                    self.relation.model_dump(mode="json")
                    if self.relation is not None
                    else None
                ),
            }
        )

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
    admission_record_id: NonEmptyStr | None = None
    admission_record_digest: Digest | None = None
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
        validator_refs = [item.validator_ref for item in self.validations]
        if len(validator_refs) != len(set(validator_refs)):
            raise ValueError("checkpoint validator results must be unique")
        if not all(item.passed for item in self.validations):
            raise ValueError("checkpoint records require successful validations")
        if (self.admission_record_id is None) != (self.admission_record_digest is None):
            raise ValueError("checkpoint admission id and digest must be present together")
        if self.replayability != "deterministic" and not self.replayability_limitations:
            raise ValueError("non-deterministic checkpoints require replayability limitations")
        return self

    @computed_field
    @property
    def checkpoint_hash(self) -> str:
        return sha256_json(semantic_model_dump(self))


class ProgressStatement(ContractModel):
    id: NonEmptyStr
    kind: Literal["observation", "interpretation", "uncertainty"]
    text: NonEmptyStr
    confidence: float | None = Field(default=None, ge=0, le=1)
    evidence_refs: tuple[EvidenceRef, ...] = ()

    @model_validator(mode="after")
    def validate_evidence(self) -> ProgressStatement:
        if self.kind in {"observation", "interpretation"} and not self.evidence_refs:
            raise ValueError("progress observations and interpretations require evidence refs")
        return self


class ProgressArtifactContent(ContractModel):
    schema_version: Literal["1"] = "1"
    run_id: NonEmptyStr
    up_to_event_sequence: int = Field(gt=0)
    event_hash: Digest
    title: NonEmptyStr
    overview: NonEmptyStr
    statements: tuple[ProgressStatement, ...]
    limitations: tuple[NonEmptyStr, ...] = Field(min_length=1)
    status: Literal["provisional"] = "provisional"

    @computed_field
    @property
    def digest(self) -> str:
        return sha256_json(semantic_model_dump(self))


class ProgressArtifactRecord(ContractModel):
    schema_version: Literal["1"] = "1"
    record_id: NonEmptyStr
    run_id: NonEmptyStr
    policy_ref: ContractRef
    definition_id: NonEmptyStr
    definition_digest: Digest
    up_to_event_sequence: int = Field(gt=0)
    event_hash: Digest
    checkpoint_id: NonEmptyStr | None = None
    checkpoint_hash: Digest | None = None
    input_projection_version: Literal["run-event-prefix-v1"] = "run-event-prefix-v1"
    input_ledger_digest: Digest
    input_event_count: int = Field(gt=0)
    summarizer_ref: CapabilityDescriptorRef
    provider_profile_id: NonEmptyStr | None = None
    provider_model: NonEmptyStr | None = None
    artifact_ref: ArtifactRef
    status: Literal["provisional"] = "provisional"
    limitations: tuple[NonEmptyStr, ...] = Field(min_length=1)
    created_at_utc: UtcDateTime

    @model_validator(mode="after")
    def validate_progress_record(self) -> ProgressArtifactRecord:
        if self.policy_ref.contract_type != ContractType.PROGRESS_ARTIFACT_POLICY:
            raise ValueError("progress record requires a progress_artifact_policy ref")
        if (self.checkpoint_id is None) != (self.checkpoint_hash is None):
            raise ValueError("progress checkpoint id and hash must be present together")
        if (self.provider_profile_id is None) != (self.provider_model is None):
            raise ValueError("model observer provider and model must be present together")
        return self

    @computed_field
    @property
    def digest(self) -> str:
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
    evaluation_guidance_digest: Digest | None = None


class SubjectRespondedPayload(ContractModel):
    output: str | None = None
    output_digest: Digest
    capture_mode: Literal["metadata", "redacted", "raw_encrypted", "disabled"]
    evidence: tuple[str, ...] = ()
    metadata: tuple[KeyValue, ...] = ()

    @model_validator(mode="after")
    def validate_capture_shape(self) -> SubjectRespondedPayload:
        if self.capture_mode == "redacted" and (
            self.output != "[REDACTED]" or self.evidence
        ):
            raise ValueError(
                "redacted Subject capture requires the redaction marker and no raw evidence"
            )
        if self.capture_mode == "metadata" and (
            self.output is not None or self.evidence
        ):
            raise ValueError("metadata Subject capture cannot contain output or raw evidence")
        if self.capture_mode == "disabled" and (
            self.output is not None or self.evidence or self.metadata
        ):
            raise ValueError("disabled Subject capture cannot contain captured content")
        if self.capture_mode == "raw_encrypted" and (
            self.output is not None
            or any(not item.startswith("artifact:") for item in self.evidence)
        ):
            raise ValueError(
                "raw encrypted Subject capture requires artifact refs, never inline content"
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
        "capability.offered",
        "skill.loaded",
        "skill.invoked",
        "skill.completed",
        "skill.failed",
        "tool.called",
        "tool.approved",
        "tool.denied",
        "tool.completed",
        "tool.failed",
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
