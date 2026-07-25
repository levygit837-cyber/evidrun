"""Persist every fenced tool interaction as a factual event in the Run ledger.

Each method writes one event under the caller's lease, so a tool interaction the
ledger did not accept did not happen. The `operation_key` per call id makes each
write idempotent under retry.
"""

from __future__ import annotations

from evidrun.contracts import CapabilityDescriptorRef
from evidrun.infrastructure.artifacts.store import ArtifactStore
from evidrun.infrastructure.database import Repository
from evidrun.runs.adapters import ToolTraceSink
from evidrun.shared.types import Classification, canonical_json, sha256_bytes

Lease = tuple[str, str, str, int]


class PersistedToolTrace(ToolTraceSink):
    def __init__(
        self,
        *,
        repository: Repository,
        artifact_store: ArtifactStore,
        run_id: str,
        project_id: str,
        actor_id: str,
        lease: Lease,
    ) -> None:
        self.repository = repository
        self.artifact_store = artifact_store
        self.run_id = run_id
        self.project_id = project_id
        self.actor_id = actor_id
        self.lease = lease

    def called(
        self,
        *,
        capability_ref: CapabilityDescriptorRef,
        call_id: str,
        arguments: str,
    ) -> None:
        arguments_ref = self.artifact_store.put_ref(
            canonical_json({"raw_arguments": arguments}).encode("utf-8"),
            project_id=self.project_id,
            media_type="application/json",
            classification=Classification.INTERNAL,
        )
        self.repository.ledger.append_event(
            run_id=self.run_id,
            event_type="tool.called",
            payload={
                "capability_ref": capability_ref.model_dump(mode="json"),
                "call_id": call_id,
                "input_digest": sha256_bytes(arguments.encode("utf-8")),
                "arguments_ref": arguments_ref.model_dump(mode="json"),
            },
            actor_type="subject",
            actor_id=self.actor_id,
            operation_key=f"tool:{call_id}:called",
            lease=self.lease,
        )

    def completed(
        self,
        *,
        capability_ref: CapabilityDescriptorRef,
        call_id: str,
        result: str,
        classification: Classification,
    ) -> None:
        """The result is stored under the tool's own classification, not the Run's."""

        result_ref = self.artifact_store.put_ref(
            result.encode("utf-8"),
            project_id=self.project_id,
            media_type="application/json",
            classification=classification,
        )
        self.repository.ledger.append_event(
            run_id=self.run_id,
            event_type="tool.completed",
            payload={
                "capability_ref": capability_ref.model_dump(mode="json"),
                "call_id": call_id,
                "result_ref": result_ref.model_dump(mode="json"),
                "reason": None,
            },
            actor_type="tool",
            actor_id=capability_ref.name,
            operation_key=f"tool:{call_id}:completed",
            lease=self.lease,
        )

    def denied(self, *, call_id: str, reason: str) -> None:
        self.repository.ledger.append_event(
            run_id=self.run_id,
            event_type="tool.denied",
            payload={
                "call_id": call_id,
                "decided_by": "runtime-policy",
                "rationale": reason,
            },
            actor_type="system",
            actor_id="runtime-policy",
            operation_key=f"tool:{call_id}:denied",
            lease=self.lease,
        )

    def failed(
        self,
        *,
        capability_ref: CapabilityDescriptorRef,
        call_id: str,
        reason: str,
    ) -> None:
        self.repository.ledger.append_event(
            run_id=self.run_id,
            event_type="tool.failed",
            payload={
                "capability_ref": capability_ref.model_dump(mode="json"),
                "call_id": call_id,
                "result_ref": None,
                "reason": reason,
            },
            actor_type="tool",
            actor_id=capability_ref.name,
            operation_key=f"tool:{call_id}:failed",
            lease=self.lease,
        )
