from __future__ import annotations

from collections.abc import Mapping
from typing import Annotated, Literal, cast

from pydantic import Field, StringConstraints, model_validator

from evidrun.contracts.base import (
    ArtifactRef,
    CapabilityDescriptorRef,
    ContractModel,
    ContractRef,
    ContractType,
    ExtensionRef,
    KeyValue,
    NonEmptyStr,
    RevisionEnvelope,
)
from evidrun.experiments.models import ContextPolicySpec
from evidrun.shared.types import EvidenceMode


class IntentScope(ContractModel):
    included: tuple[NonEmptyStr, ...] = ()
    excluded: tuple[NonEmptyStr, ...] = ()

    @model_validator(mode="after")
    def validate_boundaries(self) -> IntentScope:
        if set(self.included) & set(self.excluded):
            raise ValueError("intent scope cannot both include and exclude the same boundary")
        return self


class StudyIntent(ContractModel):
    purpose: NonEmptyStr
    questions: tuple[NonEmptyStr, ...] = ()
    hypothesis: NonEmptyStr | None = None
    decision_to_inform: NonEmptyStr | None = None
    scope: IntentScope = IntentScope()
    assumptions: tuple[NonEmptyStr, ...] = ()


class GoalOutcome(ContractModel):
    id: NonEmptyStr
    description: NonEmptyStr


class GoalConstraint(ContractModel):
    id: NonEmptyStr
    rule: Literal["must", "must_not"]
    description: NonEmptyStr


class GoalSpec(ContractModel):
    mode: Literal["goal_state", "bounded_exploration"]
    instruction: NonEmptyStr
    outcomes: tuple[GoalOutcome, ...] = ()
    learning_targets: tuple[NonEmptyStr, ...] = ()
    constraints: tuple[GoalConstraint, ...] = ()
    evidence_expectations: tuple[NonEmptyStr, ...] = ()
    completion_observations: tuple[NonEmptyStr, ...] = ()

    @model_validator(mode="after")
    def validate_goal_shape(self) -> GoalSpec:
        outcome_ids = [item.id for item in self.outcomes]
        constraint_ids = [item.id for item in self.constraints]
        if len(outcome_ids) != len(set(outcome_ids)):
            raise ValueError("goal outcome ids must be unique")
        if len(constraint_ids) != len(set(constraint_ids)):
            raise ValueError("goal constraint ids must be unique")
        if set(outcome_ids) & set(constraint_ids):
            raise ValueError("goal ids must be unique across outcomes and constraints")
        if self.mode == "goal_state" and not self.outcomes:
            raise ValueError("goal_state requires at least one outcome")
        if self.mode == "bounded_exploration" and not (self.learning_targets or self.outcomes):
            raise ValueError("bounded_exploration requires a learning target or outcome")
        return self


class GoalRevision(RevisionEnvelope):
    contract_type: Literal[ContractType.GOAL] = ContractType.GOAL
    payload: GoalSpec


class InputBinding(ContractModel):
    id: NonEmptyStr
    role: NonEmptyStr
    source: ArtifactRef
    visibility: Literal["subject", "evaluator", "laboratory", "subject_and_evaluator"]
    mount_access: Literal["read_only", "read_write"] = "read_only"
    mount_name: NonEmptyStr | None = None


class ScenarioSpec(ContractModel):
    description: NonEmptyStr
    input_bindings: tuple[InputBinding, ...]
    observable_conditions: tuple[NonEmptyStr, ...] = ()
    limitations: tuple[NonEmptyStr, ...] = ()
    provenance: tuple[NonEmptyStr, ...] = ()

    @model_validator(mode="after")
    def validate_binding_ids(self) -> ScenarioSpec:
        ids = [item.id for item in self.input_bindings]
        if not ids:
            raise ValueError("scenario requires at least one input binding")
        if len(ids) != len(set(ids)):
            raise ValueError("scenario input binding ids must be unique")
        return self


class ScenarioRevision(RevisionEnvelope):
    contract_type: Literal[ContractType.SCENARIO] = ContractType.SCENARIO
    payload: ScenarioSpec


