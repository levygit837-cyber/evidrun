from __future__ import annotations

from typing import Protocol

from evidrun.contracts.base import Digest, HumanAttestationRecord


class HumanAttestationError(ValueError):
    """Base error for human authority that could not be established."""


class HumanAttestationUnavailable(HumanAttestationError):
    """No trusted user-verification adapter is installed."""


class HumanAttestationInvalid(HumanAttestationError):
    """A verifier rejected the ceremony evidence."""


class HumanAttestationVerifier(Protocol):
    def verify(
        self,
        attestation: HumanAttestationRecord,
        *,
        expected_subject_digest: Digest,
    ) -> None: ...


class UnavailableHumanAttestationVerifier:
    """Safe production default until WebAuthn or an equivalent adapter exists."""

    def verify(
        self,
        attestation: HumanAttestationRecord,
        *,
        expected_subject_digest: Digest,
    ) -> None:
        del attestation, expected_subject_digest
        raise HumanAttestationUnavailable(
            "verified human authority is unavailable; no trusted verifier is installed"
        )
