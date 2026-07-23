from __future__ import annotations

import json
from typing import Any, cast

from evidrun.authority import crypto
from evidrun.authority.repository import AuthorityRepository, CredentialUnavailable
from evidrun.contracts.authority import HumanAttestationInvalid
from evidrun.contracts.base import Digest, HumanAttestationRecord
from evidrun.infrastructure.artifacts.store import ArtifactStore


class LocalWebAuthnVerifier:
    """Verifies software-authenticator assertions against enrolled EC public keys.

    Pure and idempotent: it performs no writes and does not consume challenges, so
    it is safe to run both when persisting a decision and when replaying the ledger
    on load. Single-use enforcement lives in the confirmation service.
    """

    def __init__(self, repository: AuthorityRepository, artifacts: ArtifactStore) -> None:
        self._repository = repository
        self._artifacts = artifacts

    def verify(
        self,
        attestation: HumanAttestationRecord,
        *,
        expected_subject_digest: Digest,
    ) -> None:
        if attestation.subject_digest != expected_subject_digest:
            raise HumanAttestationInvalid(
                "attestation does not cover the expected decision content"
            )
        try:
            credential = self._repository.get_credential(attestation.credential_id)
        except CredentialUnavailable as exc:
            raise HumanAttestationInvalid(str(exc)) from exc
        if credential.principal_id != attestation.principal_id:
            raise HumanAttestationInvalid("attestation principal does not own the credential")
        if credential.relying_party_id != attestation.relying_party_id:
            raise HumanAttestationInvalid("attestation relying party does not match credential")
        if credential.origin != attestation.origin:
            raise HumanAttestationInvalid("attestation origin does not match credential")

        try:
            assertion_bytes = self._artifacts.get(attestation.assertion_ref.artifact_id)
        except (FileNotFoundError, KeyError) as exc:
            raise HumanAttestationInvalid("assertion artifact is unavailable") from exc
        try:
            parsed: object = json.loads(assertion_bytes)
        except json.JSONDecodeError as exc:
            raise HumanAttestationInvalid("assertion artifact is not valid JSON") from exc
        if not isinstance(parsed, dict):
            raise HumanAttestationInvalid("assertion artifact is malformed")
        assertion = cast("dict[str, Any]", parsed)

        try:
            crypto.verify_assertion(
                credential.public_key_pem,
                assertion,
                relying_party_id=attestation.relying_party_id,
                origin=attestation.origin,
                challenge_digest=attestation.challenge_digest,
            )
        except crypto.AssertionVerificationError as exc:
            raise HumanAttestationInvalid(str(exc)) from exc
