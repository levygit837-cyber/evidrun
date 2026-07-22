from __future__ import annotations

from collections.abc import AsyncIterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class SubjectResult:
    output: str
    evidence: tuple[str, ...]
    metadata: Mapping[str, Any]


class LabAgentPort(Protocol):
    async def respond(self, session_id: str, message: str) -> Mapping[str, Any]: ...


class SubjectRunnerPort(Protocol):
    @property
    def name(self) -> str: ...

    async def execute(self, objective: str, context: str) -> SubjectResult: ...


class ProviderPort(Protocol):
    async def invoke(self, request: Mapping[str, Any]) -> Mapping[str, Any]: ...


class ToolEnvironmentPort(Protocol):
    async def execute(self, tool: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]: ...


class EventSink(Protocol):
    def append(self, run_id: str, event_type: str, payload: Mapping[str, Any]) -> Any: ...


class ArtifactStorePort(Protocol):
    def put(self, content: bytes, *, media_type: str, classification: str) -> Mapping[str, Any]: ...

    def get(self, artifact_id: str) -> bytes: ...


class GraderPort(Protocol):
    @property
    def name(self) -> str: ...

    def grade(self, output: str, evidence: Sequence[str]) -> Mapping[str, Any]: ...


class ApprovalGateway(Protocol):
    async def request(self, action: str, details: Mapping[str, Any]) -> str: ...


class TraceExporter(Protocol):
    async def export(self, run_id: str) -> AsyncIterator[bytes]: ...


class TraceImporter(Protocol):
    async def ingest(self, payload: bytes) -> str: ...

