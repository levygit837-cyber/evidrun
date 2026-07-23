from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

UP_FLAG = 0b0000_0001
UV_FLAG = 0b0000_0100


class AssertionVerificationError(ValueError):
    """The assertion could not be cryptographically validated."""


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def generate_private_key() -> ec.EllipticCurvePrivateKey:
    return ec.generate_private_key(ec.SECP256R1())


def private_key_to_pem(private_key: ec.EllipticCurvePrivateKey) -> str:
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")


def load_private_key(pem: str) -> ec.EllipticCurvePrivateKey:
    key = serialization.load_pem_private_key(pem.encode("ascii"), password=None)
    if not isinstance(key, ec.EllipticCurvePrivateKey):
        raise AssertionVerificationError("stored authenticator key is not an EC private key")
    return key


def public_key_to_pem(public_key: ec.EllipticCurvePublicKey) -> str:
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")


def load_public_key(pem: str) -> ec.EllipticCurvePublicKey:
    key = serialization.load_pem_public_key(pem.encode("ascii"))
    if not isinstance(key, ec.EllipticCurvePublicKey):
        raise AssertionVerificationError("enrolled credential key is not an EC public key")
    return key


def rp_id_hash(relying_party_id: str) -> bytes:
    return hashlib.sha256(relying_party_id.encode("utf-8")).digest()


def build_authenticator_data(relying_party_id: str, sign_count: int) -> bytes:
    """Minimal WebAuthn authenticatorData: rpIdHash(32) + flags(1) + signCount(4)."""
    flags = (UP_FLAG | UV_FLAG).to_bytes(1, "big")
    counter = sign_count.to_bytes(4, "big")
    return rp_id_hash(relying_party_id) + flags + counter


def build_client_data(challenge_digest: str, origin: str) -> bytes:
    """Canonical clientDataJSON for a WebAuthn 'get' assertion.

    The challenge carries the intent digest bytes so the signature commits to the
    full action/target/subject/principal/rp/origin binding.
    """
    document = {
        "type": "webauthn.get",
        "challenge": b64url_encode(bytes.fromhex(challenge_digest)),
        "origin": origin,
    }
    return json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def sign_assertion(
    private_key: ec.EllipticCurvePrivateKey,
    *,
    relying_party_id: str,
    origin: str,
    challenge_digest: str,
    sign_count: int,
) -> dict[str, Any]:
    authenticator_data = build_authenticator_data(relying_party_id, sign_count)
    client_data = build_client_data(challenge_digest, origin)
    client_data_hash = hashlib.sha256(client_data).digest()
    signature = private_key.sign(authenticator_data + client_data_hash, ec.ECDSA(hashes.SHA256()))
    return {
        "authenticator_data": b64url_encode(authenticator_data),
        "client_data_json": b64url_encode(client_data),
        "signature": b64url_encode(signature),
    }


def verify_assertion(
    public_key_pem: str,
    assertion: dict[str, Any],
    *,
    relying_party_id: str,
    origin: str,
    challenge_digest: str,
) -> None:
    """Validate a software-authenticator assertion. Pure and idempotent."""
    for field in ("authenticator_data", "client_data_json", "signature"):
        if field not in assertion or not isinstance(assertion[field], str):
            raise AssertionVerificationError(f"assertion is missing field: {field}")

    authenticator_data = b64url_decode(assertion["authenticator_data"])
    client_data = b64url_decode(assertion["client_data_json"])
    signature = b64url_decode(assertion["signature"])

    if len(authenticator_data) < 37:
        raise AssertionVerificationError("authenticator data is malformed")
    if authenticator_data[:32] != rp_id_hash(relying_party_id):
        raise AssertionVerificationError("authenticator data does not match the relying party")
    flags = authenticator_data[32]
    if not flags & UP_FLAG:
        raise AssertionVerificationError("assertion lacks user presence")
    if not flags & UV_FLAG:
        raise AssertionVerificationError("assertion lacks verified user presence")

    try:
        client = json.loads(client_data)
    except json.JSONDecodeError as exc:
        raise AssertionVerificationError("client data is not valid JSON") from exc
    if client.get("type") != "webauthn.get":
        raise AssertionVerificationError("client data is not a webauthn.get assertion")
    if client.get("origin") != origin:
        raise AssertionVerificationError("client data origin does not match the credential")
    expected_challenge = b64url_encode(bytes.fromhex(challenge_digest))
    if client.get("challenge") != expected_challenge:
        raise AssertionVerificationError("client data challenge does not match the intent")

    client_data_hash = hashlib.sha256(client_data).digest()
    public_key = load_public_key(public_key_pem)
    signed_bytes = authenticator_data + client_data_hash
    try:
        public_key.verify(signature, signed_bytes, ec.ECDSA(hashes.SHA256()))
    except InvalidSignature as exc:
        raise AssertionVerificationError("assertion signature is invalid") from exc
