from __future__ import annotations

from datetime import timedelta

import pytest

from evidrun.contracts import (
    ArtifactRef,
    ContractRef,
    ExecutionRevisionSet,
    ExecutionRevisionSetSealer,
    ExecutionTrustProjection,
    ExecutionTrustRecord,
    ReviewTarget,
    RevisionDecisionRecord,
    RevisionEnvelope,
    RunRecord,
    VerifiedDecisionBinding,
    semantic_model_dump,
    validate_verified_trust,
)
from evidrun.contracts.authority import UnavailableHumanAttestationVerifier
from evidrun.contracts.compiler import StudyCompiler
from evidrun.contracts.registry import RevisionKey
from evidrun.infrastructure.database import Repository
from evidrun.infrastructure.database.models import RunRow
from evidrun.shared.types import Classification, new_id, sha256_json, utc_now
from tests.support.human_attestation import (
    TestHumanAttestationVerifier,
    accepted_decision,
)
from tests.support.runtime_study import build_runtime_study


class RegisteredRevisionResolver:
    """Exact registered-revision seam; unlike the accepted registry, it has no decisions."""

    def __init__(self, revisions: tuple[RevisionEnvelope, ...]) -> None:
        self._revisions = {
            self._key(revision.ref): revision for revision in revisions
        }

    @staticmethod
    def _key(reference: ContractRef) -> RevisionKey:
        return (reference.contract_type, reference.logical_id, reference.revision)

    def resolve(self, reference: ContractRef) -> RevisionEnvelope:
        try:
            return self._revisions[self._key(reference)]
        except KeyError as exc:
            raise KeyError(reference.logical_id) from exc


def _draft_study(project_id: str = "project-execution-trust"):
    source = ArtifactRef(
        artifact_id="artifact:execution-trust-fixture",
        digest=sha256_json({"fixture": "execution-trust"}),
        media_type="text/plain",
        classification=Classification.INTERNAL,
    )
    return build_runtime_study(project_id=project_id, source=source)


def test_draft_study_seals_and_compiles_without_human_decisions() -> None:
    revisions, study = _draft_study()
    sealed = ExecutionRevisionSetSealer(
        RegisteredRevisionResolver(tuple(reversed(revisions)))
    ).seal(study)

    assert sealed.revision_set.study_ref == study.ref
    assert len(sealed.revision_set.revision_refs) == len(revisions)
    assert list(sealed.revision_set.revision_refs) == sorted(
        sealed.revision_set.revision_refs,
        key=lambda ref: (
            ref.contract_type.value,
            ref.logical_id,
            ref.revision,
            ref.digest,
        ),
    )
    specs = StudyCompiler(sealed.resolver).compile(study)
    assert len(specs) == 1
    assert specs[0].study_ref == study.ref
    with pytest.raises(KeyError, match="outside the sealed set"):
        sealed.resolver.resolve(
            ContractRef(
                contract_type=study.ref.contract_type,
                logical_id="future-study",
                revision=1,
                digest="f" * 64,
            )
        )


def test_sealer_rejects_project_crossing_and_digest_drift() -> None:
    revisions, study = _draft_study()
    goal = revisions[0]
    crossed_goal = goal.model_copy(update={"project_id": "another-project"})
    crossed = (crossed_goal, *revisions[1:])
    with pytest.raises(ValueError, match="Project boundary"):
        ExecutionRevisionSetSealer(
            RegisteredRevisionResolver(crossed)
        ).seal(study)

    bad_goal_ref = study.payload.goal_ref.model_copy(update={"digest": "0" * 64})
    drifted_study = study.model_copy(
        update={"payload": study.payload.model_copy(update={"goal_ref": bad_goal_ref})}
    )
    drifted_revisions = (*revisions[:-1], drifted_study)
    with pytest.raises(ValueError, match="does not reproduce"):
        ExecutionRevisionSetSealer(
            RegisteredRevisionResolver(drifted_revisions)
        ).seal(drifted_study)


