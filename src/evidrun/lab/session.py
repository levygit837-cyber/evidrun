"""Composição de um turno persistido do Lab Agent.

O laço permanece independente de banco e transporte; esta camada fixa a ordem em que
pertencimento, transcript, catálogo e persistência cercam uma execução ao vivo.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Mapping
from contextlib import suppress
from dataclasses import dataclass

from evidrun.contracts.lab_agent.envelope import (
    LabAgentEnvelope,
    LabAgentMessage,
    LabAgentMessageRole,
    LabAgentTurnLimits,
)
from evidrun.contracts.lab_agent.scope import LabAgentSessionScope
from evidrun.infrastructure.database import Repository
from evidrun.infrastructure.database.lab_records import LabSession
from evidrun.lab.instructions.compose import ComposedInstruction, compose_instruction
from evidrun.lab.loop import LabAgentLoop
from evidrun.lab.protocol import LabTool
from evidrun.lab.tools import build_catalog, build_proposal_tools, build_read_tools, offered_tools
from evidrun.lab.tools.read_repository import SqlAlchemyLabReadRepository
from evidrun.lab.tools.registry import CapabilityCatalogSource
from evidrun.lab.trace import CancellationProbe, LabUiEvent
from evidrun.providers.profile import ProviderProfile
from evidrun.shared.ports import ProviderPort

__all__ = ["DEFAULT_TURN_LIMITS", "LabAgentSessionService"]


# Estes tetos permitem uma conversa com várias leituras, mas limitam custo, recusas e o
# tempo de uma conexão HTTP sem anunciar nenhum budget que o runtime não fiscalize.
DEFAULT_TURN_LIMITS = LabAgentTurnLimits(
    max_tool_calls_per_turn=12,
    max_provider_round_trips_per_turn=8,
    max_wall_seconds_per_turn=120,
    max_refusals_per_turn=4,
    max_output_tokens_per_round_trip=2_048,
)

@dataclass(frozen=True, slots=True)
class _TurnSetup:
    """O que o turno recebe: catálogo, envelope e instrução do mesmo catálogo efetivo."""

    catalog: Mapping[str, LabTool]
    envelope: LabAgentEnvelope
    instruction: ComposedInstruction



class LabAgentSessionService:
    """Conduz o turno sem misturar eventos de apresentação ao ledger de Runs."""

    def __init__(
        self,
        repository: Repository,
        provider: ProviderPort,
        *,
        profile: ProviderProfile,
        capability_source: CapabilityCatalogSource,
        limits: LabAgentTurnLimits = DEFAULT_TURN_LIMITS,
    ) -> None:
        self._repository = repository
        self._provider = provider
        self._profile = profile
        self._capability_source = capability_source
        self._limits = limits

    def require_session(self, *, session_id: str, workspace_id: str) -> None:
        """Antecipa somente o enforcement necessário para ainda responder por HTTP."""

        self._repository.lab.get_session(
            session_id=session_id,
            workspace_id=workspace_id,
        )

    async def run_turn(
        self,
        *,
        session_id: str,
        workspace_id: str,
        content: str,
        cancelled: CancellationProbe,
    ) -> AsyncIterator[LabUiEvent]:
        """Produz eventos enquanto o turno roda e preserva a ordem dos fatos persistidos."""

        session = self._repository.lab.get_session(
            session_id=session_id,
            workspace_id=workspace_id,
        )
        self._repository.lab.append_message(
            session_id=session_id,
            workspace_id=workspace_id,
            role="human",
            content=content,
        )
        setup = self._prepare(session_id=session_id, workspace_id=workspace_id, session=session)
        catalog, envelope, instruction = setup.catalog, setup.envelope, setup.instruction
        queue: asyncio.Queue[LabUiEvent] = asyncio.Queue()

        async def execute_turn() -> None:
            # A instrução é composta do mesmo catálogo efetivo que o envelope anuncia e o
            # executor impõe, então prompt e enforcement não podem divergir.
            terminal = await LabAgentLoop(
                self._provider,
                catalog,
                profile=self._profile,
                instructions=instruction.text,
            ).execute(
                envelope,
                trace_sink=self._repository.lab,
                emit=queue.put_nowait,
                cancelled=cancelled,
            )
            if terminal.complete and terminal.content:
                # Só terminal completo carrega fala do modelo. Os demais trazem texto do
                # próprio runtime — "Turno cancelado", "O provider não devolveu uma resposta
                # utilizável" — e gravá-lo como `agent` colocaria aviso de infraestrutura na
                # boca do modelo. Pior: o transcript é reenviado a cada round-trip, então na
                # mensagem seguinte o modelo leria aquilo como algo que ele mesmo disse.
                #
                # O humano não perde o fato: o terminal incompleto chega pelos eventos `status`
                # e `error`, e é assim que o laço já o apresenta.
                self._repository.lab.append_message(
                    session_id=session_id,
                    workspace_id=workspace_id,
                    role="agent",
                    content=terminal.content,
                )

        execution = asyncio.create_task(execute_turn())
        pending_get: asyncio.Task[LabUiEvent] | None = None
        try:
            while not execution.done() or not queue.empty():
                if not queue.empty():
                    yield queue.get_nowait()
                    continue
                pending_get = asyncio.create_task(queue.get())
                done, _pending = await asyncio.wait(
                    (execution, pending_get),
                    return_when=asyncio.FIRST_COMPLETED,
                )
                if pending_get in done:
                    yield pending_get.result()
                    pending_get = None
                else:
                    pending_get.cancel()
                    with suppress(asyncio.CancelledError):
                        await pending_get
                    pending_get = None
            # A exceção do laço pertence ao consumidor; observar a task aqui impede que uma
            # falha vire aviso tardio e garante que ela nunca seja engolida pela ponte.
            await execution
        finally:
            if pending_get is not None:
                pending_get.cancel()
                with suppress(asyncio.CancelledError):
                    await pending_get
            if not execution.done():
                execution.cancel()
            # Desconexão fecha o gerador: sempre observar/cancelar a task evita provider
            # órfão continuando a trabalhar depois que já não existe consumidor do turno.
            with suppress(asyncio.CancelledError):
                await execution

    def _prepare(
        self, *, session_id: str, workspace_id: str, session: LabSession
    ) -> _TurnSetup:
        """Monta o que o turno recebe, separado de como o turno é conduzido.

        Catálogo, envelope e instrução mudam quando muda o que é divulgado ao modelo. O laço
        abaixo muda quando muda a condução — ponte de eventos, cancelamento, persistência do
        terminal. Manter as duas coisas numa função só obrigaria quem lê a ponte a atravessar a
        montagem do envelope, que não a afeta.

        O catálogo é montado uma vez e serve os três: o envelope anuncia seus nomes, a instrução
        os descreve e o executor os impõe. Três montagens divergiriam no primeiro patch.
        """

        scope = LabAgentSessionScope.model_validate(session.scope_document())
        catalog = build_catalog(
            (
                *build_read_tools(
                    SqlAlchemyLabReadRepository(
                        self._repository.unit_of_work, self._capability_source
                    )
                ),
                *build_proposal_tools(self._repository),
            )
        )
        effective = offered_tools(catalog, scope.form)
        history = tuple(
            LabAgentMessage(
                role=LabAgentMessageRole(message.role),
                content=message.content,
                sequence=message.sequence,
            )
            for message in self._repository.lab.list_messages(
                session_id=session_id, workspace_id=workspace_id
            )
        )
        return _TurnSetup(
            catalog=catalog,
            envelope=LabAgentEnvelope(
                session_id=session_id,
                scope=scope,
                history=history,
                offered_tools=tuple(effective),
                limits=self._limits,
            ),
            instruction=compose_instruction(
                scope=scope,
                offered=effective,
                catalog=self._capability_source.capability_catalog(),
                limits=self._limits,
            ),
        )
