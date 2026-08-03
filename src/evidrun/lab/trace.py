"""Portas estreitas para rastro, policy e progresso do laço."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Protocol

from evidrun.contracts.lab_agent.errors import LabAgentError
from evidrun.lab.protocol import LabTool, LabToolContext

LabUiEvent = Mapping[str, Any]
LabUiEventSink = Callable[[LabUiEvent], None]
CancellationProbe = Callable[[], bool]


class LabToolTraceSink(Protocol):
    def append_tool_trace(
        self,
        *,
        session_id: str,
        workspace_id: str,
        turn_sequence: int,
        tool_name: str,
        arguments: Any,
        requested_refs: tuple[Any, ...] = (),
        returned_refs: tuple[Any, ...] = (),
        outcome: str,
        refusal_code: str | None = None,
    ) -> Any: ...


class LabToolPolicy(Protocol):
    """As duas etapas que dependem do repository, depois do schema local."""

    def check_scope(
        self, tool: LabTool, arguments: Mapping[str, Any], context: LabToolContext
    ) -> LabAgentError | None: ...

    def check_classification(
        self, tool: LabTool, arguments: Mapping[str, Any], context: LabToolContext
    ) -> LabAgentError | None: ...


class AllowingLabToolPolicy:
    """Policy explícita para tools que não resolvem refs nem leem conteúdo classificado."""

    def check_scope(
        self, tool: LabTool, arguments: Mapping[str, Any], context: LabToolContext
    ) -> LabAgentError | None:
        del tool, arguments, context
        return None

    def check_classification(
        self, tool: LabTool, arguments: Mapping[str, Any], context: LabToolContext
    ) -> LabAgentError | None:
        del tool, arguments, context
        return None
