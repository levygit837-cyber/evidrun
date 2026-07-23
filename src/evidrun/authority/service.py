from __future__ import annotations

import json
from typing import Any

from evidrun.authority.authenticator import AuthenticatorKeyStore
from evidrun.authority.challenge import ConfirmationIntent, challenge_digest
from evidrun.authority.policy import AuthorityMode, AuthorityPolicy
from evidrun.authority.repository import (
    AuthorityRepository,
    ChallengeUnavailable,
    EnrolledCredential,
    IssuedChallenge,
)
from evidrun.authority.subject import (
    EvaluationDecisionSubject,
    RevisionDecisionSubject,
)
from evidrun.contracts.base import (
    ArtifactRef,
    CapabilityDescriptorRef,
    HumanAttestationRecord,
)
from evidrun.infrastructure.artifacts.store import ArtifactStore
from evidrun.shared.types import Classification, new_id, utc_now

VERIFIER_REF = CapabilityDescriptorRef(
    namespace="evidrun.authority",
    name="local-webauthn-verifier",
    version="1",
    digest="0" * 63 + "1",
)

HumanSubject = RevisionDecisionSubject | EvaluationDecisionSubject


class HumanAuthorityService:
    """Orchestrates enrollment, confirmation, and verified-human attestation.

    No method here executes a Run or mutates a RunSpec/Admission. It only produces
    attestation evidence and builds the kernel record that downstream repositories
    verify before persisting a human decision or evaluation.
    """

    def __init__(
        self,
        *,
        repository: AuthorityRepository,
        authenticator: AuthenticatorKeyStore,
        artifacts: ArtifactStore,
        policy: AuthorityPolicy | None = None,
    ) -> None:
        self._repository = repository
        self._authenticator = authenticator
        self._artifacts = artifacts
        self._policy = policy or AuthorityPolicy()

    def enroll(
        self,
        *,
        principal_id: str,
        display_name: str,
        relying_party_id: str,
        origin: str,
    ) -> EnrolledCredential:
        credential_id = new_id("hcred")
        public_key_pem = self._authenticator.create(credential_id)
        return self._repository.enroll_credential(
            credential_id=credential_id,
            principal_id=principal_id,
            display_name=display_name,
            public_key_pem=public_key_pem,
            relying_party_id=relying_party_id,
            origin=origin,
        )

    def list_credentials(self) -> list[EnrolledCredential]:
        return self._repository.list_credentials()

    def revoke(self, credential_id: str) -> EnrolledCredential:
        return self._repository.revoke_credential(credential_id)

    # --- Two-step confirmation ------------------------------------------------

    @staticmethod
    def _intent_for(subject: HumanSubject, credential: EnrolledCredential) -> ConfirmationIntent:
        return ConfirmationIntent(
            action=subject.action,
            target_digest=subject.target_digest,
            subject_digest=subject.subject_digest(),
            principal_id=credential.principal_id,
            credential_id=credential.credential_id,
            relying_party_id=credential.relying_party_id,
            origin=credential.origin,
        )

    def begin_confirmation(
        self,
        *,
        mode: AuthorityMode,
        subject: HumanSubject,
        credential_id: str,
    ) -> IssuedChallenge:
        if isinstance(subject, EvaluationDecisionSubject):
            subject.validate_role()
        self._policy.enforce(mode=mode, action=subject.action, verified_human=True)
        credential = self._repository.require_active_credential(credential_id)
        return self._repository.issue_challenge(self._intent_for(subject, credential))

    def complete_confirmation(
        self,
        *,
        subject: HumanSubject,
        credential_id: str,
        challenge: IssuedChallenge,
        assertion: dict[str, Any],
        project_id: str,
    ) -> HumanAttestationRecord:
        credential = self._repository.require_active_credential(credential_id)
        # Bind the issued challenge to the exact subject being completed: the signed
        # challenge must re-derive from this subject's intent, or the confirmation
        # for one action cannot be redirected to authorize a different one.
        expected_digest = challenge_digest(
            self._intent_for(subject, credential), challenge.nonce
        )
        if expected_digest != challenge.challenge_digest:
            raise ChallengeUnavailable("challenge does not match the confirmed intent")
        # Single-use enforcement: fails closed on replay or expiry.
        self._repository.consume_challenge(challenge.challenge_digest)
        stored = self._artifacts.put(
            json.dumps(assertion, sort_keys=True).encode("utf-8"),
            project_id=project_id,
            media_type="application/webauthn+json",
            classification=Classification.INTERNAL,
        )
        assertion_ref = ArtifactRef(
            artifact_id=str(stored["artifact_id"]),
            digest=str(stored["digest"]),
            media_type="application/webauthn+json",
            classification=Classification.INTERNAL,
        )
        return HumanAttestationRecord(
            attestation_id=new_id("hatt"),
            principal_id=credential.principal_id,
            credential_id=credential.credential_id,
            action=subject.action,
            target_digest=subject.target_digest,
            subject_digest=subject.subject_digest(),
            challenge_digest=challenge.challenge_digest,
            assertion_ref=assertion_ref,
            relying_party_id=credential.relying_party_id,
            origin=credential.origin,
            verifier_ref=VERIFIER_REF,
            verified_at_utc=utc_now(),
        )

    # --- Local software-authenticator shortcut (offline dev/desktop) ----------

    def sign_locally(
        self,
        *,
        credential_id: str,
        challenge: IssuedChallenge,
    ) -> dict[str, Any]:
        credential = self._repository.require_active_credential(credential_id)
        return self._authenticator.sign(
            credential.credential_id,
            relying_party_id=credential.relying_party_id,
            origin=credential.origin,
            challenge_digest=challenge.challenge_digest,
            sign_count=0,
        )

    def confirm_with_local_authenticator(
        self,
        *,
        mode: AuthorityMode,
        subject: HumanSubject,
        credential_id: str,
        project_id: str,
    ) -> HumanAttestationRecord:
        challenge = self.begin_confirmation(
            mode=mode, subject=subject, credential_id=credential_id
        )
        assertion = self.sign_locally(credential_id=credential_id, challenge=challenge)
        return self.complete_confirmation(
            subject=subject,
            credential_id=credential_id,
            challenge=challenge,
            assertion=assertion,
            project_id=project_id,
        )
