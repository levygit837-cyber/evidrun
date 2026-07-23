from __future__ import annotations

import base64
import json
import os
import secrets
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Protocol

import keyring
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from evidrun.contracts import ArtifactRef
from evidrun.shared.types import Classification, canonical_json, new_id, sha256_bytes, utc_now


class KeyProvider(Protocol):
    def get_or_create(self, project_id: str) -> bytes: ...


class KeyringKeyProvider:
    service = "evidrun-project-keys"

    def get_or_create(self, project_id: str) -> bytes:
        encoded = keyring.get_password(self.service, project_id)
        if encoded:
            return base64.urlsafe_b64decode(encoded.encode("ascii"))
        key = AESGCM.generate_key(bit_length=256)
        encoded_key = base64.urlsafe_b64encode(key).decode("ascii")
        keyring.set_password(self.service, project_id, encoded_key)
        return key


class MemoryKeyProvider:
    def __init__(self) -> None:
        self._keys: dict[str, bytes] = {}

    def get_or_create(self, project_id: str) -> bytes:
        return self._keys.setdefault(project_id, AESGCM.generate_key(bit_length=256))


class ArtifactStore:
    def __init__(self, root: Path, key_provider: KeyProvider | None = None):
        self.root = root
        self.cas = root / "cas"
        self.vault = root / "vault"
        self.metadata = root / "metadata"
        for path in (self.cas, self.vault, self.metadata):
            path.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.key_provider = key_provider or KeyringKeyProvider()

    def put(
        self,
        content: bytes,
        *,
        project_id: str,
        media_type: str,
        classification: Classification,
        raw_authorized: bool = False,
        ttl_days: int = 30,
    ) -> Mapping[str, object]:
        if classification is Classification.RESTRICTED:
            raise ValueError("restricted content cannot be persisted")
        if classification is Classification.SENSITIVE and ttl_days < 1:
            raise ValueError("sensitive artifact ttl_days must be positive")
        created_at = utc_now()
        if classification is Classification.SENSITIVE:
            if not raw_authorized:
                raise PermissionError("sensitive raw capture requires explicit authorization")
            artifact_id = new_id("art")
            key = self.key_provider.get_or_create(project_id)
            nonce = secrets.token_bytes(12)
            encrypted = AESGCM(key).encrypt(nonce, content, artifact_id.encode("utf-8"))
            target = self.vault / f"{artifact_id}.bin"
            target.write_bytes(nonce + encrypted)
            os.chmod(target, 0o600)
            digest = sha256_bytes(encrypted)
            storage = "encrypted_vault"
        else:
            digest = sha256_bytes(content)
            authority_digest = sha256_bytes(
                canonical_json(
                    {
                        "project_id": project_id,
                        "media_type": media_type,
                        "classification": classification.value,
                    }
                ).encode("utf-8")
            )
            artifact_id = f"art_{digest}_{authority_digest[:16]}"
            target = self.cas / digest[:2] / digest[2:]
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            if not target.exists():
                with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as temporary:
                    temporary.write(content)
                    temporary.flush()
                    os.fsync(temporary.fileno())
                    temporary_path = Path(temporary.name)
                os.chmod(temporary_path, 0o600)
                os.replace(temporary_path, target)
            storage = "cas"

        record = {
            "artifact_id": artifact_id,
            "project_id": project_id,
            "media_type": media_type,
            "classification": classification.value,
            "storage": storage,
            "digest": digest,
            "created_at": created_at.isoformat(),
            "ttl_days": ttl_days if classification is Classification.SENSITIVE else None,
            "pinned": False,
        }
        meta_path = self.metadata / f"{artifact_id}.json"
        if meta_path.exists():
            existing = json.loads(meta_path.read_text(encoding="utf-8"))
            immutable_fields = {
                "artifact_id",
                "project_id",
                "media_type",
                "classification",
                "storage",
                "digest",
            }
            if any(existing.get(field) != record.get(field) for field in immutable_fields):
                raise ValueError("artifact identity collides with different immutable metadata")
            record = existing
        else:
            self._write_metadata(meta_path, record)
        return record

    def put_ref(
        self,
        content: bytes,
        *,
        project_id: str,
        media_type: str,
        classification: Classification,
        raw_authorized: bool = False,
        ttl_days: int = 30,
    ) -> ArtifactRef:
        record = self.put(
            content,
            project_id=project_id,
            media_type=media_type,
            classification=classification,
            raw_authorized=raw_authorized,
            ttl_days=ttl_days,
        )
        return ArtifactRef(
            artifact_id=str(record["artifact_id"]),
            digest=str(record["digest"]),
            media_type=str(record["media_type"]),
            classification=classification,
        )

    def get(self, artifact_id: str) -> bytes:
        record = self._metadata(artifact_id)
        if record["storage"] == "cas":
            digest = str(record["digest"])
            return (self.cas / digest[:2] / digest[2:]).read_bytes()
        project_id = str(record["project_id"])
        payload = (self.vault / f"{artifact_id}.bin").read_bytes()
        nonce, encrypted = payload[:12], payload[12:]
        key = self.key_provider.get_or_create(project_id)
        return AESGCM(key).decrypt(nonce, encrypted, artifact_id.encode("utf-8"))

    def get_verified(self, reference: ArtifactRef, *, project_id: str | None = None) -> bytes:
        record = self._metadata(reference.artifact_id)
        if (
            record.get("media_type") != reference.media_type
            or record.get("classification") != reference.classification.value
            or record.get("digest") != reference.digest
            or (project_id is not None and record.get("project_id") != project_id)
        ):
            raise ValueError("artifact metadata does not match its canonical reference")
        storage = record.get("storage")
        if storage == "cas":
            content = self.get(reference.artifact_id)
            if sha256_bytes(content) != reference.digest:
                raise ValueError("artifact content digest does not match its canonical reference")
            return content
        if storage == "encrypted_vault":
            payload = (self.vault / f"{reference.artifact_id}.bin").read_bytes()
            if len(payload) < 13 or sha256_bytes(payload[12:]) != reference.digest:
                raise ValueError("encrypted artifact digest does not match its canonical reference")
            return self.get(reference.artifact_id)
        raise ValueError("artifact storage kind is not supported")

    def purge(self, artifact_id: str) -> Mapping[str, object]:
        record = self._metadata(artifact_id)
        if record["storage"] == "cas":
            digest = str(record["digest"])
            target = self.cas / digest[:2] / digest[2:]
            has_live_reference = any(
                candidate.name != f"{artifact_id}.json"
                and self._is_live_cas_reference(candidate, digest)
                for candidate in self.metadata.glob("*.json")
            )
        else:
            target = self.vault / f"{artifact_id}.bin"
            has_live_reference = False
        if not has_live_reference:
            target.unlink(missing_ok=True)
        tombstone = {
            "artifact_id": artifact_id,
            "classification": record["classification"],
            "digest": record["digest"],
            "purged_at": utc_now().isoformat(),
            "reason": "retention_expired_or_user_requested",
        }
        meta_path = self.metadata / f"{artifact_id}.json"
        self._write_metadata(meta_path, tombstone)
        return tombstone

    @staticmethod
    def _is_live_cas_reference(path: Path, digest: str) -> bool:
        try:
            candidate = json.loads(path.read_text(encoding="utf-8"))
        except OSError, json.JSONDecodeError:
            return False
        return candidate.get("storage") == "cas" and candidate.get("digest") == digest

    def _write_metadata(self, target: Path, document: Mapping[str, object]) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=self.metadata,
            delete=False,
        ) as temporary:
            temporary.write(canonical_json(document))
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        os.chmod(temporary_path, 0o600)
        os.replace(temporary_path, target)

    def _metadata(self, artifact_id: str) -> dict[str, object]:
        if "/" in artifact_id or "\\" in artifact_id or artifact_id.startswith("."):
            raise ValueError("invalid artifact id")
        path = self.metadata / f"{artifact_id}.json"
        return json.loads(path.read_text(encoding="utf-8"))
