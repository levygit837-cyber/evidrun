"""Laço nativo e limitado de um turno do Lab Agent.

O laço não conhece o event ledger. Rastro de tool e eventos de apresentação entram por
portas estreitas e pertencem à sessão de chat, nunca a uma Run.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, cast

from evidrun.contracts.lab_agent.envelope import LabAgentEnvelope, LabAgentMessageRole
from evidrun.contracts.lab_agent.errors import LabAgentError
from evidrun.infrastructure.providers.openai_responses import (
    ProviderRequestError,
    extract_function_calls,
    extract_output_text,
    extract_response_id,
    extract_usage,
)
from evidrun.lab.budgets import TurnBudgetGuard, TurnLimits
from evidrun.lab.protocol import LabTool, LabToolContext
from evidrun.lab.serving import ToolCallServer
from evidrun.lab.tools import offered_tools
from evidrun.lab.trace import (
    AllowingLabToolPolicy,
    CancellationProbe,
    LabToolPolicy,
    LabToolTraceSink,
    LabUiEventSink,
)
from evidrun.lab.turn import (
    LabTurnState,
    LabTurnTerminal,
    LabTurnTerminalName,
    TurnBudget,
)
from evidrun.providers.profile import ProviderProfile
from evidrun.shared.ports import ProviderPort


class LabAgentLoop:
    """Executa um turno segundo as três decisões e as cinco etapas normativas."""

    def __init__(
        self,
        provider: ProviderPort,
        catalog: Mapping[str, LabTool],
        *,
        profile: ProviderProfile | None = None,
        instructions: str = "",
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.provider = provider
        self.catalog = catalog
        self.profile = profile or ProviderProfile.load_default()
        self.instructions = instructions
        self.clock = clock

    async def execute(
        self,
        envelope: LabAgentEnvelope,
        *,
        trace_sink: LabToolTraceSink,
        policy: LabToolPolicy | None = None,
        emit: LabUiEventSink | None = None,
        cancelled: CancellationProbe | None = None,
    ) -> LabTurnTerminal:
        scope = envelope.scope
        limits = cast(TurnLimits, envelope.limits)  # pyright: ignore[reportUnknownMemberType]
        effective = offered_tools(self.catalog, scope.form)
        if set(envelope.offered_tools) != set(effective):
            raise ValueError("O envelope não anuncia exatamente o catálogo efetivo da sessão.")
        turn_sequence = max((message.sequence for message in envelope.history), default=1)
        state = LabTurnState(transcript=self._initial_transcript(envelope))
        guard = TurnBudgetGuard(limits, **({} if self.clock is None else {"clock": self.clock}))
        context = LabToolContext(
            scope=scope,
            session_id=envelope.session_id,
            turn_sequence=turn_sequence,
        )
        active_policy = policy or AllowingLabToolPolicy()
        is_cancelled = cancelled or (lambda: False)
        self._emit(emit, {"type": "status", "source": "live", "label": "working"})

        while True:
            terminal = self._boundary_terminal(state, guard, is_cancelled)
            if terminal is not None:
                return self._finish(terminal, state, emit)
            if guard.round_trip_denied(state.provider_round_trips):
                return self._finish(
                    self._terminal(
                        state,
                        LabTurnTerminalName.BUDGET_EXHAUSTED,
                        budget=TurnBudget.ROUND_TRIPS,
                        complete=False,
                    ),
                    state,
                    emit,
                )
            try:
                response = await self.provider.invoke(self._request(state, effective, envelope))
                state.provider_round_trips += 1
                extract_response_id(response)
                self._record_usage(state, extract_usage(response))
                calls = extract_function_calls(response)
            except ProviderRequestError, ValueError, TypeError, KeyError:
                return self._finish(
                    self._terminal(
                        state,
                        LabTurnTerminalName.PROVIDER_FAILED,
                        content="O provider não devolveu uma resposta utilizável.",
                        complete=False,
                    ),
                    state,
                    emit,
                )
            if calls:
                terminal = self._server().serve(
                    calls,
                    state=state,
                    envelope=envelope,
                    effective=effective,
                    context=context,
                    guard=guard,
                    trace_sink=trace_sink,
                    policy=active_policy,
                    emit=emit,
                    cancelled=is_cancelled,
                )
                if terminal is not None:
                    return self._finish(terminal, state, emit)
                continue
            text = extract_output_text(response).strip()
            if not text:
                return self._finish(
                    self._terminal(
                        state,
                        LabTurnTerminalName.PROVIDER_FAILED,
                        content="O provider não devolveu uma resposta utilizável.",
                        complete=False,
                    ),
                    state,
                    emit,
                )
            self._emit(emit, {"type": "message", "source": "live", "content": text})
            name = LabTurnTerminalName.PROPOSED if state.proposed else LabTurnTerminalName.ANSWERED
            return self._finish(self._terminal(state, name, content=text), state, emit)

    def _server(self) -> ToolCallServer:
        """O servidor de tool call, montado com as duas costuras que são estado do laço.

        Recriado por turno em vez de guardado em `__init__` porque ele não carrega estado:
        guardá-lo sugeriria que carrega, e o próximo leitor teria de provar que não.
        """

        return ToolCallServer(
            self.catalog,
            emit_event=self._emit,
            build_terminal=self._terminal,
        )

    def _request(
        self,
        state: LabTurnState,
        effective: Mapping[str, LabTool],
        envelope: LabAgentEnvelope,
    ) -> dict[str, Any]:
        tools = [
            {"type": "function", "name": name, "parameters": tool.provider_schema(), "strict": True}
            for name, tool in effective.items()
        ]
        return {
            "input": list(state.transcript),
            "instructions": self.instructions,
            "tools": tools,
            "tool_choice": "auto",
            "max_output_tokens": envelope.limits.max_output_tokens_per_round_trip,
        }

    @staticmethod
    def _initial_transcript(envelope: LabAgentEnvelope) -> list[dict[str, Any]]:
        roles = {
            LabAgentMessageRole.HUMAN: "user",
            LabAgentMessageRole.AGENT: "assistant",
            LabAgentMessageRole.SYSTEM_NOTE: "developer",
        }
        return [{"role": roles[item.role], "content": item.content} for item in envelope.history]

    @staticmethod
    def _record_usage(state: LabTurnState, usage: Mapping[str, int]) -> None:
        state.input_tokens += usage.get("input_tokens", 0)
        state.output_tokens += usage.get("output_tokens", 0)
        state.total_tokens += usage.get("total_tokens", 0)

    @staticmethod
    def _boundary_terminal(
        state: LabTurnState, guard: TurnBudgetGuard, cancelled: CancellationProbe
    ) -> LabTurnTerminal | None:
        if cancelled():
            return LabAgentLoop._terminal(
                state,
                LabTurnTerminalName.CANCELLED,
                content="Turno cancelado; o trabalho exibido é parcial.",
                complete=False,
            )
        if guard.wall_exhausted():
            return LabAgentLoop._terminal(
                state,
                LabTurnTerminalName.BUDGET_EXHAUSTED,
                budget=TurnBudget.WALL_SECONDS,
                complete=False,
            )
        return None

    @staticmethod
    def _terminal(
        state: LabTurnState,
        name: LabTurnTerminalName,
        *,
        content: str = "",
        complete: bool = True,
        error: LabAgentError | None = None,
        budget: TurnBudget | None = None,
    ) -> LabTurnTerminal:
        return LabTurnTerminal(
            name=name,
            content=content,
            complete=complete,
            error=error,
            budget=budget,
            returned_refs=tuple(state.returned_refs),
            provider_round_trips=state.provider_round_trips,
            tool_calls=state.tool_calls,
            refusals=state.refusals,
            usage=state.usage(),
        )

    @staticmethod
    def _finish(
        terminal: LabTurnTerminal, state: LabTurnState, emit: LabUiEventSink | None
    ) -> LabTurnTerminal:
        del state
        error = terminal.error
        if error is not None:
            LabAgentLoop._emit(emit, {"type": "error", "source": "live", "message": error.message})
        LabAgentLoop._emit(emit, {"type": "status", "source": "live", "label": terminal.name.value})
        LabAgentLoop._emit(emit, {"type": "done", "source": "live"})
        return terminal

    @staticmethod
    def _emit(emit: LabUiEventSink | None, event: Mapping[str, Any]) -> None:
        if emit is not None:
            emit(event)
