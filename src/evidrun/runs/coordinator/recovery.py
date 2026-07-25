"""Rebuild a Subject result from what the ledger and the artifact store persisted.

A Run whose `subject.responded` event survived a crash must be evaluable without
re-invoking the Subject. That is only possible when the response was captured as a
recoverable artifact; a redacted or metadata-only capture is deliberately NOT
recoverable, and the caller terminates the Run instead of guessing.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from pydantic import TypeAdapter

from evidrun.contracts import ArtifactRef
from evidrun.infrastructure.artifacts.store import ArtifactStore
from evidrun.shared.ports import SubjectResult

_json_object = TypeAdapter(dict[str, object])


def recoverable_output_ref(response_event: Mapping[str, object]) -> ArtifactRef | None:
    """The stored output artifact, or `None` when capture kept nothing to recover."""

    payload = cast(Mapping[str, object], response_event["payload"])
    document = payload.get("output_ref")
    if document is None:
        return None
    return ArtifactRef.model_validate(document)


def load_subject_result(
    output_ref: ArtifactRef,
    *,
    artifact_store: ArtifactStore,
    project_id: str,
) -> SubjectResult:
    """Read the persisted result back, rejecting a document of the wrong shape."""

    document = _json_object.validate_json(
        artifact_store.get_verified(output_ref, project_id=project_id)
    )
    output_value = document.get("output")
    evidence_value = document.get("evidence")
    metadata_value = document.get("metadata")
    if (
        not isinstance(output_value, str)
        or not isinstance(evidence_value, list)
        or not all(isinstance(item, str) for item in cast(list[object], evidence_value))
        or not isinstance(metadata_value, list)
    ):
        raise ValueError("persisted Subject result has an invalid shape")
    return SubjectResult(
        output=output_value,
        evidence=tuple(cast(list[str], evidence_value)),
        metadata=_metadata(cast(list[object], metadata_value)),
    )


def _metadata(entries: list[object]) -> dict[str, str | int | float | bool]:
    """Accept only `{key, value}` scalar pairs; anything else is dropped."""

    metadata: dict[str, str | int | float | bool] = {}
    for entry_value in entries:
        if not isinstance(entry_value, dict):
            continue
        entry = cast(dict[str, object], entry_value)
        key = entry.get("key")
        value = entry.get("value")
        if (
            set(entry) == {"key", "value"}
            and isinstance(key, str)
            and isinstance(value, str | int | float | bool)
        ):
            metadata[key] = value
    return metadata