class CapabilityRequirement(ContractModel):
    kind: Literal["tool", "skill"]
    capability_ref: CapabilityDescriptorRef
    required: bool = True
    minimum_interface_version: NonEmptyStr
    requested_permissions: tuple[NonEmptyStr, ...] = ()
    exposure: Literal["schema_only", "instructions", "instructions_and_schema"]
    instruction_refs: tuple[ArtifactRef, ...] = ()
    authority_constraints: tuple[NonEmptyStr, ...] = ()


class RuntimeRequirement(ContractModel):
    capability: NonEmptyStr
    required: bool = True


class AgentInventorySpec(ContractModel):
    subject_id: NonEmptyStr
    runner_ref: CapabilityDescriptorRef
    provider_profile_id: NonEmptyStr | None = None
    capability_requirements: tuple[CapabilityRequirement, ...] = ()
    runtime_requirements: tuple[RuntimeRequirement, ...] = ()

    @model_validator(mode="after")
    def validate_capability_keys(self) -> AgentInventorySpec:
        keys = [
            (item.kind, item.capability_ref.namespace, item.capability_ref.name)
            for item in self.capability_requirements
        ]
        if len(keys) != len(set(keys)):
            raise ValueError("capability requirements must be unique")
        return self


class AgentInventoryRevision(RevisionEnvelope):
    contract_type: Literal[ContractType.AGENT_INVENTORY] = ContractType.AGENT_INVENTORY
    payload: AgentInventorySpec


class WorkspaceMount(ContractModel):
    name: NonEmptyStr
    source: ArtifactRef
    access: Literal["read_only", "read_write"]
    target: NonEmptyStr


class NetworkPolicy(ContractModel):
    mode: Literal["disabled", "provider_only", "allowlist"]
    allowed_endpoint_refs: tuple[NonEmptyStr, ...] = ()

    @model_validator(mode="after")
    def validate_allowlist(self) -> NetworkPolicy:
        if self.mode == "allowlist" and not self.allowed_endpoint_refs:
            raise ValueError("allowlist network policy requires endpoint refs")
        if self.mode != "allowlist" and self.allowed_endpoint_refs:
            raise ValueError("endpoint refs are only valid for allowlist network policy")
        return self


class ExternalEffectPolicy(ContractModel):
    mode: Literal["denied", "approval_required", "allowlist"]
    allowed_effects: tuple[NonEmptyStr, ...] = ()

    @model_validator(mode="after")
    def validate_allowlist(self) -> ExternalEffectPolicy:
        if self.mode == "allowlist" and not self.allowed_effects:
            raise ValueError("external effect allowlist requires effects")
        if self.mode != "allowlist" and self.allowed_effects:
            raise ValueError("allowed effects are only valid for allowlist policy")
        return self


class SnapshotPolicy(ContractModel):
    capture_workspace: bool = False
    include_zones: tuple[NonEmptyStr, ...] = ()


class SecretBindingRef(ContractModel):
    binding_id: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            min_length=1,
            max_length=64,
            pattern=r"^[a-z][a-z0-9.-]*$",
        ),
    ]
    source: Literal["keychain", "environment"]


class CleanupPolicy(ContractModel):
    mode: Literal["discard", "retain_until_ttl", "retain"] = "discard"
    ttl_seconds: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_ttl(self) -> CleanupPolicy:
        if self.mode == "retain_until_ttl" and self.ttl_seconds is None:
            raise ValueError("retain_until_ttl cleanup requires ttl_seconds")
        if self.mode != "retain_until_ttl" and self.ttl_seconds is not None:
            raise ValueError("ttl_seconds is only valid with retain_until_ttl")
        return self


