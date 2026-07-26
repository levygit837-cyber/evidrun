"""Study, variantes e plano de comparação: o que compila em RunSpec."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from evidrun.contracts.authoring.run import (
    BudgetSpec,
    CapturePolicySpec,
    RunBlueprint,
    StopCondition,
)
from evidrun.contracts.authoring.study_intent import StudyIntent
from evidrun.contracts.base import (
    ContractModel,
    ContractRef,
    ContractType,
    ExtensionRef,
    NonEmptyStr,
    RevisionEnvelope,
)
from evidrun.experiments.models import ContextPolicySpec
from evidrun.shared.types import EvidenceMode


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