def test_sealer_rejects_missing_conflicting_and_unsupported_refs() -> None:
    revisions, study = _draft_study()
    with pytest.raises(KeyError, match=study.payload.goal_ref.logical_id):
        ExecutionRevisionSetSealer(
            RegisteredRevisionResolver(revisions[1:])
        ).seal(study)

    conflicting_goal = study.payload.goal_ref.model_copy(update={"digest": "c" * 64})
    variant = study.payload.variants[0].model_copy(
        update={
            "overrides": study.payload.variants[0].overrides.model_copy(
                update={"goal_ref": conflicting_goal}
            )
        }
    )
    conflicting_study = study.model_copy(
        update={"payload": study.payload.model_copy(update={"variants": (variant,)})}
    )
    with pytest.raises(ValueError, match="different digests"):
        ExecutionRevisionSetSealer(
            RegisteredRevisionResolver((*revisions[:-1], conflicting_study))
        ).seal(conflicting_study)

    cyclic_study = study.model_copy(
        update={
            "payload": study.payload.model_copy(update={"goal_ref": study.ref})
        }
    )
    with pytest.raises(ValueError, match="unsupported or cyclic"):
        ExecutionRevisionSetSealer(
            RegisteredRevisionResolver((*revisions[:-1], cyclic_study))
        ).seal(cyclic_study)


def test_trust_and_review_target_require_canonical_complete_bindings() -> None:
    revisions, study = _draft_study()
    sealed = ExecutionRevisionSetSealer(
        RegisteredRevisionResolver(revisions)
    ).seal(study)
    spec = StudyCompiler(sealed.resolver).compile(study)[0]
    now = utc_now()
    unverified = ExecutionTrustRecord(
        trust_id=new_id("trust"),
        kind="unverified_revision_set",
        project_id=study.project_id,
        study_ref=study.ref,
        revision_refs=sealed.revision_set.revision_refs,
        revision_set_digest=sealed.revision_set.revision_set_digest,
        run_spec_digest=spec.digest,
        created_at_utc=now,
    )
    assert unverified.ref.digest == unverified.digest

    bindings = tuple(
        VerifiedDecisionBinding(
            revision_ref=reference,
            decision_digest=sha256_json({"accepted": reference.digest}),
        )
        for reference in sealed.revision_set.revision_refs
    )
    verified = unverified.model_copy(
        update={"kind": "verified_revision_set", "verified_decisions": bindings}
    )
    assert ExecutionTrustRecord.model_validate(verified).kind == "verified_revision_set"

    with pytest.raises(ValueError, match="cannot bind verified decisions"):
        ExecutionTrustRecord.model_validate(
            unverified.model_copy(update={"verified_decisions": bindings})
        )
    with pytest.raises(ValueError, match="cover every revision"):
        ExecutionTrustRecord.model_validate(
            verified.model_copy(update={"verified_decisions": bindings[:-1]})
        )
    with pytest.raises(ValueError, match="canonical order"):
        ReviewTarget(
            project_id=study.project_id,
            revision_set_digest=sealed.revision_set.revision_set_digest,
            run_spec_digests=("b" * 64, "a" * 64),
        )


def test_verified_trust_requires_exact_decisions_and_a_trusted_human_verifier() -> None:
    revisions, study = _draft_study()
    sealed = ExecutionRevisionSetSealer(
        RegisteredRevisionResolver(revisions)
    ).seal(study)
    spec = StudyCompiler(sealed.resolver).compile(study)[0]
    decisions = tuple(accepted_decision(revision) for revision in sealed.revisions)
    bindings = tuple(
        VerifiedDecisionBinding(
            revision_ref=decision.revision_ref,
            decision_digest=decision.digest,
        )
        for decision in decisions
    )
    record = ExecutionTrustRecord(
        trust_id=new_id("trust"),
        kind="verified_revision_set",
        project_id=study.project_id,
        study_ref=study.ref,
        revision_refs=sealed.revision_set.revision_refs,
        revision_set_digest=sealed.revision_set.revision_set_digest,
        run_spec_digest=spec.digest,
        verified_decisions=bindings,
        created_at_utc=utc_now(),
    )

    assert (
        validate_verified_trust(record, decisions, TestHumanAttestationVerifier())
        == record
    )
    with pytest.raises(ValueError, match="does not match"):
        validate_verified_trust(
            record,
            tuple(reversed(decisions)),
            TestHumanAttestationVerifier(),
        )
    replayed_document = semantic_model_dump(decisions[0])
    replayed_document["revision_ref"] = semantic_model_dump(decisions[1].revision_ref)
    with pytest.raises(ValueError, match="attestation target does not match"):
        RevisionDecisionRecord.model_validate(replayed_document)
    with pytest.raises(ValueError, match="authority is unavailable"):
        validate_verified_trust(record, decisions, UnavailableHumanAttestationVerifier())


