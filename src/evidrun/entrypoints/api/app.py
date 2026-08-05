"""Compose the API process: build the runtime, then mount one router per family.

`create_app` declares no handler. It resolves settings, opens the database, wires
the optional authority slice, and mounts routers that receive their collaborators
through `ApiContext` instead of capturing them by closure.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

import uvicorn
from fastapi import FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from evidrun import __version__
from evidrun.authority.authenticator import KeyringAuthenticator
from evidrun.authority.repository import AuthorityRepository
from evidrun.authority.router import create_authority_router
from evidrun.authority.service import HumanAuthorityService
from evidrun.authority.verifier import LocalWebAuthnVerifier
from evidrun.entrypoints.api.context import ApiContext
from evidrun.entrypoints.api.routers import (
    create_admission_router,
    create_catalog_router,
    create_comparison_router,
    create_contract_router,
    create_evidence_router,
    create_lab_router,
    create_lab_turn_router,
    create_platform_router,
    create_review_router,
    create_run_read_router,
    create_run_router,
)
from evidrun.evidence.bundle import EvidenceBundleService
from evidrun.infrastructure.artifacts.store import ArtifactStore
from evidrun.infrastructure.database import Database, Repository
from evidrun.infrastructure.providers import OpenAIResponsesProvider, ProviderCredentialStore
from evidrun.lab.session import LabAgentSessionService
from evidrun.lab.tools.registry import AdmissionCapabilityCatalog
from evidrun.runs import EvidrunService
from evidrun.settings import Settings
from evidrun.shared.resources import benchmarks_root

ALLOWED_ORIGINS = (
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "evidrun://app",
    "null",
)

ROUTER_FACTORIES = (
    create_platform_router,
    create_catalog_router,
    create_contract_router,
    create_review_router,
    create_admission_router,
    create_run_router,
    create_run_read_router,
    create_comparison_router,
    create_lab_router,
    create_lab_turn_router,
    create_evidence_router,
)


class AuthoritySlice:
    """The optional human-authority collaborators, present only when enabled."""

    __slots__ = ("repository", "service", "verifier")

    def __init__(self, database: Database, settings: Settings) -> None:
        self.repository = AuthorityRepository(database)
        artifacts = ArtifactStore(settings.artifacts_dir)
        self.verifier = LocalWebAuthnVerifier(self.repository, artifacts)
        self.service = HumanAuthorityService(
            repository=self.repository,
            authenticator=KeyringAuthenticator(),
            artifacts=artifacts,
        )


def create_app(
    *,
    data_dir: Path | None = None,
    launch_token: str | None = None,
    benchmark_root: Path | None = None,
) -> FastAPI:
    settings = Settings.load(data_dir)
    settings.ensure_directories()
    database = Database(settings.database_path)
    database.create_all()

    authority = AuthoritySlice(database, settings) if settings.authority_enabled else None
    repository = Repository(
        database,
        human_attestation_verifier=None if authority is None else authority.verifier,
    )
    service = EvidrunService(repository)
    provider_credentials = ProviderCredentialStore()
    lab_agent = LabAgentSessionService(
        repository,
        OpenAIResponsesProvider(settings.default_provider, provider_credentials),
        profile=settings.default_provider,
        capability_source=AdmissionCapabilityCatalog(
            service.runtime.catalog.capability_envelope()
        ),
    )
    context = ApiContext(
        settings=settings,
        repository=repository,
        service=service,
        bundles=EvidenceBundleService(repository),
        provider_credentials=provider_credentials,
        lab_agent=lab_agent,
        benchmarks=benchmark_root or benchmarks_root(),
    )

    app = _build_app(database, context, launch_token=launch_token)
    authorize = _authorizer(launch_token)
    if authority is not None:
        app.include_router(
            create_authority_router(
                service=authority.service,
                authority_repository=authority.repository,
                repository=repository,
                authorize=authorize,
            )
        )
    for factory in ROUTER_FACTORIES:
        app.include_router(factory(context=context, authorize=authorize))
    return app


def _build_app(
    database: Database, context: ApiContext, *, launch_token: str | None
) -> FastAPI:
    """The app object, its CORS policy, and the state the desktop shell reads."""

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
        yield
        database.dispose()

    app = FastAPI(
        title="Evidrun API",
        version=__version__,
        description="Local-first, auditable context reliability laboratory.",
        lifespan=lifespan,
    )
    app.state.settings = context.settings
    app.state.repository = context.repository
    app.state.service = context.service
    app.state.lab_agent = context.lab_agent
    app.state.runtime_kernel = context.service.runtime
    app.state.launch_token = launch_token
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(ALLOWED_ORIGINS),
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
    )
    return app


def _authorizer(launch_token: str | None) -> Callable[..., Any]:
    """Without a launch token the API is open; with one, every route requires it."""

    async def authorize(authorization: Annotated[str | None, Header()] = None) -> None:
        if launch_token is None:
            return
        if authorization != f"Bearer {launch_token}":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
            )

    return authorize


def run() -> None:
    port = int(os.environ.get("EVIDRUN_PORT", "8765"))
    uvicorn.run(create_app(), host="127.0.0.1", port=port)
