"""Read a Subject input back from the canonical store, verifying its identity."""

from __future__ import annotations

from evidrun.contracts import ArtifactRef
from evidrun.infrastructure.artifacts.store import ArtifactStore


class ArtifactInputMaterializer:
    def __init__(self, artifact_store: ArtifactStore) -> None:
        self.artifact_store = artifact_store

    def resolve_text(self, reference: ArtifactRef, *, project_id: str | None = None) -> str:
        """Resolve a text input, rejecting classified or non-text material.

        The active runtime has no classified materialization boundary, so a
        sensitive or restricted reference fails here rather than reaching a Subject.
        """

        if reference.classification.value not in {"public", "internal"}:
            raise ValueError("the active runtime rejects classified Subject inputs")
        if reference.media_type != "text/plain":
            raise ValueError("the deterministic adapter requires text/plain")
        content = self.artifact_store.get_verified(reference, project_id=project_id)
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("Subject input is not valid UTF-8") from exc
