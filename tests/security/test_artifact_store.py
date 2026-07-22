from __future__ import annotations

from pathlib import Path

import pytest

from evidrun.infrastructure.artifacts.store import ArtifactStore, MemoryKeyProvider
from evidrun.shared.types import Classification


def test_sensitive_artifact_requires_opt_in_and_is_encrypted(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path, MemoryKeyProvider())
    with pytest.raises(PermissionError):
        store.put(
            b"private prompt",
            project_id="project-1",
            media_type="text/plain",
            classification=Classification.SENSITIVE,
        )

    record = store.put(
        b"private prompt",
        project_id="project-1",
        media_type="text/plain",
        classification=Classification.SENSITIVE,
        raw_authorized=True,
    )
    artifact_id = str(record["artifact_id"])
    encrypted = (tmp_path / "vault" / f"{artifact_id}.bin").read_bytes()
    assert b"private prompt" not in encrypted
    assert store.get(artifact_id) == b"private prompt"


def test_restricted_artifact_is_never_persisted(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path, MemoryKeyProvider())
    with pytest.raises(ValueError):
        store.put(
            b"secret-token",
            project_id="project-1",
            media_type="text/plain",
            classification=Classification.RESTRICTED,
            raw_authorized=True,
        )

