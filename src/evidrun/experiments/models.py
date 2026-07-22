from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from evidrun.shared.types import EvidenceMode, sha256_json


class ContextPolicySpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    strategy: Literal["head", "tail", "full"]
    max_chars: int = Field(gt=0)


class VariantSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    label: str
    context_policy: str
    confounders: tuple[str, ...] = ()


class SubjectProfile(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    runner: str
    model: str | None = None


class GraderSpec(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    id: str
    type: str
    expected: str


class ExperimentManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1"]
    id: str
    project_id: str
    title: str
    objective: str
    hypothesis: str
    evidence_mode: EvidenceMode
    scenario_refs: tuple[str, ...]
    baseline_variant: str
    variants: tuple[VariantSpec, ...]
    primary_variable: str
    subject_profile: SubjectProfile
    context_policies: tuple[ContextPolicySpec, ...]
    tools: tuple[dict[str, Any], ...] = ()
    environment: dict[str, Any] = Field(default_factory=dict)
    budgets: dict[str, Any] = Field(default_factory=dict)
    approvals: tuple[dict[str, Any], ...] = ()
    capture_policy: dict[str, Any] = Field(default_factory=dict)
    repetitions: int = Field(default=1, gt=0)
    seed_strategy: dict[str, Any] = Field(default_factory=dict)
    graders: tuple[GraderSpec, ...]
    comparison_plan: dict[str, Any] = Field(default_factory=dict)
    stop_conditions: dict[str, Any] = Field(default_factory=dict)
    tags: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_references(self) -> ExperimentManifest:
        variant_ids = [variant.id for variant in self.variants]
        if len(variant_ids) != len(set(variant_ids)):
            raise ValueError("variant ids must be unique")
        if self.baseline_variant not in variant_ids:
            raise ValueError("baseline_variant must reference a declared variant")
        policy_ids = {policy.id for policy in self.context_policies}
        missing = [v.context_policy for v in self.variants if v.context_policy not in policy_ids]
        if missing:
            raise ValueError(f"unknown context policies: {', '.join(missing)}")
        return self

    @property
    def validity(self) -> str:
        if any(variant.confounders for variant in self.variants):
            return "exploratory"
        if self.evidence_mode is not EvidenceMode.PROSPECTIVE_CONTROLLED:
            return self.evidence_mode.value
        return "controlled"

    @property
    def digest(self) -> str:
        return sha256_json(self.model_dump(mode="json"))

    def policy_for(self, variant: VariantSpec) -> ContextPolicySpec:
        return next(
            policy for policy in self.context_policies if policy.id == variant.context_policy
        )
