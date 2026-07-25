"""Comparisons, chat sessions, and evidence bundle export."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from evidrun.entrypoints.api.context import ApiContext
from evidrun.entrypoints.api.schemas import ChatMessageCreate, ChatSessionCreate


def create_comparison_router(
    *, context: ApiContext, authorize: Callable[..., Any]
) -> APIRouter:
    router = APIRouter(prefix="/api/v1")
    repository = context.repository

    @router.get("/comparisons")
    async def comparisons(_: None = Depends(authorize)) -> list[dict[str, Any]]:
        return repository.read_model.latest_dashboard()["comparisons"]

    @router.get("/comparisons/{comparison_id}")
    async def comparison(
        comparison_id: str, _: None = Depends(authorize)
    ) -> dict[str, Any]:
        matches = [
            item
            for item in repository.read_model.latest_dashboard()["comparisons"]
            if item["id"] == comparison_id
        ]
        if not matches:
            raise HTTPException(status_code=404, detail="comparison not found")
        return matches[0]

    return router


def create_chat_router(
    *, context: ApiContext, authorize: Callable[..., Any]
) -> APIRouter:
    router = APIRouter(prefix="/api/v1")
    repository = context.repository

    @router.post("/chat/sessions")
    async def create_chat(
        payload: ChatSessionCreate, _: None = Depends(authorize)
    ) -> dict[str, Any]:
        row = repository.catalog.create_chat_session(
            workspace_id=payload.workspace_id,
            title=payload.title,
            scope_type=payload.scope_type,
            scope_id=payload.scope_id,
        )
        return {
            "id": row.id,
            "workspace_id": row.workspace_id,
            "title": row.title,
            "scope_type": row.scope_type,
            "scope_id": row.scope_id,
        }

    @router.get("/chat/sessions")
    async def chat_sessions(_: None = Depends(authorize)) -> list[dict[str, Any]]:
        return repository.read_model.latest_dashboard()["chats"]

    @router.post("/chat/sessions/{session_id}/messages")
    async def add_chat_message(
        session_id: str,
        payload: ChatMessageCreate,
        _: None = Depends(authorize),
    ) -> dict[str, Any]:
        row = repository.catalog.add_chat_message(session_id, payload.role, payload.content)
        return {
            "id": row.id,
            "session_id": row.session_id,
            "role": row.role,
            "content": row.content,
        }

    return router


def create_evidence_router(
    *, context: ApiContext, authorize: Callable[..., Any]
) -> APIRouter:
    """Export is blocking work, so both routes hand it to a thread."""

    router = APIRouter(prefix="/api/v1")
    repository = context.repository
    bundles = context.bundles
    settings = context.settings

    @router.post("/evidence-bundles/{comparison_id}")
    async def export_bundle(
        comparison_id: str, _: None = Depends(authorize)
    ) -> dict[str, Any]:
        target = settings.data_dir / "exports" / f"{comparison_id}.evidrun.zip"
        await asyncio.to_thread(bundles.export_comparison_v2, comparison_id, target)
        return {"path": str(target), "comparison_id": comparison_id}

    @router.post("/runs/{run_id}/evidence-bundles")
    async def export_run_bundle(
        run_id: str, _: None = Depends(authorize)
    ) -> dict[str, Any]:
        try:
            repository.read_model.get_run(run_id)
            target = settings.data_dir / "exports" / f"{run_id}.evidrun.zip"
            await asyncio.to_thread(bundles.export_run_v3, run_id, target)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="run not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"path": str(target), "run_id": run_id, "schema_version": "3"}

    return router
