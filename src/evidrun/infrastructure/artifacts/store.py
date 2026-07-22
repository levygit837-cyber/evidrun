from __future__ import annotations

import base64
import json
import os
import secrets
from collections.abc import Mapping
from pathlib import Path
from typing import Protocol

import keyring
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

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
            artifact_id = f"art_{digest}"
            target = self.cas / digest[:2] / digest[2:]
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            if not target.exists():
                target.write_bytes(content)
                os.chmod(target, 0o600)
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
        meta_path.write_text(canonical_json(record), encoding="utf-8")
        os.chmod(meta_path, 0o600)
        return record

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

    def purge(self, artifact_id: str) -> Mapping[str, object]:
        record = self._metadata(artifact_id)
        if record["storage"] == "cas":
            digest = str(record["digest"])
            target = self.cas / digest[:2] / digest[2:]
        else:
            target = self.vault / f"{artifact_id}.bin"
        target.unlink(missing_ok=True)
        tombstone = {
            "artifact_id": artifact_id,
            "classification": record["classification"],
            "digest": record["digest"],
            "purged_at": utc_now().isoformat(),
            "reason": "retention_expired_or_user_requested",
        }
        meta_path = self.metadata / f"{artifact_id}.json"
        meta_path.write_text(canonical_json(tombstone), encoding="utf-8")
        return tombstone

    def _metadata(self, artifact_id: str) -> dict[str, object]:
        if "/" in artifact_id or "\\" in artifact_id or artifact_id.startswith("."):
            raise ValueError("invalid artifact id")
        path = self.metadata / f"{artifact_id}.json"
        return json.loads(path.read_text(encoding="utf-8"))
