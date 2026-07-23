from __future__ import annotations

import secrets
from dataclasses import dataclass

from evidrun.shared.types import sha256_json


@dataclass(frozen=True)
class ConfirmationIntent:
    """The exact human action a challenge is bound to.

    The challenge digest commits to every field so the signed assertion cannot be
    replayed for a different action, target, subject, principal, or origin.
    """

    action: str
    target_digest: str
    subject_digest: str
    principal_id: str
    credential_id: str
    relying_party_id: str
    origin: str

    def binding_document(self) -> dict[str, str]:
        return {
            "action": self.action,
            "target_digest": self.target_digest,
            "subject_digest": self.subject_digest,
            "principal_id": self.principal_id,
            "credential_id": self.credential_id,
            "relying_party_id": self.relying_party_id,
            "origin": self.origin,
        }


def challenge_digest(intent: ConfirmationIntent, nonce: str) -> str:
    """Deterministic 64-hex digest binding the intent to a single-use nonce."""
    return sha256_json({"intent": intent.binding_document(), "nonce": nonce})


def new_nonce() -> str:
    return secrets.token_hex(32)
