"""SubjectEnvelope and EvaluatorEnvelope: closed disclosure allowlists.

A new RunSpec, contract, artifact or evaluation field does NOT enter here automatically.
"""

from __future__ import annotations

from typing import Literal

from pydantic import computed_field, model_validator

from evidrun.contracts.authoring.evaluation import EvaluationDimension, EvaluationStage
from evidrun.contracts.authoring.goal import GoalSpec
from evidrun.contracts.authoring.protocol import InteractionProtocolSpec
from evidrun.contracts.authoring.run import BudgetSpec, StopCondition
from evidrun.contracts.authoring.scenario import InputBinding
from evidrun.contracts.base import (
    ArtifactRef,
    ContractModel,
    ContractRef,
    ContractType,
    Digest,
    KeyValue,
    NonEmptyStr,
    UtcDateTime,
    semantic_model_dump,
)
from evidrun.contracts.runtime.spec import ResolvedCapability
from evidrun.shared.types import sha256_json


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
    effective_capabilities: tuple[ResolvedCapability, ...] = ()
    workspace: SubjectWorkspace
    budgets: BudgetSpec
    stop_conditions: tuple[StopCondition, ...]
    evaluation_guidance: SubjectEvaluationGuidance | None = None

    @computed_field
    @property
    def digest(self) -> str:
        return sha256_json(semantic_model_dump(self))


class SubjectEnvelopeRecord(ContractModel):
    """The exact materialized SubjectEnvelope used for one Run."""

    schema_version: Literal["1"] = "1"
    run_id: NonEmptyStr
    envelope: SubjectEnvelope
    created_at_utc: UtcDateTime

    @computed_field
    @property
    def digest(self) -> str:
        return self.envelope.digest


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