class WorkspaceTemplateSpec(ContractModel):
    runtime_kind: NonEmptyStr
    lifecycle: Literal["ephemeral_per_run"] = "ephemeral_per_run"
    mounts: tuple[WorkspaceMount, ...] = ()
    write_zones: tuple[NonEmptyStr, ...] = ()
    network_policy: NetworkPolicy
    external_effect_policy: ExternalEffectPolicy
    secret_binding_refs: tuple[SecretBindingRef, ...] = ()
    snapshot_policy: SnapshotPolicy = SnapshotPolicy()
    cleanup_policy: CleanupPolicy = CleanupPolicy()

    @model_validator(mode="after")
    def validate_workspace_names(self) -> WorkspaceTemplateSpec:
        mount_names = [item.name for item in self.mounts]
        if len(mount_names) != len(set(mount_names)):
            raise ValueError("workspace mount names must be unique")
        if len(self.write_zones) != len(set(self.write_zones)):
            raise ValueError("workspace write zones must be unique")
        return self


class WorkspaceTemplateRevision(RevisionEnvelope):
    contract_type: Literal[ContractType.WORKSPACE_TEMPLATE] = ContractType.WORKSPACE_TEMPLATE
    payload: WorkspaceTemplateSpec


class InteractionNode(ContractModel):
    id: NonEmptyStr
    kind: Literal["prompt", "await_subject", "checkpoint", "human_approval", "terminal"]
    content_ref: ArtifactRef | None = None


class AlwaysTrigger(ContractModel):
    kind: Literal["always"] = "always"


class EventTrigger(ContractModel):
    kind: Literal["event"] = "event"
    event_type: NonEmptyStr


class CheckpointReachedTrigger(ContractModel):
    kind: Literal["checkpoint_reached"] = "checkpoint_reached"
    checkpoint_definition_id: NonEmptyStr


class EvaluatorSignalTrigger(ContractModel):
    kind: Literal["evaluator_signal"] = "evaluator_signal"
    stage_id: NonEmptyStr
    signal: NonEmptyStr


class HumanSignalTrigger(ContractModel):
    kind: Literal["human_signal"] = "human_signal"
    signal: NonEmptyStr


class PredicateTrigger(ContractModel):
    kind: Literal["predicate"] = "predicate"
    predicate_ref: CapabilityDescriptorRef


InteractionTrigger = Annotated[
    AlwaysTrigger
    | EventTrigger
    | CheckpointReachedTrigger
    | EvaluatorSignalTrigger
    | HumanSignalTrigger
    | PredicateTrigger,
    Field(discriminator="kind"),
]


class InteractionEdge(ContractModel):
    source: NonEmptyStr
    target: NonEmptyStr
    trigger: InteractionTrigger
    priority: int = 0
    max_activations: int = Field(default=1, gt=0)


class InteractionProtocolSpec(ContractModel):
    mode: Literal["single_turn", "graph"]
    system_prompt_ref: ArtifactRef | None = None
    initial_message_refs: tuple[ArtifactRef, ...] = ()
    max_turns: int = Field(default=1, gt=0)
    nodes: tuple[InteractionNode, ...] = ()
    edges: tuple[InteractionEdge, ...] = ()

    @model_validator(mode="after")
    def validate_graph(self) -> InteractionProtocolSpec:
        if self.mode == "single_turn" and (self.nodes or self.edges):
            raise ValueError("single_turn protocol cannot declare graph nodes or edges")
        if self.mode == "graph":
            ids = [node.id for node in self.nodes]
            if not ids:
                raise ValueError("graph protocol requires nodes")
            if len(ids) != len(set(ids)):
                raise ValueError("interaction node ids must be unique")
            known = set(ids)
            for edge in self.edges:
                if edge.source not in known or edge.target not in known:
                    raise ValueError("interaction edge references unknown node")
        return self


class InteractionProtocolRevision(RevisionEnvelope):
    contract_type: Literal[ContractType.INTERACTION_PROTOCOL] = ContractType.INTERACTION_PROTOCOL
    payload: InteractionProtocolSpec


class EvaluationDimension(ContractModel):
    id: NonEmptyStr
    description: NonEmptyStr
    value_type: Literal["boolean", "number", "category"]
    minimum: float | None = None
    maximum: float | None = None
    anchors: tuple[KeyValue, ...] = ()

    @model_validator(mode="after")
    def validate_scale(self) -> EvaluationDimension:
        if (
            self.value_type == "number"
            and self.minimum is not None
            and self.maximum is not None
            and self.minimum >= self.maximum
        ):
            raise ValueError("evaluation dimension minimum must be lower than maximum")
        if self.value_type != "number" and (self.minimum is not None or self.maximum is not None):
            raise ValueError("only numeric dimensions can declare minimum or maximum")
        return self


