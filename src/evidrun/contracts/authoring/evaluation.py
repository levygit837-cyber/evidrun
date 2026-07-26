"""Plano de avaliação: dimensões, stages, disclosure e adjudicação humana."""

from __future__ import annotations

from typing import Literal

from pydantic import model_validator

from evidrun.contracts.base import (
    ArtifactRef,
    CapabilityDescriptorRef,
    ContractModel,
    ContractType,
    KeyValue,
    NonEmptyStr,
    RevisionEnvelope,
)


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
