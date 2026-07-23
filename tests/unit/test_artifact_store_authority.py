from __future__ import annotations

import json
from pathlib import Path

import pytest

from evidrun.infrastructure.artifacts.store import ArtifactStore, MemoryKeyProvider
from evidrun.shared.types import Classification


def test_cas_identity_preserves_project_and_authority_metadata(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "artifacts", MemoryKeyProvider())
    first = store.put_ref(
        b"same bytes",
        project_id="project-a",
        media_type="text/plain",
        classification=Classification.INTERNAL,
    )
    repeated = store.put_ref(
        b"same bytes",
        project_id="project-a",
        media_type="text/plain",
        classification=Classification.INTERNAL,
    )
    other_project = store.put_ref(
        b"same bytes",
        project_id="project-b",
        media_type="text/plain",
        classification=Classification.INTERNAL,
    )
    other_media = store.put_ref(
        b"same bytes",
        project_id="project-a",
        media_type="application/octet-stream",
        classification=Classification.INTERNAL,
    )

    assert repeated == first
    assert first.digest == other_project.digest == other_media.digest
    assert len({first.artifact_id, other_project.artifact_id, other_media.artifact_id}) == 3
    assert store.get_verified(first, project_id="project-a") == b"same bytes"
    with pytest.raises(ValueError, match="metadata"):
        store.get_verified(first, project_id="project-b")


def test_sensitive_result_is_encrypted_and_project_scoped(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "artifacts", MemoryKeyProvider())
    reference = store.put_ref(
        b'{"answer":"synthetic"}',
        project_id="project-sensitive",
        media_type="application/json",
        classification=Classification.SENSITIVE,
        raw_authorized=True,
        ttl_days=7,
    )
    assert store.get_verified(reference, project_id="project-sensitive") == (
        b'{"answer":"synthetic"}'
    )
    assert (
        not (store.vault / f"{reference.artifact_id}.bin")
        .read_bytes()
        .endswith(b'{"answer":"synthetic"}')
    )
    with pytest.raises(ValueError, match="metadata"):
        store.get_verified(reference, project_id="another-project")
    metadata = json.loads(
        (store.metadata / f"{reference.artifact_id}.json").read_text(encoding="utf-8")
    )
    assert metadata["ttl_days"] == 7


def test_purging_one_authority_ref_preserves_shared_cas_content(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "artifacts", MemoryKeyProvider())
    first = store.put_ref(
        b"shared immutable bytes",
        project_id="project-a",
        media_type="text/plain",
        classification=Classification.INTERNAL,
    )
    second = store.put_ref(
        b"shared immutable bytes",
        project_id="project-b",
        media_type="text/plain",
        classification=Classification.INTERNAL,
    )

    store.purge(first.artifact_id)

    with pytest.raises(ValueError, match="metadata"):
        store.get_verified(first, project_id="project-a")
    assert store.get_verified(second, project_id="project-b") == b"shared immutable bytes"
