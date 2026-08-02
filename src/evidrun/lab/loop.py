"""Laço nativo e limitado de um turno do Lab Agent.

O laço não conhece o event ledger. Rastro de tool e eventos de apresentação entram por
portas estreitas e pertencem à sessão de chat, nunca a uma Run.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, cast

from evidrun.contracts.lab_agent.envelope import LabAgentEnvelope, LabAgentMessageRole
from evidrun.contracts.lab_agent.errors import LabAgentError, LabAgentErrorCode
from evidrun.infrastructure.providers.openai_responses import (
    ProviderFunctionCall,
    ProviderRequestError,
    extract_function_calls,
    extract_output_text,
    extract_response_id,
    extract_usage,
)
from evidrun.lab.budgets import TurnBudgetGuard, TurnLimits
from evidrun.lab.protocol import LabTool, LabToolContext
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
    error_payload,
    parse_arguments,
    refusal_error,
    validate_schema,
    workspace_id,
)
from evidrun.providers.profile import ProviderProfile
from evidrun.shared.ports import ProviderPort
from evidrun.shared.types import canonical_json, sha256_json


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
                        budget="max_provider_round_trips_per_turn",
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
                terminal = self._service_calls(
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

    def _service_calls(
        self,
        calls: tuple[ProviderFunctionCall, ...],
        *,
        state: LabTurnState,
        envelope: LabAgentEnvelope,
        effective: Mapping[str, LabTool],
        context: LabToolContext,
        guard: TurnBudgetGuard,
        trace_sink: LabToolTraceSink,
        policy: LabToolPolicy,
        emit: LabUiEventSink | None,
        cancelled: CancellationProbe,
    ) -> LabTurnTerminal | None:
        for call in calls:
            arguments, parse_error = parse_arguments(call.arguments, call.name)
            state.transcript.append(
                {
                    "type": "function_call",
                    "call_id": call.call_id,
                    "name": call.name,
                    "arguments": call.arguments,
                }
            )
            tool = effective.get(call.name)
            if tool is None:
                code = (
                    LabAgentErrorCode.CATALOG_TOOL_NOT_OFFERED
                    if call.name in self.catalog
                    else LabAgentErrorCode.CATALOG_TOOL_UNKNOWN
                )
                error = refusal_error(code, tool_name=call.name)
                terminal = self._refuse(call, arguments, error, state, envelope, trace_sink)
                if terminal is not None:
                    return terminal
                if guard.refusal_exhausted(state.refusals):
                    return self._terminal(
                        state,
                        LabTurnTerminalName.BUDGET_EXHAUSTED,
                        error=error,
                        budget="max_refusals_per_turn",
                        complete=False,
                    )
                continue

            state.tool_calls += 1
            if guard.tool_call_denied(state.tool_calls):
                error = refusal_error(
                    LabAgentErrorCode.BUDGET_TOOL_CALLS_EXHAUSTED,
                    tool_name=call.name,
                )
                self._append_refusal_trace(
                    trace_sink, envelope, context, call.name, arguments, error
                )
                return self._terminal(
                    state,
                    LabTurnTerminalName.BUDGET_EXHAUSTED,
                    error=error,
                    budget="max_tool_calls_per_turn",
                    complete=False,
                )
            if guard.wall_exhausted():
                error = refusal_error(
                    LabAgentErrorCode.BUDGET_WALL_TIME_EXHAUSTED,
                    tool_name=call.name,
                )
                self._append_refusal_trace(
                    trace_sink, envelope, context, call.name, arguments, error
                )
                return self._terminal(
                    state,
                    LabTurnTerminalName.BUDGET_EXHAUSTED,
                    error=error,
                    budget="max_wall_seconds_per_turn",
                    complete=False,
                )

            error = parse_error or validate_schema(tool.provider_schema(), arguments, call.name)
            if error is None:
                error = policy.check_scope(tool, arguments, context)
            if error is None:
                error = policy.check_classification(tool, arguments, context)
            if error is not None:
                terminal = self._refuse(call, arguments, error, state, envelope, trace_sink)
                if terminal is not None:
                    return terminal
                if guard.refusal_exhausted(state.refusals):
                    return self._terminal(
                        state,
                        LabTurnTerminalName.BUDGET_EXHAUSTED,
                        error=error,
                        budget="max_refusals_per_turn",
                        complete=False,
                    )
                continue

            self._emit(
                emit,
                {
                    "type": "tool",
                    "source": "live",
                    "id": call.call_id,
                    "name": call.name,
                    "status": "running",
                    "argumentsSummary": canonical_json(arguments),
                },
            )
            try:
                result = tool.execute(arguments, context)
            except Exception:
                trace_sink.append_tool_trace(
                    session_id=envelope.session_id,
                    workspace_id=workspace_id(context),
                    turn_sequence=context.turn_sequence,
                    tool_name=call.name,
                    arguments=arguments,
                    outcome="failed",
                )
                self._emit(
                    emit,
                    {
                        "type": "tool",
                        "source": "live",
                        "id": call.call_id,
                        "name": call.name,
                        "status": "failed",
                    },
                )
                return self._terminal(
                    state,
                    LabTurnTerminalName.PROVIDER_FAILED,
                    content="A tool não devolveu um resultado utilizável.",
                    complete=False,
                )
            trace_sink.append_tool_trace(
                session_id=envelope.session_id,
                workspace_id=workspace_id(context),
                turn_sequence=context.turn_sequence,
                tool_name=call.name,
                arguments=arguments,
                requested_refs=result.requested_refs,
                returned_refs=result.returned_refs,
                outcome="completed",
            )
            state.returned_refs.extend(result.returned_refs)
            state.proposed = state.proposed or call.name == "propose_draft"
            output = canonical_json(result.content)
            state.transcript.append(
                {"type": "function_call_output", "call_id": call.call_id, "output": output}
            )
            self._emit(
                emit,
                {
                    "type": "tool",
                    "source": "live",
                    "id": call.call_id,
                    "name": call.name,
                    "status": "completed",
                    "resultSummary": output,
                },
            )
            if cancelled():
                return self._terminal(
                    state,
                    LabTurnTerminalName.CANCELLED,
                    content="Turno cancelado após registrar o trabalho parcial.",
                    complete=False,
                )
        return None

    def _refuse(
        self,
        call: ProviderFunctionCall,
        arguments: Mapping[str, Any],
        error: LabAgentError,
        state: LabTurnState,
        envelope: LabAgentEnvelope,
        trace_sink: LabToolTraceSink,
    ) -> LabTurnTerminal | None:
        state.refusals += 1
        digest = sha256_json(
            {"tool_name": call.name, "arguments": arguments, "refusal_code": error.code.value}
        )
        repeated = digest in state.refusal_digests
        state.refusal_digests.add(digest)
        self._append_refusal_trace(
            trace_sink,
            envelope,
            LabToolContext(
                scope=envelope.scope,
                session_id=envelope.session_id,
                turn_sequence=max((m.sequence for m in envelope.history), default=1),
            ),
            call.name,
            arguments,
            error,
        )
        output = canonical_json({"error": error_payload(error)})
        state.transcript.append(
            {"type": "function_call_output", "call_id": call.call_id, "output": output}
        )
        if repeated:
            return self._terminal(
                state,
                LabTurnTerminalName.REPEATED_REFUSAL,
                content=output,
                error=error,
                complete=False,
            )
        return None

    @staticmethod
    def _append_refusal_trace(
        trace_sink: LabToolTraceSink,
        envelope: LabAgentEnvelope,
        context: LabToolContext,
        tool_name: str,
        arguments: Mapping[str, Any],
        error: LabAgentError,
    ) -> None:
        trace_sink.append_tool_trace(
            session_id=envelope.session_id,
            workspace_id=workspace_id(context),
            turn_sequence=context.turn_sequence,
            tool_name=tool_name,
            arguments=arguments,
            outcome="refused",
            refusal_code=error.code.value,
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
                budget="max_wall_seconds_per_turn",
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
        budget: str | None = None,
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
