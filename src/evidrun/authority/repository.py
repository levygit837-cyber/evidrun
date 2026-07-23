from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, timedelta

from sqlalchemy import select

from evidrun.authority.challenge import ConfirmationIntent, challenge_digest, new_nonce
from evidrun.authority.models import HumanChallengeRow, HumanCredentialRow
from evidrun.infrastructure.database.engine import Database
from evidrun.shared.types import new_id, utc_now

CHALLENGE_TTL = timedelta(minutes=5)


class CredentialUnavailable(ValueError):
    """The referenced credential is unknown or revoked."""


class ChallengeUnavailable(ValueError):
    """The challenge is unknown, expired, or already consumed."""


@dataclass(frozen=True)
class EnrolledCredential:
    credential_id: str
    principal_id: str
    display_name: str
    public_key_pem: str
    relying_party_id: str
    origin: str
    status: str


@dataclass(frozen=True)
class IssuedChallenge:
    challenge_id: str
    challenge_digest: str
    nonce: str
    expires_at_iso: str


class AuthorityRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def enroll_credential(
        self,
        *,
        credential_id: str,
        principal_id: str,
        display_name: str,
        public_key_pem: str,
        relying_party_id: str,
        origin: str,
    ) -> EnrolledCredential:
        row = HumanCredentialRow(
            credential_id=credential_id,
            principal_id=principal_id,
            display_name=display_name,
            public_key_pem=public_key_pem,
            relying_party_id=relying_party_id,
            origin=origin,
            sign_count=0,
            status="active",
            created_at=utc_now(),
        )
        with self.database.session() as session:
            session.add(row)
            session.commit()
        return self._to_credential(row)

    def get_credential(self, credential_id: str) -> EnrolledCredential:
        with self.database.session() as session:
            row = session.get(HumanCredentialRow, credential_id)
            if row is None:
                raise CredentialUnavailable(f"unknown credential: {credential_id}")
            return self._to_credential(row)

    def list_credentials(self) -> list[EnrolledCredential]:
        with self.database.session() as session:
            rows = list(session.scalars(select(HumanCredentialRow)))
            return [self._to_credential(row) for row in rows]

    def require_active_credential(self, credential_id: str) -> EnrolledCredential:
        credential = self.get_credential(credential_id)
        if credential.status != "active":
            raise CredentialUnavailable(f"credential is not active: {credential_id}")
        return credential

    def revoke_credential(self, credential_id: str) -> EnrolledCredential:
        with self.database.session() as session:
            row = session.get(HumanCredentialRow, credential_id)
            if row is None:
                raise CredentialUnavailable(f"unknown credential: {credential_id}")
            if row.status == "active":
                row.status = "revoked"
                row.revoked_at = utc_now()
                session.commit()
            return self._to_credential(row)

    def issue_challenge(self, intent: ConfirmationIntent) -> IssuedChallenge:
        self.require_active_credential(intent.credential_id)
        nonce = new_nonce()
        digest = challenge_digest(intent, nonce)
        issued_at = utc_now()
        expires_at = issued_at + CHALLENGE_TTL
        row = HumanChallengeRow(
            challenge_id=new_id("hchal"),
            challenge_digest=digest,
            principal_id=intent.principal_id,
            credential_id=intent.credential_id,
            action=intent.action,
            intent_json=json.dumps(intent.binding_document(), sort_keys=True),
            issued_at=issued_at,
            expires_at=expires_at,
        )
        with self.database.session() as session:
            session.add(row)
            session.commit()
        return IssuedChallenge(
            challenge_id=row.challenge_id,
            challenge_digest=digest,
            nonce=nonce,
            expires_at_iso=expires_at.isoformat(),
        )

    def consume_challenge(self, challenge_digest_value: str) -> None:
        """Single-use guard. Idempotency is intentionally not offered here."""
        with self.database.session() as session:
            row = session.scalar(
                select(HumanChallengeRow).where(
                    HumanChallengeRow.challenge_digest == challenge_digest_value
                )
            )
            if row is None:
                raise ChallengeUnavailable("challenge does not exist")
            if row.consumed_at is not None:
                raise ChallengeUnavailable("challenge was already consumed")
            expires_at = row.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
            if expires_at < utc_now():
                raise ChallengeUnavailable("challenge has expired")
            row.consumed_at = utc_now()
            session.commit()

    @staticmethod
    def _to_credential(row: HumanCredentialRow) -> EnrolledCredential:
        return EnrolledCredential(
            credential_id=row.credential_id,
            principal_id=row.principal_id,
            display_name=row.display_name,
            public_key_pem=row.public_key_pem,
            relying_party_id=row.relying_party_id,
            origin=row.origin,
            status=row.status,
        )
