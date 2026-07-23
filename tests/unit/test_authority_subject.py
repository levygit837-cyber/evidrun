from __future__ import annotations

from evidrun.authority.subject import EvaluationDecisionSubject, RevisionDecisionSubject
from evidrun.contracts.base import (
    ArtifactRef,
    CapabilityDescriptorRef,
    ContractRef,
    ContractType,
    EvidenceRef,
    HumanAttestationRecord,
)
from evidrun.contracts.runtime import (
    DimensionValue,
    EvaluationBoundary,
    IndependentHumanReviewRelation,
)
from evidrun.shared.types import utc_now


def _attestation(action: str, target_digest: str, subject_digest: str) -> HumanAttestationRecord:
    return HumanAttestationRecord(
        attestation_id="hatt_test",
        principal_id="alice",
        credential_id="hcred_test",
        action=action,  # type: ignore[arg-type]
        target_digest=target_digest,
        subject_digest=subject_digest,
        challenge_digest="c" * 64,
        assertion_ref=ArtifactRef(
            artifact_id="art_test",
            digest="d" * 64,
            media_type="application/webauthn+json",
        ),
        relying_party_id="evidrun.local",
        origin="https://evidrun.local",
        verifier_ref=CapabilityDescriptorRef(
            namespace="evidrun.authority", name="local-webauthn-verifier", version="1",
            digest="0" * 63 + "1",
        ),
        verified_at_utc=utc_now(),
    )


def test_revision_subject_digest_matches_kernel_record() -> None:
    subject = RevisionDecisionSubject(
        revision_ref=ContractRef(
            contract_type=ContractType.STUDY, logical_id="study-x", revision=1, digest="a" * 64
        ),
        decision="accepted",
        rationale="Reviewed the exact revision content.",
    )
    attestation = _attestation("revision.accepted", subject.target_digest, subject.subject_digest())
    decision = subject.build_decision(attestation)
    # The kernel record recomputes the digest and validates the attestation.
    assert decision.human_subject_digest() == subject.subject_digest()
    assert decision.decision == "accepted"


def test_evaluation_subject_digest_matches_kernel_record() -> None:
    subject = EvaluationDecisionSubject(
        source_type="human_reviewer",
        record_id="eval_1",
        run_id="run_1",
        plan_ref=ContractRef(
            contract_type=ContractType.EVALUATION_PLAN,
            logical_id="plan-x",
            revision=1,
            digest="b" * 64,
        ),
        stage_id="stage-1",
        evaluator_ref=CapabilityDescriptorRef(
            namespace="evidrun.human", name="reviewer", version="1", digest="e" * 64
        ),
        boundary=EvaluationBoundary(up_to_event_sequence=3, event_hash="f" * 64),
        dimension_values=(
            DimensionValue(
                dimension_id="quality",
                value=True,
                rationale="Meets the bar.",
                evidence_refs=(EvidenceRef(ref="event:run_1:3"),),
            ),
        ),
        gate_status="passed",
        relation=IndependentHumanReviewRelation(),
    )
    attestation = _attestation(
        "evaluation.reviewed", subject.target_digest, subject.subject_digest()
    )
    record = subject.build_evaluation(attestation)
    assert record.human_subject_digest() == subject.subject_digest()
    assert record.status == "final"
