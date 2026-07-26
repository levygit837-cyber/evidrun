"""Revision identity, immutability, decision authority and reference slots."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from evidrun.contracts import (
    ArtifactRef,
    ExtensionRef,
    HumanAttestationRecord,
    RevisionDecisionRecord,
    StudyRevision,
    VerifiedHumanDecisionAuthority,
    semantic_model_dump,
)
from evidrun.contracts.authority import HumanAttestationUnavailable
from evidrun.contracts.base import ContractModel
from evidrun.contracts.legacy import (
    capability_ref,
)
from evidrun.contracts.registry import InMemoryContractRegistry
from evidrun.shared.types import (
    sha256_json,
    utc_now,
)
from tests.support.contract_fixtures import (
    legacy_package,
)


def test_revision_is_closed_immutable_and_has_stable_digest() -> None:
    _, package = legacy_package()
    study = package.study
    copy = StudyRevision.model_validate(study.semantic_document())
    assert copy.digest == study.digest
    with pytest.raises(ValidationError):
        StudyRevision.model_validate({**study.semantic_document(), "unexpected": True})
    with pytest.raises(ValidationError):
        study.title = "mutated"  # type: ignore[misc]


def test_all_core_contract_models_are_closed_and_frozen() -> None:
    pending = list(ContractModel.__subclasses__())
    models: set[type[ContractModel]] = set()
    while pending:
        model = pending.pop()
        if model in models:
            continue
        models.add(model)
        pending.extend(model.__subclasses__())
    assert models
    for model in models:
        assert model.model_config.get("extra") == "forbid"
        assert model.model_config.get("frozen") is True


def test_semantic_serialization_omits_absent_modules_and_digest_excludes_metadata() -> None:
    _, package = legacy_package()
    original = package.study
    document = original.semantic_document()
    assert "decision_to_inform" not in document["payload"]["intent"]
    assert "assumptions" not in document["payload"]["intent"]
    assert "checkpoint_policy_ref" not in document["payload"]["run_blueprint"]
    assert "digest" not in document

    renamed = original.model_copy(update={"title": "A storage-only title change"})
    assert renamed.digest == original.digest
    registry = InMemoryContractRegistry()
    registry.add(original)
    with pytest.raises(ValueError, match="immutable"):
        registry.add(renamed)


def test_revision_decisions_reject_unverified_human_claim_and_require_monotonic_revision() -> None:
    _, package = legacy_package()
    with pytest.raises(ValidationError):
        RevisionDecisionRecord.model_validate(
            {
                "revision_ref": package.study.ref.model_dump(mode="json"),
                "decision": "accepted",
                "authority": {"kind": "verified_human", "principal_id": "lab"},
                "rationale": "A Lab Agent cannot accept its own draft.",
                "decided_at_utc": utc_now().isoformat(),
            }
        )

    skipped = package.study.model_copy(update={"revision": 3})
    registry = InMemoryContractRegistry()
    registry.add(package.study)
    with pytest.raises(ValueError, match="monotonic"):
        registry.add(skipped)


def test_structurally_valid_human_decision_fails_closed_without_verifier() -> None:
    _, package = legacy_package()
    revision = package.study
    rationale = "I reviewed the exact revision content."
    decided_at = utc_now()
    subject_digest = sha256_json(
        {
            "revision_ref": revision.ref.model_dump(mode="json"),
            "decision": "accepted",
            "rationale": rationale,
        }
    )
    attestation = HumanAttestationRecord(
        attestation_id="human-attestation-test",
        principal_id="test-principal",
        credential_id="credential-test",
        action="revision.accepted",
        target_digest=revision.digest,
        subject_digest=subject_digest,
        challenge_digest="a" * 64,
        assertion_ref=ArtifactRef(
            artifact_id="webauthn-assertion-test",
            digest="b" * 64,
            media_type="application/webauthn+json",
        ),
        relying_party_id="evidrun.local",
        origin="https://evidrun.local",
        verifier_ref=capability_ref("evidrun.authority", "webauthn"),
        verified_at_utc=decided_at,
    )
    decision = RevisionDecisionRecord(
        revision_ref=revision.ref,
        decision="accepted",
        authority=VerifiedHumanDecisionAuthority(
            principal_id="test-principal", attestation=attestation
        ),
        rationale=rationale,
        decided_at_utc=decided_at,
    )
    registry = InMemoryContractRegistry()
    registry.add(revision)
    with pytest.raises(HumanAttestationUnavailable, match="no trusted verifier"):
        registry.decide(decision)

    fixture_registry = InMemoryContractRegistry()
    fixture_registry.add(revision)
    fixture_decision = next(
        item
        for item in package.acceptance_decisions()
        if item.revision_ref == revision.ref
    )
    with pytest.raises(PermissionError, match="legacy import path"):
        fixture_registry.decide(fixture_decision)


def test_reference_slots_and_extension_identity_are_validated() -> None:
    _, package = legacy_package()
    wrong_goal_ref = package.study.payload.scenario_refs[0]
    with pytest.raises(ValidationError, match="wrong contract type"):
        type(package.study.payload).model_validate(
            {
                **semantic_model_dump(package.study.payload),
                "goal_ref": wrong_goal_ref.model_dump(mode="json"),
            }
        )

    schema = ArtifactRef(
        artifact_id="extension-schema",
        digest="a" * 64,
        media_type="application/schema+json",
    )
    payload = ArtifactRef(
        artifact_id="extension-payload",
        digest="b" * 64,
        media_type="application/json",
    )
    with pytest.raises(ValidationError, match="digest must match"):
        ExtensionRef(
            namespace="example.extension",
            slot="analysis",
            schema_ref=schema,
            schema_version="1",
            payload_ref=payload,
            digest="c" * 64,
            classification=payload.classification,
        )
    with pytest.raises(ValidationError, match="Extra inputs"):
        ArtifactRef.model_validate(
            {
                "artifact_id": "storage-coupled-ref",
                "digest": "d" * 64,
                "media_type": "text/plain",
                "locator": "/private/laboratory/hidden.txt",
            }
        )

