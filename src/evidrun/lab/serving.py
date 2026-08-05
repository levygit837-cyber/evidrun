"""Servir uma tool call: as cinco etapas, a execução e o rastro de cada tentativa.

Assunto separado do laço de propósito. `loop.py` decide quando ir ao provider e quando o
turno acaba; este módulo decide o que acontece com **uma** tool call. A fronteira existe
porque as duas responsabilidades mudam por razões diferentes: a ordem das etapas vem do
contrato de loop v1, enquanto a orquestração de round-trips vem do transporte do provider.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from evidrun.contracts.lab_agent.envelope import LabAgentEnvelope
from evidrun.contracts.lab_agent.errors import LabAgentError, LabAgentErrorCode
from evidrun.infrastructure.providers.openai_responses import ProviderFunctionCall
from evidrun.lab.budgets import TurnBudgetGuard
from evidrun.lab.protocol import LabTool, LabToolContext, LabToolRejected
from evidrun.lab.trace import (
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
    error_payload,
    parse_arguments,
    refusal_error,
    validate_schema,
    workspace_id,
)
from evidrun.shared.types import canonical_json, sha256_json

__all__ = ["BuildTerminal", "EmitEvent", "ToolCallServer", "append_refusal_trace"]


class EmitEvent(Protocol):
    def __call__(self, emit: LabUiEventSink | None, event: Mapping[str, Any]) -> None: ...


class BuildTerminal(Protocol):
    """Monta o terminal com os contadores do turno, que são estado do laço.

    Injetado em vez de reimplementado aqui: duplicar a montagem faria os dois módulos
    divergirem sobre o que um terminal carrega.
    """

    def __call__(
        self,
        state: LabTurnState,
        name: LabTurnTerminalName,
        *,
        content: str = "",
        complete: bool = True,
        error: LabAgentError | None = None,
        budget: TurnBudget | None = None,
    ) -> LabTurnTerminal: ...


class ToolCallServer:
    """Atravessa as cinco etapas normativas e executa o que sobreviver a elas.

    Recebe `terminal_factory` em vez de construir o terminal por conta própria: o terminal
    carrega contadores do turno inteiro, que são estado do laço. Duplicar essa montagem aqui
    faria os dois lados divergirem sobre o que um terminal contém.
    """

    def __init__(
        self,
        catalog: Mapping[str, LabTool],
        *,
        emit_event: EmitEvent,
        build_terminal: BuildTerminal,
    ) -> None:
        self.catalog = catalog
        self.emit_event = emit_event
        self.build_terminal = build_terminal

    def serve(
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
        """Serve cada chamada em ordem; devolve terminal só quando o turno realmente acaba."""

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
                # Etapa 1, catálogo. Antes de budget de propósito: consumir orçamento com uma
                # tool inexistente puniria o humano por um erro do modelo.
                code = (
                    LabAgentErrorCode.CATALOG_TOOL_NOT_OFFERED
                    if call.name in self.catalog
                    else LabAgentErrorCode.CATALOG_TOOL_UNKNOWN
                )
                terminal = self.refuse_and_maybe_terminate(
                    call,
                    arguments,
                    refusal_error(code, tool_name=call.name),
                    state=state,
                    envelope=envelope,
                    guard=guard,
                    trace_sink=trace_sink,
                )
                if terminal is not None:
                    return terminal
                continue

            # Etapa 2, budget. O teto é sobre tentativas, não sobre tentativas bem formadas,
            # por isso vem antes de schema.
            state.tool_calls += 1
            terminal = self._deny_budget(
                call,
                arguments,
                state=state,
                envelope=envelope,
                context=context,
                guard=guard,
                trace_sink=trace_sink,
            )
            if terminal is not None:
                return terminal

            # Etapas 3 a 5: schema, scope, classification. Schema antes de scope porque uma ref
            # só resolve depois de existir como campo válido; scope antes de classification
            # porque negar por classificação um alvo de outro Project revelaria que ele existe.
            error = parse_error or validate_schema(tool.provider_schema(), arguments, call.name)
            if error is None:
                error = policy.check_scope(tool, arguments, context)
            if error is None:
                error = policy.check_classification(tool, arguments, context)
            if error is not None:
                terminal = self.refuse_and_maybe_terminate(
                    call,
                    arguments,
                    error,
                    state=state,
                    envelope=envelope,
                    guard=guard,
                    trace_sink=trace_sink,
                )
                if terminal is not None:
                    return terminal
                continue

            terminal = self._execute(
                call,
                arguments,
                tool,
                state=state,
                envelope=envelope,
                context=context,
                guard=guard,
                trace_sink=trace_sink,
                emit=emit,
                cancelled=cancelled,
            )
            if terminal is not None:
                return terminal
        return None

    def _execute(
        self,
        call: ProviderFunctionCall,
        arguments: Mapping[str, Any],
        tool: LabTool,
        *,
        state: LabTurnState,
        envelope: LabAgentEnvelope,
        context: LabToolContext,
        guard: TurnBudgetGuard,
        trace_sink: LabToolTraceSink,
        emit: LabUiEventSink | None,
        cancelled: CancellationProbe,
    ) -> LabTurnTerminal | None:
        """Executa a tool aprovada, registra o rastro e devolve terminal só se o turno acabar.

        O cancelamento é checado no fim de propósito: a fronteira segura é depois de a tool
        executar e ser registrada, nunca no meio de uma escrita. Interromper antes do rastro
        apagaria trabalho que o humano pediu.
        """

        self.emit_event(
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
        except LabToolRejected as rejected:
            # Fecha o estado visual iniciado acima sem classificar a recusa como falha real.
            self.emit_event(
                emit,
                {
                    "type": "tool",
                    "source": "live",
                    "id": call.call_id,
                    "name": call.name,
                    "status": "failed",
                },
            )
            return self.refuse_and_maybe_terminate(
                call,
                arguments,
                rejected.error,
                state=state,
                envelope=envelope,
                guard=guard,
                trace_sink=trace_sink,
            )
        except Exception:
            trace_sink.append_tool_trace(
                session_id=envelope.session_id,
                workspace_id=workspace_id(context),
                turn_sequence=context.turn_sequence,
                tool_name=call.name,
                arguments=arguments,
                outcome="failed",
            )
            self.emit_event(
                emit,
                {
                    "type": "tool",
                    "source": "live",
                    "id": call.call_id,
                    "name": call.name,
                    "status": "failed",
                },
            )
            return self.build_terminal(
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
        self.emit_event(
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
            return self.build_terminal(
                state,
                LabTurnTerminalName.CANCELLED,
                content="Turno cancelado após registrar o trabalho parcial.",
                complete=False,
            )
        return None

    def refuse_and_maybe_terminate(
        self,
        call: ProviderFunctionCall,
        arguments: Mapping[str, Any],
        error: LabAgentError,
        *,
        state: LabTurnState,
        envelope: LabAgentEnvelope,
        guard: TurnBudgetGuard,
        trace_sink: LabToolTraceSink,
    ) -> LabTurnTerminal | None:
        """Recusa a chamada e devolve terminal só quando o turno realmente acaba.

        Recusa não interrompe o turno: ela volta ao modelo como resultado da tool call, para
        que o modelo corrija. Só duas condições encerram — repetição exata e o teto de recusas.
        """

        terminal = self._refuse(call, arguments, error, state, envelope, trace_sink)
        if terminal is not None:
            return terminal
        if guard.refusal_exhausted(state.refusals):
            return self.build_terminal(
                state,
                LabTurnTerminalName.BUDGET_EXHAUSTED,
                error=error,
                budget=TurnBudget.REFUSALS,
                complete=False,
            )
        return None

    def _deny_budget(
        self,
        call: ProviderFunctionCall,
        arguments: Mapping[str, Any],
        *,
        state: LabTurnState,
        envelope: LabAgentEnvelope,
        context: LabToolContext,
        guard: TurnBudgetGuard,
        trace_sink: LabToolTraceSink,
    ) -> LabTurnTerminal | None:
        """Nega por teto de turno, registrando a negação ANTES de levantar o terminal.

        A ordem importa e é prova mínima do contrato: registrar depois perderia justamente a
        tentativa que estourou o teto, que é a única evidência de por que o turno acabou.
        """

        denials = (
            (
                guard.tool_call_denied(state.tool_calls),
                LabAgentErrorCode.BUDGET_TOOL_CALLS_EXHAUSTED,
                TurnBudget.TOOL_CALLS,
            ),
            (
                guard.wall_exhausted(),
                LabAgentErrorCode.BUDGET_WALL_TIME_EXHAUSTED,
                TurnBudget.WALL_SECONDS,
            ),
        )
        for denied, code, budget in denials:
            if not denied:
                continue
            error = refusal_error(code, tool_name=call.name)
            append_refusal_trace(trace_sink, envelope, context, call.name, arguments, error)
            return self.build_terminal(
                state,
                LabTurnTerminalName.BUDGET_EXHAUSTED,
                error=error,
                budget=budget,
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
        """Registra a recusa e detecta repetição exata.

        Identidade é digest canônico dos argumentos mais nome da tool mais código do
        resultado. Argumento diferente não é repetição, mesmo que a intenção pareça a mesma:
        o produto não adivinha intenção, e igualdade exata é o que dá um limite testável.
        """

        state.refusals += 1
        digest = sha256_json(
            {"tool_name": call.name, "arguments": arguments, "refusal_code": error.code.value}
        )
        repeated = digest in state.refusal_digests
        state.refusal_digests.add(digest)
        append_refusal_trace(
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
            return self.build_terminal(
                state,
                LabTurnTerminalName.REPEATED_REFUSAL,
                content=output,
                error=error,
                complete=False,
            )
        return None


def append_refusal_trace(
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
