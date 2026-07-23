from __future__ import annotations

import contextlib
from typing import Any, Protocol

import keyring
from keyring.errors import PasswordDeleteError

from evidrun.authority import crypto


class AuthenticatorKeyStore(Protocol):
    def create(self, credential_id: str) -> str: ...
    def sign(
        self,
        credential_id: str,
        *,
        relying_party_id: str,
        origin: str,
        challenge_digest: str,
        sign_count: int,
    ) -> dict[str, Any]: ...
    def delete(self, credential_id: str) -> None: ...


class KeyringAuthenticator:
    """Local software authenticator holding EC private keys in the OS keystore.

    Signing is only reachable through an explicit confirmation ceremony; no agent
    or automation code path invokes this implicitly.
    """

    service = "evidrun-human-authenticator"

    def create(self, credential_id: str) -> str:
        private_key = crypto.generate_private_key()
        keyring.set_password(
            self.service, credential_id, crypto.private_key_to_pem(private_key)
        )
        return crypto.public_key_to_pem(private_key.public_key())

    def sign(
        self,
        credential_id: str,
        *,
        relying_party_id: str,
        origin: str,
        challenge_digest: str,
        sign_count: int,
    ) -> dict[str, Any]:
        pem = keyring.get_password(self.service, credential_id)
        if pem is None:
            raise KeyError(f"no authenticator key for credential {credential_id}")
        private_key = crypto.load_private_key(pem)
        return crypto.sign_assertion(
            private_key,
            relying_party_id=relying_party_id,
            origin=origin,
            challenge_digest=challenge_digest,
            sign_count=sign_count,
        )

    def delete(self, credential_id: str) -> None:
        with contextlib.suppress(PasswordDeleteError):
            keyring.delete_password(self.service, credential_id)


class MemoryAuthenticator:
    """In-memory authenticator for tests and headless offline flows."""

    def __init__(self) -> None:
        self._keys: dict[str, str] = {}

    def create(self, credential_id: str) -> str:
        private_key = crypto.generate_private_key()
        self._keys[credential_id] = crypto.private_key_to_pem(private_key)
        return crypto.public_key_to_pem(private_key.public_key())

    def sign(
        self,
        credential_id: str,
        *,
        relying_party_id: str,
        origin: str,
        challenge_digest: str,
        sign_count: int,
    ) -> dict[str, Any]:
        pem = self._keys.get(credential_id)
        if pem is None:
            raise KeyError(f"no authenticator key for credential {credential_id}")
        private_key = crypto.load_private_key(pem)
        return crypto.sign_assertion(
            private_key,
            relying_party_id=relying_party_id,
            origin=origin,
            challenge_digest=challenge_digest,
            sign_count=sign_count,
        )

    def delete(self, credential_id: str) -> None:
        self._keys.pop(credential_id, None)