class EvaluationTrigger(ContractModel):
    kind: Literal["run_terminal", "checkpoint", "event"]
    reference: NonEmptyStr | None = None

    @model_validator(mode="after")
    def validate_reference(self) -> EvaluationTrigger:
        if self.kind in {"checkpoint", "event"} and self.reference is None:
            raise ValueError(f"{self.kind} evaluation trigger requires a reference")
        if self.kind == "run_terminal" and self.reference is not None:
            raise ValueError("run_terminal evaluation trigger cannot declare a reference")
        return self


class EvaluationStage(ContractModel):
    id: NonEmptyStr
    kind: Literal["integrity", "deterministic_grader", "model_judge", "human_review"]
    evaluator_ref: CapabilityDescriptorRef
    trigger: EvaluationTrigger
    output_dimensions: tuple[NonEmptyStr, ...] = ()
    hard_gate: bool = False
    parameters: tuple[KeyValue, ...] = ()


class SubjectEvaluationDisclosure(ContractModel):
    mode: Literal["none", "pre_run", "on_request", "post_run"] = "none"
    dimension_ids: tuple[NonEmptyStr, ...] = ()
    include_scale: bool = False
    include_anchors: bool = False

    @model_validator(mode="after")
    def validate_disclosure(self) -> SubjectEvaluationDisclosure:
        if self.mode == "none" and (
            self.dimension_ids or self.include_scale or self.include_anchors
        ):
            raise ValueError("none disclosure cannot expose evaluation guidance")
        if self.mode != "none" and not self.dimension_ids:
            raise ValueError("enabled Subject disclosure requires public dimensions")
        return self


class EvaluationDisclosure(ContractModel):
    subject: SubjectEvaluationDisclosure = SubjectEvaluationDisclosure()
    hidden_input_refs: tuple[ArtifactRef, ...] = ()


class BlindingPolicy(ContractModel):
    hidden_fields: tuple[NonEmptyStr, ...] = ()


class AggregationSpec(ContractModel):
    projector_ref: CapabilityDescriptorRef
    parameters: tuple[KeyValue, ...] = ()


class HumanAdjudicationPolicy(ContractModel):
    required: bool = False
    adjudicator_ref: CapabilityDescriptorRef | None = None
    adjudicable_stage_ids: tuple[NonEmptyStr, ...] = ()
    attestation_verifier_ref: CapabilityDescriptorRef | None = None

    @model_validator(mode="after")
    def validate_required_authority(self) -> HumanAdjudicationPolicy:
        configured = (
            self.adjudicator_ref is not None
            and bool(self.adjudicable_stage_ids)
            and self.attestation_verifier_ref is not None
        )
        if self.required and not configured:
            raise ValueError(
                "required human adjudication needs an adjudicator, stages, and verifier"
            )
        if not self.required and any(
            (
                self.adjudicator_ref is not None,
                bool(self.adjudicable_stage_ids),
                self.attestation_verifier_ref is not None,
            )
        ):
            raise ValueError("optional adjudication authority is not supported in v1")
        return self


