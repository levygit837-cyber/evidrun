"""Readable ReviewPackage projection; ReviewTarget remains its only identity."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from evidrun.contracts.authoring.evaluation import (
    EvaluationPlanSpec,
    SubjectEvaluationDisclosure,
)
from evidrun.contracts.authoring.inventory import CapabilityRequirement
from evidrun.contracts.authoring.workspace import ExternalEffectPolicy, NetworkPolicy
from evidrun.contracts.base import (
    ArtifactRef,
    ContractModel,
    ContractRef,
    ContractType,
    Digest,
    NonEmptyStr,
)
from evidrun.contracts.execution_trust import ReviewTarget
from evidrun.contracts.runtime.spec import AdmissionIssue, RunSpec
from evidrun.shared.types import Classification


def _ref_key(reference: ContractRef) -> tuple[str, str, int, str]:
    return (
        reference.contract_type.value,
        reference.logical_id,
        reference.revision,
        reference.digest,
    )


class ReviewRevisionDocument(ContractModel):
    """One exact closure member expanded for human review."""

    ref: ContractRef
    document: dict[str, Any]


class ReviewRunSpec(ContractModel):
    """One RunSpec plus the security-relevant fields readers must not hunt for."""

    run_spec_digest: Digest
    run_spec: RunSpec
    subject_disclosure: SubjectEvaluationDisclosure
    capability_requirements: tuple[CapabilityRequirement, ...] = ()
    requested_permissions: tuple[NonEmptyStr, ...] = ()
    classifications: tuple[Classification, ...] = ()
    network: NetworkPolicy
    external_effects: ExternalEffectPolicy
    evaluation_plan: EvaluationPlanSpec
    hidden_input_refs: tuple[ArtifactRef, ...] = ()
    limitations: tuple[NonEmptyStr, ...] = ()
    isolation: NonEmptyStr
    known_admission_refusals: tuple[AdmissionIssue, ...] = ()
    missing_requirements: tuple[NonEmptyStr, ...] = ()
    denied_policies: tuple[NonEmptyStr, ...] = ()

    @model_validator(mode="after")
    def validate_projection(self) -> ReviewRunSpec:
        spec = self.run_spec
        if self.run_spec_digest != spec.digest:
            raise ValueError("ReviewPackage RunSpec digest does not recompute")
        if self.subject_disclosure != spec.evaluation_plan.disclosure.subject:
            raise ValueError("ReviewPackage disclosure does not match its RunSpec")
        if self.capability_requirements != spec.agent_inventory.capability_requirements:
            raise ValueError("ReviewPackage capabilities do not match its RunSpec")
        if self.network != spec.workspace.network_policy:
            raise ValueError("ReviewPackage network does not match its RunSpec")
        if self.external_effects != spec.workspace.external_effect_policy:
            raise ValueError("ReviewPackage external effects do not match its RunSpec")
        if self.evaluation_plan != spec.evaluation_plan:
            raise ValueError("ReviewPackage evaluation plan does not match its RunSpec")
        if self.hidden_input_refs != spec.evaluation_plan.disclosure.hidden_input_refs:
            raise ValueError("ReviewPackage hidden inputs do not match its RunSpec")
        if self.isolation != spec.workspace.runtime_kind:
            raise ValueError("ReviewPackage isolation does not match its RunSpec")
        return self


class ReviewRevisionChange(ContractModel):
    contract_type: ContractType
    logical_id: NonEmptyStr
    before: ContractRef
    after: ContractRef


class ReviewRunSpecChange(ContractModel):
    slot: NonEmptyStr
    before_digest: Digest
    after_digest: Digest


class ReviewPackageDiff(ContractModel):
    """Deterministic semantic difference from one earlier persisted target."""

    base_review_target_digest: Digest
    revision_refs_added: tuple[ContractRef, ...] = ()
    revision_refs_removed: tuple[ContractRef, ...] = ()
    revision_refs_changed: tuple[ReviewRevisionChange, ...] = ()
    run_specs_added: tuple[Digest, ...] = ()
    run_specs_removed: tuple[Digest, ...] = ()
    run_specs_changed: tuple[ReviewRunSpecChange, ...] = ()
    semantic_changes: tuple[NonEmptyStr, ...] = ()


class ReviewPackage(ContractModel):
    """Readable projection whose only semantic identity is its ReviewTarget."""

    schema_version: Literal["1"] = "1"
    review_target: ReviewTarget
    review_target_digest: Digest
    study_ref: ContractRef
    closure: tuple[ReviewRevisionDocument, ...] = Field(min_length=1)
    run_specs: tuple[ReviewRunSpec, ...] = Field(min_length=1)
    diff: ReviewPackageDiff | None = None

    @model_validator(mode="after")
    def validate_target_coverage(self) -> ReviewPackage:
        if self.review_target.review_target_digest != self.review_target_digest:
            raise ValueError("ReviewPackage target digest does not recompute")
        refs = tuple(item.ref for item in self.closure)
        if self.study_ref not in refs:
            raise ValueError("ReviewPackage closure must contain its Study")
        if refs != tuple(sorted(refs, key=_ref_key)):
            raise ValueError("ReviewPackage closure must use canonical order")
        digests = tuple(sorted(item.run_spec_digest for item in self.run_specs))
        if digests != self.review_target.run_spec_digests:
            raise ValueError("ReviewPackage must cover its complete ReviewTarget")
        return self