def test_trust_store_is_idempotent_by_semantic_content(repository: Repository) -> None:
    workspace = repository.catalog.create_workspace("Execution Trust Workspace")
    project = repository.catalog.create_project(workspace.id, "Execution Trust Project")
    revisions, study = _draft_study(project.id)
    for revision in revisions:
        repository.registry.save_contract_revision(revision)
    sealed = ExecutionRevisionSetSealer(
        RegisteredRevisionResolver(revisions)
    ).seal(study)
    spec = StudyCompiler(sealed.resolver).compile(study)[0]
    spec_row = repository.catalog.save_run_spec(spec)
    first = ExecutionTrustRecord(
        trust_id=new_id("trust"),
        kind="unverified_revision_set",
        project_id=project.id,
        study_ref=study.ref,
        revision_refs=sealed.revision_set.revision_refs,
        revision_set_digest=sealed.revision_set.revision_set_digest,
        run_spec_digest=spec.digest,
        created_at_utc=utc_now(),
    )
    first_row = repository.execution_trust.save_record(first)
    fabricated_spec = spec.model_copy(update={"limitations": ("not compiled",)})
    repository.catalog.save_run_spec(fabricated_spec)
    fabricated_trust = first.model_copy(
        update={
            "trust_id": new_id("trust"),
            "run_spec_digest": fabricated_spec.digest,
            "created_at_utc": first.created_at_utc + timedelta(milliseconds=1),
        }
    )
    with pytest.raises(ValueError, match="was not compiled"):
        repository.execution_trust.save_record(fabricated_trust)
    equivalent = first.model_copy(
        update={
            "trust_id": new_id("trust"),
            "created_at_utc": first.created_at_utc + timedelta(seconds=1),
        }
    )
    second_row = repository.execution_trust.save_record(equivalent)

    assert second_row.id == first_row.id
    assert repository.execution_trust.get_record(first_row.id) == first
    run_id = new_id("run")
    with repository.unit_of_work.session() as session:
        session.add(
            RunRow(
                id=run_id,
                experiment_revision_id=None,
                variant_id="default",
                repetition=1,
                status="draft",
                runner="fixture",
                objective="exercise explicit trust projection",
                execution_trust_id=first_row.id,
                execution_trust_digest=first_row.digest,
                created_at=utc_now(),
            )
        )
        session.commit()
    projection = repository.read_model.get_run_execution_trust(run_id)
    assert projection.status == "recorded"
    assert projection.trust_id == first_row.id
    assert projection.digest == first_row.digest
    assert projection.kind == "unverified_revision_set"
    target = ReviewTarget(
        project_id=project.id,
        revision_set_digest=sealed.revision_set.revision_set_digest,
        run_spec_digests=(spec_row.digest,),
    )
    target_row = repository.execution_trust.save_review_target(target)
    assert target_row.digest == target.review_target_digest
    assert repository.execution_trust.get_review_target(target_row.digest) == target

    bindings = tuple(
        VerifiedDecisionBinding(
            revision_ref=reference,
            decision_digest=sha256_json({"fabricated": reference.digest}),
        )
        for reference in first.revision_refs
    )
    fabricated_verified = ExecutionTrustRecord.model_validate(
        first.model_copy(
            update={
                "trust_id": new_id("trust"),
                "kind": "verified_revision_set",
                "verified_decisions": bindings,
                "created_at_utc": first.created_at_utc + timedelta(seconds=2),
            }
        )
    )
    with pytest.raises(ValueError, match="unknown decision"):
        repository.execution_trust.save_record(fabricated_verified)

    other_project = repository.catalog.create_project(workspace.id, "Other Project")
    crossed_set = ExecutionRevisionSet(
        project_id=other_project.id,
        study_ref=study.ref,
        revision_refs=first.revision_refs,
    )
    crossed = first.model_copy(
        update={
            "trust_id": new_id("trust"),
            "project_id": other_project.id,
            "revision_set_digest": crossed_set.revision_set_digest,
            "created_at_utc": first.created_at_utc + timedelta(seconds=3),
        }
    )
    with pytest.raises(ValueError, match="Project boundary"):
        repository.execution_trust.save_record(crossed)