class EvaluationPlanSpec(ContractModel):
    dimensions: tuple[EvaluationDimension, ...]
    stages: tuple[EvaluationStage, ...]
    disclosure: EvaluationDisclosure = EvaluationDisclosure()
    blinding_policy: BlindingPolicy = BlindingPolicy()
    aggregation: AggregationSpec | None = None
    human_adjudication_policy: HumanAdjudicationPolicy = HumanAdjudicationPolicy()
    limitations: tuple[NonEmptyStr, ...] = ()

    @model_validator(mode="after")
    def validate_evaluation_plan(self) -> EvaluationPlanSpec:
        dimension_ids = [item.id for item in self.dimensions]
        stage_ids = [item.id for item in self.stages]
        if not dimension_ids or not stage_ids:
            raise ValueError("evaluation plan requires dimensions and stages")
        if len(dimension_ids) != len(set(dimension_ids)):
            raise ValueError("evaluation dimension ids must be unique")
        if len(stage_ids) != len(set(stage_ids)):
            raise ValueError("evaluation stage ids must be unique")
        known_dimensions = set(dimension_ids)
        for stage in self.stages:
            if not set(stage.output_dimensions).issubset(known_dimensions):
                raise ValueError("evaluation stage references unknown dimension")
        if not set(self.disclosure.subject.dimension_ids).issubset(known_dimensions):
            raise ValueError("disclosure references unknown dimension")
        adjudicable = set(self.human_adjudication_policy.adjudicable_stage_ids)
        if not adjudicable.issubset(stage_ids):
            raise ValueError("human adjudication policy references an unknown stage")
        return self


class EvaluationPlanRevision(RevisionEnvelope):
    contract_type: Literal[ContractType.EVALUATION_PLAN] = ContractType.EVALUATION_PLAN
    payload: EvaluationPlanSpec


class ManualCheckpointTrigger(ContractModel):
    kind: Literal["manual"] = "manual"


class CheckpointEventTrigger(ContractModel):
    kind: Literal["event"] = "event"
    event_type: NonEmptyStr


class ProtocolNodeCheckpointTrigger(ContractModel):
    kind: Literal["protocol_node"] = "protocol_node"
    node_id: NonEmptyStr


class PredicateCheckpointTrigger(ContractModel):
    kind: Literal["predicate"] = "predicate"
    predicate_ref: CapabilityDescriptorRef


CheckpointTrigger = Annotated[
    ManualCheckpointTrigger
    | CheckpointEventTrigger
    | ProtocolNodeCheckpointTrigger
    | PredicateCheckpointTrigger,
    Field(discriminator="kind"),
]


class CheckpointCaptureSpec(ContractModel):
    context_snapshot: bool = False
    protocol_state: bool = False
    artifact_manifest: bool = False
    workspace_snapshot: bool = False
    provider_resolution: bool = False
    agent_inventory: bool = False
    evaluation_records: bool = False


class CheckpointDefinition(ContractModel):
    id: NonEmptyStr
    label: NonEmptyStr
    order: int = Field(gt=0)
    trigger: CheckpointTrigger
    validator_refs: tuple[CapabilityDescriptorRef, ...] = ()
    capture: CheckpointCaptureSpec
    required: bool = False
    compatibility_tags: tuple[NonEmptyStr, ...] = ()


class CheckpointPolicySpec(ContractModel):
    definitions: tuple[CheckpointDefinition, ...]

    @model_validator(mode="after")
    def validate_definitions(self) -> CheckpointPolicySpec:
        ids = [item.id for item in self.definitions]
        orders = [item.order for item in self.definitions]
        if not ids:
            raise ValueError("checkpoint policy requires at least one definition")
        if len(ids) != len(set(ids)):
            raise ValueError("checkpoint definition ids must be unique")
        if len(orders) != len(set(orders)):
            raise ValueError("checkpoint definition order must be unique")
        return self


class CheckpointPolicyRevision(RevisionEnvelope):
    contract_type: Literal[ContractType.CHECKPOINT_POLICY] = ContractType.CHECKPOINT_POLICY
    payload: CheckpointPolicySpec


class CheckpointReachedProgressTrigger(ContractModel):
    kind: Literal["checkpoint_reached"] = "checkpoint_reached"
    checkpoint_definition_id: NonEmptyStr


class SubjectTurnIntervalProgressTrigger(ContractModel):
    kind: Literal["subject_turn_interval"] = "subject_turn_interval"
    counted_event_type: Literal["subject.responded"] = "subject.responded"
    every_n_turns: int = Field(gt=0)


ProgressArtifactTrigger = Annotated[
    CheckpointReachedProgressTrigger | SubjectTurnIntervalProgressTrigger,
    Field(discriminator="kind"),
]


