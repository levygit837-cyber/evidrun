"""One deep seam from a registered Study to an immutable execution package."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from evidrun.contracts import (
    ContractRef,
    ExecutionRevisionSet,
    ExecutionRevisionSetSealer,
    ExecutionTrustRecord,
    ReviewTarget,
    RevisionEnvelope,
    RunSpec,
    StudyRevision,
    VerifiedDecisionBinding,
    semantic_model_dump,
)
from evidrun.contracts.compiler import StudyCompiler
from evidrun.contracts.registry import ContractResolver
from evidrun.infrastructure.database import Repository
from evidrun.shared.types import new_id, utc_now


class RegisteredRevisionResolver(ContractResolver):
    """Resolve exact registered revisions regardless of human decision state."""

    def __init__(self, repository: Repository) -> None:
        self._repository = repository

    def resolve(self, reference: ContractRef) -> RevisionEnvelope:
        return self._repository.read_model.get_contract_revision_by_ref(reference)


@dataclass(frozen=True, slots=True)
class PreparedRunSpec:
    row_id: str
    spec: RunSpec
    execution_trust: ExecutionTrustRecord

    def document(self) -> dict[str, Any]:
        return {
            "id": self.row_id,
            "digest": self.spec.digest,
            "variant_id": self.spec.variant_id,
            "scenario_id": self.spec.scenario_ref.logical_id,
            "repetition_index": self.spec.repetition_index,
            "execution_trust": {
                "trust_id": self.execution_trust.trust_id,
                "digest": self.execution_trust.digest,
                "kind": self.execution_trust.kind,
            },
        }


@dataclass(frozen=True, slots=True)
class ExecutionPreparation:
    revision_set: ExecutionRevisionSet
    review_target: ReviewTarget
    run_specs: tuple[PreparedRunSpec, ...]

    def document(self) -> dict[str, Any]:
        return {
            "revision_set": {
                **semantic_model_dump(self.revision_set),
                "digest": self.revision_set.revision_set_digest,
            },
            "review_target": {
                **semantic_model_dump(self.review_target),
                "digest": self.review_target.review_target_digest,
            },
            "run_specs": [item.document() for item in self.run_specs],
        }


class ExecutionPreparationService:
    """Seal, compile and persist every execution identity in one operation."""

    def __init__(self, repository: Repository) -> None:
        self._repository = repository

    def prepare(self, study_revision_id: str) -> ExecutionPreparation:
        revision = self._repository.read_model.get_contract_revision(study_revision_id)
        if not isinstance(revision, StudyRevision):
            raise ValueError("contract revision is not a StudyRevision")
        sealed = ExecutionRevisionSetSealer(
            RegisteredRevisionResolver(self._repository)
        ).seal(revision)
        specs = StudyCompiler(sealed.resolver).compile(revision)
        decisions = self._repository.execution_trust.verified_decisions_for(
            sealed.revision_set.revision_refs
        )
        bindings = (
            tuple(
                VerifiedDecisionBinding(
                    revision_ref=decision.revision_ref,
                    decision_digest=decision.digest,
                )
                for decision in decisions
            )
            if decisions is not None
            else ()
        )
        kind = (
            "verified_revision_set"
            if decisions is not None
            else "unverified_revision_set"
        )
        prepared: list[PreparedRunSpec] = []
        for spec in specs:
            row = self._repository.catalog.save_run_spec(spec)
            candidate = ExecutionTrustRecord(
                trust_id=new_id("trust"),
                kind=kind,
                project_id=revision.project_id,
                study_ref=revision.ref,
                revision_refs=sealed.revision_set.revision_refs,
                revision_set_digest=sealed.revision_set.revision_set_digest,
                run_spec_digest=spec.digest,
                verified_decisions=bindings,
                created_at_utc=utc_now(),
            )
            trust_row = self._repository.execution_trust.save_record(candidate)
            prepared.append(
                PreparedRunSpec(
                    row_id=row.id,
                    spec=spec,
                    execution_trust=self._repository.execution_trust.get_record(
                        trust_row.id
                    ),
                )
            )
        target = ReviewTarget(
            project_id=revision.project_id,
            revision_set_digest=sealed.revision_set.revision_set_digest,
            run_spec_digests=tuple(sorted(spec.digest for spec in specs)),
        )
        self._repository.execution_trust.save_review_target(target)
        return ExecutionPreparation(
            revision_set=sealed.revision_set,
            review_target=target,
            run_specs=tuple(prepared),
        )
