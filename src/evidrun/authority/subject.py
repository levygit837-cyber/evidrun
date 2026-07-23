from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from evidrun.contracts.base import (
    CapabilityDescriptorRef,
    ContractModel,
    ContractRef,
    ContractType,
    HumanAttestationRecord,
    NonEmptyStr,
    RevisionDecisionRecord,
    VerifiedHumanDecisionAuthority,
)
from evidrun.contracts.runtime import (
    AdjudicatesEvaluationRelation,
    DimensionValue,
    EvaluationBoundary,
    EvaluationRecord,
    HumanEvaluationRelation,
    IndependentHumanReviewRelation,
)
from evidrun.shared.types import sha256_json

# Canonical human-authority actions. Mirrors the closed set on
# HumanAttestationRecord.action.
RevisionAction = Literal["revision.accepted", "revision.rejected", "revision.superseded"]
EvaluationAction = Literal["evaluation.reviewed", "evaluation.adjudicated"]


class RevisionDecisionSubject(ContractModel):
    """The exact revision-decision content a human confirms.

    This is the single source of truth for what is signed. Its subject_digest must
    equal RevisionDecisionRecord.human_subject_digest() (guarded by a drift test),
    because the kernel validators compare the attestation against that value.
    """

    kind: Literal["revision_decision"] = "revision_decision"
    revision_ref: ContractRef
    decision: Literal["accepted", "rejected", "superseded"]
    rationale: NonEmptyStr

    @property
    def action(self) -> RevisionAction:
        return f"revision.{self.decision}"  # type: ignore[return-value]

    @property
    def target_digest(self) -> str:
        return self.revision_ref.digest

    def subject_digest(self) -> str:
        return sha256_json(
            {
                "revision_ref": self.revision_ref.model_dump(mode="json"),
                "decision": self.decision,
                "rationale": self.rationale,
            }
        )

    def build_decision(
        self,
        attestation: HumanAttestationRecord,
    ) -> RevisionDecisionRecord:
        return RevisionDecisionRecord(
            revision_ref=self.revision_ref,
            decision=self.decision,
            authority=VerifiedHumanDecisionAuthority(
                principal_id=attestation.principal_id,
                attestation=attestation,
            ),
            rationale=self.rationale,
            decided_at_utc=attestation.verified_at_utc,
        )


class EvaluationDecisionSubject(ContractModel):
    """The exact human evaluation content a human confirms.

    subject_digest() must equal EvaluationRecord.human_subject_digest().
    """

    kind: Literal["evaluation_decision"] = "evaluation_decision"
    source_type: Literal["human_reviewer", "human_adjudicator"]
    record_id: NonEmptyStr
    run_id: NonEmptyStr
    plan_ref: ContractRef
    stage_id: NonEmptyStr
    evaluator_ref: CapabilityDescriptorRef
    boundary: EvaluationBoundary
    dimension_values: tuple[DimensionValue, ...]
    gate_status: Literal["passed", "failed", "not_applicable"]
    relation: HumanEvaluationRelation

    @property
    def status(self) -> Literal["final"]:
        return "final"

    @property
    def action(self) -> EvaluationAction:
        return (
            "evaluation.adjudicated"
            if self.source_type == "human_adjudicator"
            else "evaluation.reviewed"
        )

    @property
    def target_digest(self) -> str:
        return self.plan_ref.digest

    def subject_digest(self) -> str:
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
                "relation": self.relation.model_dump(mode="json"),
            }
        )

    def build_evaluation(
        self,
        attestation: HumanAttestationRecord,
    ) -> EvaluationRecord:
        return EvaluationRecord(
            record_id=self.record_id,
            run_id=self.run_id,
            plan_ref=self.plan_ref,
            stage_id=self.stage_id,
            source_type=self.source_type,
            evaluator_ref=self.evaluator_ref,
            boundary=self.boundary,
            dimension_values=self.dimension_values,
            gate_status=self.gate_status,
            status="final",
            relation=self.relation,
            human_attestation=attestation,
            created_at_utc=attestation.verified_at_utc,
        )

    def validate_role(self) -> None:
        if self.source_type == "human_adjudicator" and not isinstance(
            self.relation, AdjudicatesEvaluationRelation
        ):
            raise ValueError("adjudication requires an adjudicates relation")
        if self.source_type == "human_reviewer" and not isinstance(
            self.relation, IndependentHumanReviewRelation
        ):
            raise ValueError("review requires an independent_review relation")
        if self.plan_ref.contract_type != ContractType.EVALUATION_PLAN:
            raise ValueError("evaluation subject requires an evaluation_plan ref")


HumanSubjectEnvelope = Annotated[
    RevisionDecisionSubject | EvaluationDecisionSubject,
    Field(discriminator="kind"),
]