class ProgressArtifactDefinition(ContractModel):
    id: NonEmptyStr
    label: NonEmptyStr
    trigger: ProgressArtifactTrigger
    summarizer_ref: CapabilityDescriptorRef
    minimum_interface_version: NonEmptyStr = "1"
    authority_constraints: tuple[
        Literal["read_current_run_ledger_prefix"],
        Literal["write_progress_artifact_only"],
        Literal["no_subject_feedback"],
    ] = (
        "read_current_run_ledger_prefix",
        "write_progress_artifact_only",
        "no_subject_feedback",
    )
    input_scope: Literal["complete_run_ledger_prefix"] = "complete_run_ledger_prefix"
    max_output_characters: int = Field(default=12_000, gt=0)
    audience: Literal["laboratory_human"] = "laboratory_human"


class ProgressArtifactPolicySpec(ContractModel):
    definitions: tuple[ProgressArtifactDefinition, ...]
    limitations: tuple[NonEmptyStr, ...] = ()

    @model_validator(mode="after")
    def validate_definitions(self) -> ProgressArtifactPolicySpec:
        ids = [item.id for item in self.definitions]
        if not ids:
            raise ValueError("progress artifact policy requires at least one definition")
        if len(ids) != len(set(ids)):
            raise ValueError("progress artifact definition ids must be unique")
        return self


class ProgressArtifactPolicyRevision(RevisionEnvelope):
    contract_type: Literal[ContractType.PROGRESS_ARTIFACT_POLICY] = (
        ContractType.PROGRESS_ARTIFACT_POLICY
    )
    payload: ProgressArtifactPolicySpec


class BudgetSpec(ContractModel):
    max_wall_seconds: int = Field(gt=0)
    max_turns: int | None = Field(default=None, gt=0)
    max_input_tokens: int | None = Field(default=None, gt=0)
    max_output_tokens: int | None = Field(default=None, gt=0)
    max_tool_calls: int | None = Field(default=None, gt=0)
    max_cost: float | None = Field(default=None, ge=0)


class StopCondition(ContractModel):
    kind: Literal[
        "goal_complete",
        "bounded_exploration_complete",
        "budget_exhausted",
        "human_stop",
        "guardrail_violation",
        "provider_error",
        "predicate",
    ]
    action: Literal["terminal", "pause"] = "terminal"
    predicate_ref: CapabilityDescriptorRef | None = None

    @model_validator(mode="after")
    def validate_predicate_ref(self) -> StopCondition:
        if self.kind == "predicate" and self.predicate_ref is None:
            raise ValueError("predicate stop condition requires a predicate_ref")
        if self.kind != "predicate" and self.predicate_ref is not None:
            raise ValueError("predicate_ref is only valid for predicate stop conditions")
        return self


class CapturePolicySpec(ContractModel):
    default_mode: Literal["metadata", "redacted", "raw_encrypted", "disabled"]
    raw_sensitive: Literal["disabled", "opt_in"] = "disabled"
    sensitive_ttl_days: int = Field(default=30, gt=0)


class RunBlueprint(ContractModel):
    agent_inventory_ref: ContractRef
    workspace_template_ref: ContractRef
    interaction_protocol_ref: ContractRef
    evaluation_plan_ref: ContractRef
    checkpoint_policy_ref: ContractRef | None = None
    progress_artifact_policy_ref: ContractRef | None = None
    context_policy: ContextPolicySpec | None = None
    budgets: BudgetSpec
    stop_conditions: tuple[StopCondition, ...]
    capture_policy: CapturePolicySpec
    extensions: tuple[ExtensionRef, ...] = ()

    @model_validator(mode="after")
    def validate_stops(self) -> RunBlueprint:
        if not self.stop_conditions:
            raise ValueError("run blueprint requires at least one stop condition")
        expected_refs = (
            (self.agent_inventory_ref, ContractType.AGENT_INVENTORY),
            (self.workspace_template_ref, ContractType.WORKSPACE_TEMPLATE),
            (self.interaction_protocol_ref, ContractType.INTERACTION_PROTOCOL),
            (self.evaluation_plan_ref, ContractType.EVALUATION_PLAN),
        )
        if any(reference.contract_type != expected for reference, expected in expected_refs):
            raise ValueError("run blueprint contains a reference in the wrong contract slot")
        if (
            self.checkpoint_policy_ref is not None
            and self.checkpoint_policy_ref.contract_type != ContractType.CHECKPOINT_POLICY
        ):
            raise ValueError("checkpoint policy slot requires a checkpoint_policy ref")
        if (
            self.progress_artifact_policy_ref is not None
            and self.progress_artifact_policy_ref.contract_type
            != ContractType.PROGRESS_ARTIFACT_POLICY
        ):
            raise ValueError(
                "progress artifact policy slot requires a progress_artifact_policy ref"
            )
        return self


