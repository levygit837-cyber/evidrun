"""Sessões e mensagens tipadas do Lab Agent na borda HTTP."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from evidrun.contracts.lab_agent.scope import LabAgentSessionScope
from evidrun.entrypoints.api.context import ApiContext
from evidrun.entrypoints.api.lab_errors import (
    invalid_session_scope,
    lab_http_error,
    lab_store_error,
    storage_http_error,
)
from evidrun.entrypoints.api.schemas import LabMessageCreate, LabSessionCreate
from evidrun.infrastructure.database.lab import LabMessage, LabSession
from evidrun.infrastructure.database.lab_errors import LabStoreRejected
from evidrun.infrastructure.database.scope_errors import ScopeStorageUnavailable


def _http_error(
    exc: LabStoreRejected | ValidationError | ScopeStorageUnavailable,
) -> HTTPException:
    """Uma porta só para as três origens de recusa que estas rotas conhecem."""

    if isinstance(exc, ScopeStorageUnavailable):
        return storage_http_error(exc)
    if isinstance(exc, ValidationError):
        return lab_http_error(invalid_session_scope())
    return lab_http_error(lab_store_error(exc))


def _session_document(row: LabSession) -> dict[str, Any]:
    """A projeção é do store, para que CLI e API nunca divirjam (ADR 0025)."""

    return row.document()


def _message_document(row: LabMessage) -> dict[str, Any]:
    return {
        "id": row.id,
        "session_id": row.session_id,
        "role": row.role,
        "content": row.content,
        "sequence": row.sequence,
        "created_at": row.created_at.isoformat(),
    }


def create_lab_router(*, context: ApiContext, authorize: Callable[..., Any]) -> APIRouter:
    """Expõe apenas o store que revalida pertencimento ao escrever e hidratar."""

    router = APIRouter(prefix="/api/v1")
    store = context.repository.lab

    @router.post("/lab/sessions")
    async def create_session(
        payload: LabSessionCreate, _: None = Depends(authorize)
    ) -> dict[str, Any]:
        try:
            # `model_validate` em vez do construtor: o payload carrega `focus_kind` como texto,
            # e é o próprio contrato que precisa recusar um valor fora do vocabulário fechado.
            # Converter aqui antes da validação moveria essa recusa para um `ValueError` cru.
            scope = LabAgentSessionScope.model_validate(
                {
                    "workspace_id": payload.workspace_id,
                    "project_id": payload.project_id,
                    "focus_kind": payload.focus_kind,
                    "focus_id": payload.focus_id,
                }
            )
            row = store.create_session(
                workspace_id=scope.workspace_id,
                project_id=scope.project_id,
                focus_kind=None if scope.focus_kind is None else scope.focus_kind.value,
                focus_id=scope.focus_id,
                title=payload.title,
            )
        except (LabStoreRejected, ValidationError) as exc:
            raise _http_error(exc) from exc
        return _session_document(row)

    @router.get("/lab/sessions")
    async def list_sessions(
        workspace_id: str, _: None = Depends(authorize)
    ) -> list[dict[str, Any]]:
        try:
            rows = store.list_sessions(workspace_id=workspace_id)
        except (LabStoreRejected, ScopeStorageUnavailable) as exc:
            raise _http_error(exc) from exc
        return [_session_document(row) for row in rows]

    @router.get("/lab/sessions/{session_id}")
    async def get_session(
        session_id: str, workspace_id: str, _: None = Depends(authorize)
    ) -> dict[str, Any]:
        try:
            row = store.get_session(session_id=session_id, workspace_id=workspace_id)
        except LabStoreRejected as exc:
            raise _http_error(exc) from exc
        return _session_document(row)

    @router.get("/lab/sessions/{session_id}/messages")
    async def list_messages(
        session_id: str, workspace_id: str, _: None = Depends(authorize)
    ) -> list[dict[str, Any]]:
        try:
            rows = store.list_messages(session_id=session_id, workspace_id=workspace_id)
        except LabStoreRejected as exc:
            raise _http_error(exc) from exc
        return [_message_document(row) for row in rows]

    @router.post("/lab/sessions/{session_id}/messages")
    async def append_message(
        session_id: str,
        payload: LabMessageCreate,
        _: None = Depends(authorize),
    ) -> dict[str, Any]:
        try:
            row = store.append_message(
                session_id=session_id,
                workspace_id=payload.workspace_id,
                role="human",
                content=payload.content,
            )
        except LabStoreRejected as exc:
            raise _http_error(exc) from exc
        return _message_document(row)

    return router
