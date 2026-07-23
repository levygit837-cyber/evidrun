from __future__ import annotations

import pytest

from evidrun.authority import crypto


def _signed(challenge_digest: str = "a" * 64) -> tuple[str, dict[str, str]]:
    private_key = crypto.generate_private_key()
    public_key_pem = crypto.public_key_to_pem(private_key.public_key())
    assertion = crypto.sign_assertion(
        private_key,
        relying_party_id="evidrun.local",
        origin="https://evidrun.local",
        challenge_digest=challenge_digest,
        sign_count=0,
    )
    return public_key_pem, assertion


def test_valid_assertion_verifies() -> None:
    public_key_pem, assertion = _signed()
    crypto.verify_assertion(
        public_key_pem,
        assertion,
        relying_party_id="evidrun.local",
        origin="https://evidrun.local",
        challenge_digest="a" * 64,
    )


def test_wrong_relying_party_is_rejected() -> None:
    public_key_pem, assertion = _signed()
    with pytest.raises(crypto.AssertionVerificationError, match="relying party"):
        crypto.verify_assertion(
            public_key_pem,
            assertion,
            relying_party_id="attacker.local",
            origin="https://evidrun.local",
            challenge_digest="a" * 64,
        )


def test_wrong_origin_is_rejected() -> None:
    public_key_pem, assertion = _signed()
    with pytest.raises(crypto.AssertionVerificationError, match="origin"):
        crypto.verify_assertion(
            public_key_pem,
            assertion,
            relying_party_id="evidrun.local",
            origin="https://evil.local",
            challenge_digest="a" * 64,
        )


def test_wrong_challenge_is_rejected() -> None:
    public_key_pem, assertion = _signed()
    with pytest.raises(crypto.AssertionVerificationError, match="challenge"):
        crypto.verify_assertion(
            public_key_pem,
            assertion,
            relying_party_id="evidrun.local",
            origin="https://evidrun.local",
            challenge_digest="b" * 64,
        )


def test_tampered_signature_is_rejected() -> None:
    public_key_pem, assertion = _signed()
    assertion["signature"] = crypto.b64url_encode(b"\x00" * 70)
    with pytest.raises(crypto.AssertionVerificationError):
        crypto.verify_assertion(
            public_key_pem,
            assertion,
            relying_party_id="evidrun.local",
            origin="https://evidrun.local",
            challenge_digest="a" * 64,
        )


def test_signature_from_a_different_key_is_rejected() -> None:
    _, assertion = _signed()
    other_public = crypto.public_key_to_pem(crypto.generate_private_key().public_key())
    with pytest.raises(crypto.AssertionVerificationError, match="signature is invalid"):
        crypto.verify_assertion(
            other_public,
            assertion,
            relying_party_id="evidrun.local",
            origin="https://evidrun.local",
            challenge_digest="a" * 64,
        )


def test_missing_field_is_rejected() -> None:
    public_key_pem, assertion = _signed()
    del assertion["authenticator_data"]
    with pytest.raises(crypto.AssertionVerificationError, match="missing field"):
        crypto.verify_assertion(
            public_key_pem,
            assertion,
            relying_party_id="evidrun.local",
            origin="https://evidrun.local",
            challenge_digest="a" * 64,
        )
