"""Canonical execution-trust documents and the closed Study revision-set seam."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import Field, computed_field, model_validator

from evidrun.contracts.authoring.study import StudyRevision
from evidrun.contracts.authority import HumanAttestationVerifier
from evidrun.contracts.base import (
    ContractModel,
    ContractRef,
    ContractType,
    Digest,
    NonEmptyStr,
    RevisionDecisionRecord,
    RevisionEnvelope,
    UtcDateTime,
    semantic_model_dump,
)
from evidrun.contracts.registry import ContractResolver, RevisionKey
from evidrun.contracts.runtime.spec import RunSpec
from evidrun.shared.types import sha256_json


def _ref_key(reference: ContractRef) -> tuple[str, str, int, str]:
    return (
        reference.contract_type.value,
        reference.logical_id,
        reference.revision,
        reference.digest,
    )


def _identity_key(reference: ContractRef) -> RevisionKey:
    return (reference.contract_type, reference.logical_id, reference.revision)


class ExecutionRevisionSet(ContractModel):
    """The exact, Project-bound v1 closure used to compile a Study."""

    schema_version: Literal["1"] = "1"
    project_id: NonEmptyStr
    study_ref: ContractRef
    revision_refs: tuple[ContractRef, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_closed_set(self) -> ExecutionRevisionSet:
        if self.study_ref.contract_type != ContractType.STUDY:
            raise ValueError("execution revision set requires a Study root")
        identities = [_identity_key(reference) for reference in self.revision_refs]
        if len(identities) != len(set(identities)):
            raise ValueError("execution revision refs must have unique identities")
        if self.study_ref not in self.revision_refs:
            raise ValueError("execution revision set must include its Study root")
        if self.revision_refs != tuple(sorted(self.revision_refs, key=_ref_key)):
            raise ValueError("execution revision refs must use canonical order")
        return self

    @property
    def revision_set_digest(self) -> str:
        return sha256_json(semantic_model_dump(self))


class VerifiedDecisionBinding(ContractModel):
    revision_ref: ContractRef
    decision_digest: Digest


class ExecutionTrustRef(ContractModel):
    trust_id: NonEmptyStr
    digest: Digest


class ExecutionTrustProjection(ContractModel):
    status: Literal["recorded", "not_recorded"]
    trust_id: NonEmptyStr | None = None
    digest: Digest | None = None
    kind: Literal["unverified_revision_set", "verified_revision_set"] | None = None

    @model_validator(mode="after")
    def validate_status(self) -> ExecutionTrustProjection:
        values = (self.trust_id, self.digest, self.kind)
        if self.status == "recorded" and any(value is None for value in values):
            raise ValueError("recorded execution trust requires id, digest, and kind")
        if self.status == "not_recorded" and any(value is not None for value in values):
            raise ValueError("not_recorded execution trust cannot infer record fields")
        return self


class ExecutionTrustRecord(ContractModel):
    """Immutable trust declared for one exact RunSpec."""

    schema_version: Literal["1"] = "1"
    trust_id: NonEmptyStr
    kind: Literal["unverified_revision_set", "verified_revision_set"]
    project_id: NonEmptyStr
    study_ref: ContractRef
    revision_refs: tuple[ContractRef, ...] = Field(min_length=1)
    revision_set_digest: Digest
    run_spec_digest: Digest
    verified_decisions: tuple[VerifiedDecisionBinding, ...] = ()
    created_at_utc: UtcDateTime

    @model_validator(mode="after")
    def validate_revision_set_and_binding_coverage(self) -> ExecutionTrustRecord:
        revision_set = ExecutionRevisionSet(
            project_id=self.project_id,
            study_ref=self.study_ref,
            revision_refs=self.revision_refs,
        )
        if revision_set.revision_set_digest != self.revision_set_digest:
            raise ValueError("execution trust revision-set digest does not recompute")
        if self.kind == "unverified_revision_set":
            if self.verified_decisions:
                raise ValueError("unverified execution trust cannot bind verified decisions")
            return self
        bound_refs = tuple(binding.revision_ref for binding in self.verified_decisions)
        if bound_refs != self.revision_refs:
            raise ValueError(
                "verified execution trust must cover every revision in canonical order"
            )
        return self

    @computed_field
    @property
    def digest(self) -> str:
        return sha256_json(semantic_model_dump(self))

    @property
    def semantic_identity_digest(self) -> str:
        document = semantic_model_dump(self)
        document.pop("trust_id")
        document.pop("created_at_utc")
        return sha256_json(document)

    @property
    def ref(self) -> ExecutionTrustRef:
        return ExecutionTrustRef(trust_id=self.trust_id, digest=self.digest)


class ReviewTarget(ContractModel):
    """Canonical identity of the complete RunSpec matrix for human review."""

    schema_version: Literal["1"] = "1"
    project_id: NonEmptyStr
    revision_set_digest: Digest
    run_spec_digests: tuple[Digest, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_run_specs(self) -> ReviewTarget:
        if len(self.run_spec_digests) != len(set(self.run_spec_digests)):
            raise ValueError("ReviewTarget RunSpec digests must be unique")
        if self.run_spec_digests != tuple(sorted(self.run_spec_digests)):
            raise ValueError("ReviewTarget RunSpec digests must use canonical order")
        return self

    @property
    def review_target_digest(self) -> str:
        return sha256_json(semantic_model_dump(self))


def validate_verified_trust(
    record: ExecutionTrustRecord,
    decisions: tuple[RevisionDecisionRecord, ...],
    verifier: HumanAttestationVerifier,
) -> ExecutionTrustRecord:
    """Verify every external human-authority document bound by a verified record."""

    if record.kind != "verified_revision_set":
        raise ValueError("verified trust validation requires verified_revision_set")
    if len(decisions) != len(record.verified_decisions):
        raise ValueError("verified execution trust decision count is incomplete")
    for binding, decision in zip(record.verified_decisions, decisions, strict=True):
        if (
            decision.revision_ref != binding.revision_ref
            or decision.digest != binding.decision_digest
            or decision.decision != "accepted"
        ):
            raise ValueError("verified execution trust binding does not match its decision")
        if decision.authority.kind != "verified_human":
            raise PermissionError("verified execution trust requires human authority")
        verifier.verify(
            decision.authority.attestation,
            expected_subject_digest=decision.human_subject_digest(),
        )
    return record


class SealedContractResolver(ContractResolver):
    """Resolve only exact revisions already admitted into a sealed closure."""

    def __init__(
        self,
        revision_set: ExecutionRevisionSet,
        revisions: tuple[RevisionEnvelope, ...],
    ) -> None:
        by_identity = {_identity_key(revision.ref): revision for revision in revisions}
        expected = {_identity_key(reference) for reference in revision_set.revision_refs}
        if set(by_identity) != expected:
            raise ValueError("sealed resolver revisions do not match the revision set")
        self._revisions = by_identity

    def resolve(self, reference: ContractRef) -> RevisionEnvelope:
        revision = self._revisions.get(_identity_key(reference))
        if revision is None:
            raise KeyError(
                f"revision is outside the sealed set: {reference.logical_id}@{reference.revision}"
            )
        if revision.ref != reference:
            raise ValueError("sealed contract reference digest mismatch")
        return revision


@dataclass(frozen=True)
class SealedStudy:
    revision_set: ExecutionRevisionSet
    revisions: tuple[RevisionEnvelope, ...]
    resolver: SealedContractResolver


class ExecutionRevisionSetSealer:
    """Collect and verify the closed v1 Study dependency allowlist."""

    def __init__(self, resolver: ContractResolver) -> None:
        self._resolver = resolver

    def seal(self, study: StudyRevision) -> SealedStudy:
        resolved_root = self._resolver.resolve(study.ref)
        if not isinstance(resolved_root, StudyRevision) or resolved_root != study:
            raise ValueError("Study root did not resolve to the exact registered revision")
        references = self._collect_references(resolved_root)
        ordered_refs = tuple(sorted(references.values(), key=_ref_key))
        revisions: list[RevisionEnvelope] = []
        for reference in ordered_refs:
            revision = self._resolver.resolve(reference)
            if revision.ref != reference:
                raise ValueError("resolved revision does not reproduce its reference")
            if revision.project_id != study.project_id:
                raise ValueError("execution revision set cannot cross a Project boundary")
            revisions.append(revision)
        document = ExecutionRevisionSet(
            project_id=study.project_id,
            study_ref=study.ref,
            revision_refs=ordered_refs,
        )
        typed_revisions = tuple(revisions)
        return SealedStudy(
            revision_set=document,
            revisions=typed_revisions,
            resolver=SealedContractResolver(document, typed_revisions),
        )

    @staticmethod
    def _collect_references(study: StudyRevision) -> dict[RevisionKey, ContractRef]:
        blueprint = study.payload.run_blueprint
        typed_slots = (
            (study.payload.goal_ref, ContractType.GOAL),
            *((reference, ContractType.SCENARIO) for reference in study.payload.scenario_refs),
            (blueprint.agent_inventory_ref, ContractType.AGENT_INVENTORY),
            (blueprint.workspace_template_ref, ContractType.WORKSPACE_TEMPLATE),
            (blueprint.interaction_protocol_ref, ContractType.INTERACTION_PROTOCOL),
            (blueprint.evaluation_plan_ref, ContractType.EVALUATION_PLAN),
            (blueprint.checkpoint_policy_ref, ContractType.CHECKPOINT_POLICY),
            (
                blueprint.progress_artifact_policy_ref,
                ContractType.PROGRESS_ARTIFACT_POLICY,
            ),
            *(
                item
                for variant in study.payload.variants
                for item in (
                    (variant.overrides.goal_ref, ContractType.GOAL),
                    (variant.overrides.scenario_ref, ContractType.SCENARIO),
                    (
                        variant.overrides.agent_inventory_ref,
                        ContractType.AGENT_INVENTORY,
                    ),
                    (
                        variant.overrides.workspace_template_ref,
                        ContractType.WORKSPACE_TEMPLATE,
                    ),
                    (
                        variant.overrides.interaction_protocol_ref,
                        ContractType.INTERACTION_PROTOCOL,
                    ),
                    (
                        variant.overrides.evaluation_plan_ref,
                        ContractType.EVALUATION_PLAN,
                    ),
                    (
                        variant.overrides.checkpoint_policy_ref,
                        ContractType.CHECKPOINT_POLICY,
                    ),
                    (
                        variant.overrides.progress_artifact_policy_ref,
                        ContractType.PROGRESS_ARTIFACT_POLICY,
                    ),
                )
            ),
        )
        if any(
            reference is not None and reference.contract_type != expected
            for reference, expected in typed_slots
        ):
            raise ValueError("Study closure contains an unsupported or cyclic contract ref")
        references = (study.ref, *(reference for reference, _ in typed_slots))
        collected: dict[RevisionKey, ContractRef] = {}
        for reference in references:
            if reference is None:
                continue
            identity = _identity_key(reference)
            existing = collected.get(identity)
            if existing is not None and existing != reference:
                raise ValueError("Study closure contains one identity with different digests")
            collected[identity] = reference
        return collected


def compile_execution_revision_set(
    revision_set: ExecutionRevisionSet,
    revisions: tuple[RevisionEnvelope, ...],
) -> tuple[RunSpec, ...]:
    """Reproduce the complete RunSpec matrix from one exact sealed closure."""

    # Local import keeps runtime records free of a contracts package cycle.
    from evidrun.contracts.compiler import StudyCompiler

    resolver = SealedContractResolver(revision_set, revisions)
    study = resolver.resolve(revision_set.study_ref)
    if not isinstance(study, StudyRevision):
        raise TypeError("execution revision-set root is not a StudyRevision")
    if study.project_id != revision_set.project_id:
        raise ValueError("execution revision set cannot cross a Project boundary")
    sealed = ExecutionRevisionSetSealer(resolver).seal(study)
    if sealed.revision_set != revision_set:
        raise ValueError("execution revision set does not reproduce from its Study")
    return StudyCompiler(sealed.resolver).compile(study)


def validate_execution_trust_lineage(
    record: ExecutionTrustRecord,
    run_spec: RunSpec,
    revisions: tuple[RevisionEnvelope, ...],
) -> tuple[RunSpec, ...]:
    """Prove that trust binds a RunSpec reproduced by its exact Project closure."""

    revision_set = ExecutionRevisionSet(
        project_id=record.project_id,
        study_ref=record.study_ref,
        revision_refs=record.revision_refs,
    )
    compiled = compile_execution_revision_set(revision_set, revisions)
    by_digest = {spec.digest: spec for spec in compiled}
    if (
        run_spec.digest != record.run_spec_digest
        or by_digest.get(record.run_spec_digest) != run_spec
    ):
        raise ValueError("execution trust RunSpec was not compiled from its revision set")
    return compiled


def validate_review_target_lineage(
    target: ReviewTarget,
    records: tuple[ExecutionTrustRecord, ...],
    run_specs: tuple[RunSpec, ...],
    revisions: tuple[RevisionEnvelope, ...],
) -> ReviewTarget:
    """Prove exact, complete RunSpec coverage for one Project revision set."""

    if not records:
        raise ValueError("ReviewTarget requires execution trust records")
    root = records[0]
    revision_set = ExecutionRevisionSet(
        project_id=root.project_id,
        study_ref=root.study_ref,
        revision_refs=root.revision_refs,
    )
    if (
        target.project_id != root.project_id
        or target.revision_set_digest != root.revision_set_digest
        or revision_set.revision_set_digest != target.revision_set_digest
    ):
        raise ValueError("ReviewTarget does not match its execution revision set")
    if any(
        record.project_id != target.project_id
        or record.study_ref != root.study_ref
        or record.revision_refs != root.revision_refs
        or record.revision_set_digest != target.revision_set_digest
        for record in records
    ):
        raise ValueError("ReviewTarget trust records do not share one exact revision set")

    compiled = compile_execution_revision_set(revision_set, revisions)
    compiled_by_digest = {spec.digest: spec for spec in compiled}
    expected = tuple(sorted(compiled_by_digest))
    if target.run_spec_digests != expected:
        raise ValueError("ReviewTarget must contain the complete compiled RunSpec matrix")
    stored_by_digest = {spec.digest: spec for spec in run_specs}
    if stored_by_digest != compiled_by_digest:
        raise ValueError("ReviewTarget stored RunSpecs do not reproduce the compiled matrix")
    bound = {record.run_spec_digest for record in records}
    if bound != set(expected):
        raise ValueError("ReviewTarget trust records do not cover the complete RunSpec matrix")
    return target