class VariantOverrides(ContractModel):
    goal_ref: ContractRef | None = None
    scenario_ref: ContractRef | None = None
    agent_inventory_ref: ContractRef | None = None
    workspace_template_ref: ContractRef | None = None
    interaction_protocol_ref: ContractRef | None = None
    evaluation_plan_ref: ContractRef | None = None
    checkpoint_policy_ref: ContractRef | None = None
    progress_artifact_policy_ref: ContractRef | None = None
    context_policy: ContextPolicySpec | None = None
    budgets: BudgetSpec | None = None
    stop_conditions: tuple[StopCondition, ...] | None = None
    capture_policy: CapturePolicySpec | None = None
    extensions: tuple[ExtensionRef, ...] | None = None

    @model_validator(mode="after")
    def validate_ref_slots(self) -> VariantOverrides:
        refs = (
            (self.goal_ref, ContractType.GOAL),
            (self.scenario_ref, ContractType.SCENARIO),
            (self.agent_inventory_ref, ContractType.AGENT_INVENTORY),
            (self.workspace_template_ref, ContractType.WORKSPACE_TEMPLATE),
            (self.interaction_protocol_ref, ContractType.INTERACTION_PROTOCOL),
            (self.evaluation_plan_ref, ContractType.EVALUATION_PLAN),
            (self.checkpoint_policy_ref, ContractType.CHECKPOINT_POLICY),
            (
                self.progress_artifact_policy_ref,
                ContractType.PROGRESS_ARTIFACT_POLICY,
            ),
        )
        if any(
            reference is not None and reference.contract_type != expected
            for reference, expected in refs
        ):
            raise ValueError("variant override contains a reference in the wrong contract slot")
        return self


class VariantSpec(ContractModel):
    id: NonEmptyStr
    label: NonEmptyStr
    overrides: VariantOverrides = VariantOverrides()
    confounders: tuple[NonEmptyStr, ...] = ()
    notes: NonEmptyStr | None = None


class VariantSlot(str):
    """Validated namespaced variable slot without allowing JSON Pointer."""


VARIANT_SLOTS = frozenset(
    {
        "goal",
        "scenario",
        "agent_inventory",
        "workspace_template",
        "interaction_protocol",
        "evaluation_plan",
        "checkpoint_policy",
        "progress_artifact_policy",
        "context_policy",
        "budgets",
        "stop_conditions",
        "capture_policy",
        "extensions",
    }
)


class ComparisonPlan(ContractModel):
    baseline_variant: NonEmptyStr
    candidate_variant: NonEmptyStr
    primary_variable: NonEmptyStr

    @model_validator(mode="after")
    def validate_primary_variable(self) -> ComparisonPlan:
        if self.baseline_variant == self.candidate_variant:
            raise ValueError("comparison variants must be different")
        if self.primary_variable not in VARIANT_SLOTS and not self.primary_variable.startswith(
            "extension:"
        ):
            raise ValueError("comparison primary variable is not a typed variant slot")
        return self


class SeedStrategy(ContractModel):
    kind: Literal["deterministic", "fixed", "per_repetition"]
    seed: int | None = None

    @model_validator(mode="after")
    def validate_seed(self) -> SeedStrategy:
        if self.kind == "fixed" and self.seed is None:
            raise ValueError("fixed seed strategy requires a seed")
        if self.kind == "deterministic" and self.seed is not None:
            raise ValueError("deterministic seed strategy does not accept an explicit seed")
        return self


