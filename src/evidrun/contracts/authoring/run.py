"""What a Run declares before it exists: budget, stop conditions and capture."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from evidrun.contracts.base import (
    CapabilityDescriptorRef,
    ContractModel,
    ContractRef,
    ContractType,
    ExtensionRef,
)
from evidrun.experiments.models import ContextPolicySpec


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
