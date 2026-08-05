"""Transporte SSE de um turno ao vivo do Lab Agent."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Callable
from contextlib import suppress
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from evidrun.entrypoints.api.context import ApiContext
from evidrun.entrypoints.api.lab_errors import lab_http_error, lab_store_error
from evidrun.infrastructure.database.lab_errors import LabStoreRejected


class LabTurnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: str = Field(min_length=1)
    content: str = Field(min_length=1, max_length=100_000)


def create_lab_turn_router(
    *, context: ApiContext, authorize: Callable[..., Any]
) -> APIRouter:
    router = APIRouter(prefix="/api/v1")
    service = context.lab_agent

    @router.post("/lab/sessions/{session_id}/turns")
    async def run_lab_turn(
        session_id: str,
        payload: LabTurnRequest,
        request: Request,
        _: None = Depends(authorize),
    ) -> StreamingResponse:
        try:
            # O pertencimento precisa falhar antes de o ASGI enviar os headers do stream;
            # run_turn repete o enforcement para continuar correto quando usado sem HTTP.
            service.require_session(
                session_id=session_id,
                workspace_id=payload.workspace_id,
            )
        except LabStoreRejected as exc:
            raise lab_http_error(lab_store_error(exc)) from exc

        async def event_stream() -> AsyncIterator[str]:
            disconnected = False

            async def observe_disconnect() -> None:
                nonlocal disconnected
                while not disconnected:
                    if await request.is_disconnected():
                        disconnected = True
                        return
                    await asyncio.sleep(0.05)

            # O aborto do fetch já identifica exatamente o turno em voo. A sonda apenas
            # transporta esse sinal até as fronteiras seguras do laço; um endpoint separado
            # criaria uma segunda identidade de cancelamento sem tornar a tool interrompível.
            poller = asyncio.create_task(observe_disconnect())
            try:
                async for event in service.run_turn(
                    session_id=session_id,
                    workspace_id=payload.workspace_id,
                    content=payload.content,
                    cancelled=lambda: disconnected,
                ):
                    serialized = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
                    yield f"event: {event['type']}\ndata: {serialized}\n\n"
            finally:
                disconnected = True
                poller.cancel()
                # Fechar o poller aqui impede que ele retenha Request depois do fim normal,
                # de uma falha no stream ou do cancelamento da task ASGI.
                with suppress(asyncio.CancelledError):
                    await poller

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    return router