class StudySpec(ContractModel):
    intent: StudyIntent
    evidence_mode: EvidenceMode
    goal_ref: ContractRef
    scenario_refs: tuple[ContractRef, ...]
    run_blueprint: RunBlueprint
    variants: tuple[VariantSpec, ...] = (
        VariantSpec(id="default", label="Default"),
    )
    repetitions: int = Field(default=1, gt=0)
    seed_strategy: SeedStrategy = SeedStrategy(kind="deterministic")
    comparisons: tuple[ComparisonPlan, ...] = ()
    limitations: tuple[NonEmptyStr, ...] = ()
    tags: tuple[NonEmptyStr, ...] = ()

    @model_validator(mode="after")
    def validate_matrix(self) -> StudySpec:
        if not self.scenario_refs:
            raise ValueError("study requires at least one scenario")
        scenario_keys = [
            (item.contract_type, item.logical_id, item.revision, item.digest)
            for item in self.scenario_refs
        ]
        if len(scenario_keys) != len(set(scenario_keys)):
            raise ValueError("study scenario refs must be unique")
        if self.goal_ref.contract_type != ContractType.GOAL or any(
            item.contract_type != ContractType.SCENARIO for item in self.scenario_refs
        ):
            raise ValueError("study Goal or scenario reference has the wrong contract type")
        variant_ids = [item.id for item in self.variants]
        if not variant_ids:
            raise ValueError("study requires at least one variant")
        if len(variant_ids) != len(set(variant_ids)):
            raise ValueError("study variant ids must be unique")
        if len(self.scenario_refs) > 1 and any(
            variant.overrides.scenario_ref is not None for variant in self.variants
        ):
            raise ValueError(
                "scenario overrides are ambiguous when the Study matrix has multiple scenarios"
            )
        known = set(variant_ids)
        for comparison in self.comparisons:
            if (
                comparison.baseline_variant not in known
                or comparison.candidate_variant not in known
            ):
                raise ValueError("comparison references unknown variant")
        if self.evidence_mode == EvidenceMode.PROSPECTIVE_CONTROLLED and not self.comparisons:
            raise ValueError("prospective_controlled study requires a comparison")
        if self.evidence_mode != EvidenceMode.EXPLORATORY and any(
            variant.confounders for variant in self.variants
        ):
            raise ValueError("variant confounders are only valid in exploratory studies")
        return self


class StudyRevision(RevisionEnvelope):
    contract_type: Literal[ContractType.STUDY] = ContractType.STUDY
    payload: StudySpec


AuthoringRevision = Annotated[
    StudyRevision
    | GoalRevision
    | ScenarioRevision
    | AgentInventoryRevision
    | WorkspaceTemplateRevision
    | InteractionProtocolRevision
    | EvaluationPlanRevision
    | CheckpointPolicyRevision
    | ProgressArtifactPolicyRevision,
    Field(discriminator="contract_type"),
]


REVISION_MODELS: dict[ContractType, type[RevisionEnvelope]] = {
    ContractType.STUDY: StudyRevision,
    ContractType.GOAL: GoalRevision,
    ContractType.SCENARIO: ScenarioRevision,
    ContractType.AGENT_INVENTORY: AgentInventoryRevision,
    ContractType.WORKSPACE_TEMPLATE: WorkspaceTemplateRevision,
    ContractType.INTERACTION_PROTOCOL: InteractionProtocolRevision,
    ContractType.EVALUATION_PLAN: EvaluationPlanRevision,
    ContractType.CHECKPOINT_POLICY: CheckpointPolicyRevision,
    ContractType.PROGRESS_ARTIFACT_POLICY: ProgressArtifactPolicyRevision,
}


def parse_revision(document: object) -> RevisionEnvelope:
    if not isinstance(document, Mapping):
        raise ValueError("contract revision must be an object")
    typed_document = cast(Mapping[str, object], document)
    raw_type = typed_document.get("contract_type")
    try:
        contract_type = ContractType(str(raw_type))
    except ValueError as exc:
        raise ValueError(f"unknown contract type: {raw_type}") from exc
    return REVISION_MODELS[contract_type].model_validate(typed_document)
