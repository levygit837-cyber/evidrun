"""O RunSpec admitido e a resolução de inventário que a admissão produz."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, computed_field, model_validator

from evidrun.contracts.authoring.checkpoint import CheckpointPolicySpec
from evidrun.contracts.authoring.evaluation import EvaluationPlanSpec
from evidrun.contracts.authoring.goal import GoalSpec
from evidrun.contracts.authoring.inventory import AgentInventorySpec
from evidrun.contracts.authoring.progress import ProgressArtifactPolicySpec
from evidrun.contracts.authoring.protocol import InteractionProtocolSpec
from evidrun.contracts.authoring.run import BudgetSpec, CapturePolicySpec, StopCondition
from evidrun.contracts.authoring.scenario import ScenarioSpec
from evidrun.contracts.authoring.workspace import WorkspaceTemplateSpec
from evidrun.contracts.base import (
    ArtifactRef,
    CapabilityDescriptorRef,
    ContractModel,
    ContractRef,
    ContractType,
    Digest,
    ExtensionRef,
    NonEmptyStr,
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
