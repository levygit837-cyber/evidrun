"""Canonical append-only records: admission, Run, evaluation, checkpoint, progress.

A correction creates a new record; none of these is rewritten in place.
"""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, computed_field, field_validator, model_validator

from evidrun.contracts.base import (
    ArtifactRef,
    CapabilityDescriptorRef,
    ContractModel,
    ContractRef,
    ContractType,
    Digest,
    EvidenceRef,
    HumanAttestationRecord,
    NonEmptyStr,
    UtcDateTime,
    semantic_model_dump,
)
from evidrun.contracts.runtime.spec import (
    AdmissionIssue,
    ResolvedAgentInventory,
)
from evidrun.shared.types import sha256_json


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
