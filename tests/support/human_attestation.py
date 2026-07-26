from __future__ import annotations

from evidrun.contracts import (
    ArtifactRef,
    HumanAttestationRecord,
    RevisionDecisionRecord,
    RevisionEnvelope,
    VerifiedHumanDecisionAuthority,
    capability_ref,
)
from evidrun.contracts.authority import HumanAttestationInvalid
from evidrun.shared.types import sha256_json, utc_now


class TestHumanAttestationVerifier:
    """Narrow fake trusted adapter injected only by tests."""

    __test__ = False

    def verify(
        self,
        attestation: HumanAttestationRecord,
        *,
        expected_subject_digest: str,
    ) -> None:
        if (
            attestation.subject_digest != expected_subject_digest
            or attestation.principal_id != "runtime-kernel-test-human"
            or attestation.verifier_ref.namespace != "tests.authority"
        ):
            raise HumanAttestationInvalid("test attestation does not authorize this decision")


def accepted_decision(revision: RevisionEnvelope) -> RevisionDecisionRecord:
    rationale = "Revisao humana da fixture transversal exata."
    decided_at = utc_now()
    subject_digest = sha256_json(
        {
            "revision_ref": revision.ref.model_dump(mode="json"),
            "decision": "accepted",
            "rationale": rationale,
        }
    )
    attestation = HumanAttestationRecord(
        attestation_id=f"attestation-{revision.logical_id}",
        principal_id="runtime-kernel-test-human",
        credential_id="test-only-credential",
        action="revision.accepted",
        target_digest=revision.digest,
        subject_digest=subject_digest,
        challenge_digest="a" * 64,
        assertion_ref=ArtifactRef(
            artifact_id=f"assertion-{revision.logical_id}",
            digest="b" * 64,
            media_type="application/webauthn+json",
        ),
        relying_party_id="tests.evidrun.local",
        origin="https://tests.evidrun.local",
        verifier_ref=capability_ref("tests.authority", "human-attestation"),
        verified_at_utc=decided_at,
    )
    return RevisionDecisionRecord(
        revision_ref=revision.ref,
        decision="accepted",
        authority=VerifiedHumanDecisionAuthority(
            principal_id=attestation.principal_id,
            attestation=attestation,
        ),
        rationale=rationale,
        decided_at_utc=decided_at,
    )