def test_review_target_requires_the_complete_compiled_matrix(
    repository: Repository,
) -> None:
    workspace = repository.catalog.create_workspace("Review Matrix Workspace")
    project = repository.catalog.create_project(workspace.id, "Review Matrix Project")
    revisions, original_study = _draft_study(project.id)
    study = original_study.model_copy(
        update={
            "payload": original_study.payload.model_copy(update={"repetitions": 2})
        }
    )
    matrix_revisions = (*revisions[:-1], study)
    for revision in matrix_revisions:
        repository.registry.save_contract_revision(revision)
    sealed = ExecutionRevisionSetSealer(
        RegisteredRevisionResolver(matrix_revisions)
    ).seal(study)
    specs = StudyCompiler(sealed.resolver).compile(study)
    assert len(specs) == 2
    for spec in specs:
        repository.catalog.save_run_spec(spec)
        repository.execution_trust.save_record(
            ExecutionTrustRecord(
                trust_id=new_id("trust"),
                kind="unverified_revision_set",
                project_id=project.id,
                study_ref=study.ref,
                revision_refs=sealed.revision_set.revision_refs,
                revision_set_digest=sealed.revision_set.revision_set_digest,
                run_spec_digest=spec.digest,
                created_at_utc=utc_now(),
            )
        )

    with pytest.raises(ValueError, match="complete compiled RunSpec matrix"):
        repository.execution_trust.save_review_target(
            ReviewTarget(
                project_id=project.id,
                revision_set_digest=sealed.revision_set.revision_set_digest,
                run_spec_digests=(specs[0].digest,),
            )
        )

    complete = ReviewTarget(
        project_id=project.id,
        revision_set_digest=sealed.revision_set.revision_set_digest,
        run_spec_digests=tuple(sorted(spec.digest for spec in specs)),
    )
    row = repository.execution_trust.save_review_target(complete)
    assert row.digest == complete.review_target_digest


def test_legacy_run_record_omits_absent_execution_trust(repository: Repository) -> None:
    _, study = _draft_study()
    record = RunRecord(
        run_id=new_id("run"),
        run_spec_id="rspec_legacy",
        run_spec_digest="a" * 64,
        admission_id="adm_legacy",
        admission_digest="b" * 64,
        study_ref=study.ref,
        scenario_ref=study.payload.scenario_refs[0],
        variant_id="default",
        repetition_index=1,
        created_at_utc=utc_now(),
    )
    assert "execution_trust" not in semantic_model_dump(record)
    with repository.unit_of_work.session() as session:
        session.add(
            RunRow(
                id=record.run_id,
                experiment_revision_id=None,
                variant_id="default",
                repetition=1,
                status="legacy",
                runner="fixture",
                objective="preserve unknown legacy trust",
                created_at=record.created_at_utc,
            )
        )
        session.commit()
    stored_projection = repository.read_model.get_run_execution_trust(record.run_id)
    assert semantic_model_dump(stored_projection) == {"status": "not_recorded"}
    legacy_document = next(
        item
        for item in repository.read_model.latest_dashboard()["runs"]
        if item["id"] == record.run_id
    )
    assert legacy_document["execution_trust"] == {"status": "not_recorded"}
    assert legacy_document["isolation"] == "not_recorded"
    projection = ExecutionTrustProjection(status="not_recorded")
    assert semantic_model_dump(projection) == {"status": "not_recorded"}
    with pytest.raises(ValueError, match="cannot infer"):
        ExecutionTrustProjection(
            status="not_recorded",
            trust_id="trust_fabricated",
            digest="f" * 64,
            kind="verified_revision_set",
        )
