"""Health, provider inventory, and the read-only catalog projections."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from evidrun import __version__
from evidrun.contracts.scope import HTTP_STATUS_BY_CODE
from evidrun.entrypoints.api.context import ApiContext
from evidrun.entrypoints.api.schemas import ProjectCreateRequest, WorkspaceCreateRequest
from evidrun.infrastructure.database.read_model import projections
from evidrun.infrastructure.database.scope_errors import (
    ScopeRejected,
    ScopeStorageUnavailable,
)


def _scope_http_error(
    exc: ScopeRejected | ScopeStorageUnavailable,
) -> HTTPException:
    return HTTPException(
        status_code=HTTP_STATUS_BY_CODE[exc.error.code],
        detail=exc.error.model_dump(mode="json"),
    )


def create_platform_router(
    *, context: ApiContext, authorize: Callable[..., Any]
) -> APIRouter:
    router = APIRouter(prefix="/api/v1")
    settings = context.settings
    provider_credentials = context.provider_credentials
    benchmarks = context.benchmarks

    @router.get("/health")
    async def health(_: None = Depends(authorize)) -> dict[str, Any]:
        return {
            "status": "ok",
            "version": __version__,
            "database": str(settings.database_path),
            "schema_version": "1",
        }

    @router.get("/doctor")
    async def doctor(_: None = Depends(authorize)) -> dict[str, Any]:
        credential = provider_credentials.lookup(settings.default_provider)
        return {
            "healthy": settings.database_path.exists(),
            "data_dir": str(settings.data_dir),
            "database": str(settings.database_path),
            "artifacts": str(settings.artifacts_dir),
            "benchmark_available": (benchmarks / "experiments/crl-ctx-002-demo.yaml").exists(),
            "network_required_for_demo": False,
            "default_provider": settings.default_provider.public_dict(),
            "provider_credential_available": credential.available,
            "provider_credential_availability": credential.availability.value,
        }

    @router.get("/providers")
    async def providers(_: None = Depends(authorize)) -> list[dict[str, Any]]:
        profile = settings.default_provider
        # One lookup per response: `get` followed by `source` probed the OS backend twice.
        return [
            {
                **profile.public_dict(),
                "default": True,
                **provider_credentials.lookup(profile).document(),
            }
        ]

    @router.get("/providers/default")
    async def default_provider(_: None = Depends(authorize)) -> dict[str, Any]:
        profile = settings.default_provider
        return {
            **profile.public_dict(),
            "default": True,
            **provider_credentials.lookup(profile).document(),
        }

    return router


def create_catalog_router(
    *, context: ApiContext, authorize: Callable[..., Any]
) -> APIRouter:
    """Workspace/Project commands and direct catalog projections."""

    router = APIRouter(prefix="/api/v1")
    repository = context.repository

    @router.get("/dashboard")
    async def dashboard(_: None = Depends(authorize)) -> dict[str, Any]:
        return repository.read_model.latest_dashboard()

    @router.get("/workspaces")
    async def workspaces(_: None = Depends(authorize)) -> list[dict[str, Any]]:
        try:
            return repository.read_model.list_workspaces()
        except (ScopeRejected, ScopeStorageUnavailable) as exc:
            raise _scope_http_error(exc) from exc

    @router.post("/workspaces", status_code=status.HTTP_201_CREATED)
    async def create_workspace(
        payload: WorkspaceCreateRequest, _: None = Depends(authorize)
    ) -> dict[str, Any]:
        try:
            row = repository.catalog.create_workspace(payload.name)
        except (ScopeRejected, ScopeStorageUnavailable) as exc:
            raise _scope_http_error(exc) from exc
        return projections.workspace_document(row)

    @router.get("/projects")
    async def projects(
        workspace_id: str | None = None, _: None = Depends(authorize)
    ) -> list[dict[str, Any]]:
        try:
            return repository.read_model.list_projects(workspace_id)
        except (ScopeRejected, ScopeStorageUnavailable) as exc:
            raise _scope_http_error(exc) from exc

    @router.post("/projects", status_code=status.HTTP_201_CREATED)
    async def create_project(
        payload: ProjectCreateRequest, _: None = Depends(authorize)
    ) -> dict[str, Any]:
        try:
            row = repository.catalog.create_project(payload.workspace_id, payload.name)
        except (ScopeRejected, ScopeStorageUnavailable) as exc:
            raise _scope_http_error(exc) from exc
        return projections.project_document(row)

    @router.get("/experiments")
    async def experiments(_: None = Depends(authorize)) -> list[dict[str, Any]]:
        return repository.read_model.latest_dashboard()["experiments"]

    return router
