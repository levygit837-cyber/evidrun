from __future__ import annotations

import asyncio
import json
import os
from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any, Literal

import uvicorn
import yaml
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from evidrun import __version__
from evidrun.authority.authenticator import KeyringAuthenticator
from evidrun.authority.repository import AuthorityRepository
from evidrun.authority.router import create_authority_router
from evidrun.authority.service import HumanAuthorityService
from evidrun.authority.verifier import LocalWebAuthnVerifier
from evidrun.contracts import (
    StudyRevision,
    parse_revision,
    semantic_model_dump,
)
from evidrun.contracts.compiler import StudyCompiler
from evidrun.evidence.bundle import EvidenceBundleService
from evidrun.experiments import ExperimentManifest
from evidrun.infrastructure.artifacts.store import ArtifactStore
from evidrun.infrastructure.database import Database, Repository
from evidrun.infrastructure.providers import ProviderCredentialStore
from evidrun.runs import EvidrunService
from evidrun.shared.settings import Settings

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


class ChatSessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workspace_id: str
    title: str = Field(min_length=1, max_length=120)
    scope_type: str | None = None
    scope_id: str | None = None


class ChatMessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: str
    content: str = Field(min_length=1, max_length=100_000)


class ManifestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    yaml: str


class ContractDocumentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document: dict[str, object]
    status: Literal["draft", "proposed"] = "draft"


class ContractDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["accepted", "rejected", "superseded"]
    rationale: str = Field(min_length=1)


class RunEnqueueRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    admission_id: str = Field(min_length=1)


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

    authority_repository: AuthorityRepository | None = None
    authority_service: HumanAuthorityService | None = None
    human_verifier: LocalWebAuthnVerifier | None = None
    if settings.authority_enabled:
        authority_repository = AuthorityRepository(database)
        authority_artifacts = ArtifactStore(settings.artifacts_dir)
        human_verifier = LocalWebAuthnVerifier(authority_repository, authority_artifacts)
        authority_service = HumanAuthorityService(
            repository=authority_repository,
            authenticator=KeyringAuthenticator(),
            artifacts=authority_artifacts,
        )

    repository = Repository(database, human_attestation_verifier=human_verifier)
    service = EvidrunService(repository)
    bundles = EvidenceBundleService(repository)
    provider_credentials = ProviderCredentialStore()
    benchmarks = benchmark_root or REPOSITORY_ROOT / "benchmarks"

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
    app.state.settings = settings
    app.state.repository = repository
    app.state.service = service
    app.state.runtime_kernel = service.runtime
    app.state.launch_token = launch_token

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:5173",
            "http://localhost:5173",
            "evidrun://app",
            "null",
        ],
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
    )

    async def authorize(authorization: Annotated[str | None, Header()] = None) -> None:
        if launch_token is None:
            return
        if authorization != f"Bearer {launch_token}":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")

    if authority_service is not None and authority_repository is not None:
        app.include_router(
            create_authority_router(
                service=authority_service,
                authority_repository=authority_repository,
                repository=repository,
                authorize=authorize,
            )
        )

    @app.get("/api/v1/health")
    async def health(_: None = Depends(authorize)) -> dict[str, Any]:
        return {
            "status": "ok",
            "version": __version__,
            "database": str(settings.database_path),
            "schema_version": "1",
        }

    @app.get("/api/v1/doctor")
    async def doctor(_: None = Depends(authorize)) -> dict[str, Any]:
        return {
            "healthy": settings.database_path.exists(),
            "data_dir": str(settings.data_dir),
            "database": str(settings.database_path),
            "artifacts": str(settings.artifacts_dir),
            "benchmark_available": (benchmarks / "experiments/crl-ctx-002-demo.yaml").exists(),
            "network_required_for_demo": False,
            "default_provider": settings.default_provider.public_dict(),
            "provider_credential_available": bool(
                provider_credentials.get(settings.default_provider)
            ),
        }

    @app.get("/api/v1/providers")
    async def providers(_: None = Depends(authorize)) -> list[dict[str, Any]]:
        profile = settings.default_provider
        return [
            {
                **profile.public_dict(),
                "default": True,
                "credential_available": bool(provider_credentials.get(profile)),
                "credential_source": provider_credentials.source(profile),
            }
        ]

    @app.get("/api/v1/providers/default")
    async def default_provider(_: None = Depends(authorize)) -> dict[str, Any]:
        profile = settings.default_provider
        return {
            **profile.public_dict(),
            "default": True,
            "credential_available": bool(provider_credentials.get(profile)),
            "credential_source": provider_credentials.source(profile),
        }

    @app.get("/api/v1/dashboard")
    async def dashboard(_: None = Depends(authorize)) -> dict[str, Any]:
        return repository.read_model.latest_dashboard()

    @app.get("/api/v1/workspaces")
    async def workspaces(_: None = Depends(authorize)) -> list[dict[str, Any]]:
        return repository.read_model.latest_dashboard()["workspaces"]

    @app.get("/api/v1/projects")
    async def projects(_: None = Depends(authorize)) -> list[dict[str, Any]]:
        return repository.read_model.latest_dashboard()["projects"]

    @app.get("/api/v1/experiments")
    async def experiments(_: None = Depends(authorize)) -> list[dict[str, Any]]:
        return repository.read_model.latest_dashboard()["experiments"]

    @app.post("/api/v1/experiments/validate")
    async def validate_manifest(
        payload: ManifestRequest, _: None = Depends(authorize)
    ) -> dict[str, Any]:
        try:
            manifest = ExperimentManifest.model_validate(yaml.safe_load(payload.yaml))
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {
            "valid": True,
            "digest": manifest.digest,
            "validity": manifest.validity,
            "normalized": manifest.model_dump(mode="json"),
        }

    @app.post("/api/v1/contracts/validate")
    async def validate_contract(
        payload: ContractDocumentRequest, _: None = Depends(authorize)
    ) -> dict[str, Any]:
        try:
            revision = parse_revision(payload.document)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {
            "valid": True,
            "digest": revision.digest,
            "normalized": revision.semantic_document(),
        }

    @app.post("/api/v1/contracts/revisions")
    async def register_contract(
        payload: ContractDocumentRequest, _: None = Depends(authorize)
    ) -> dict[str, Any]:
        try:
            revision = parse_revision(payload.document)
            row = repository.registry.save_contract_revision(revision, status=payload.status)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {
            "id": row.id,
            "contract_type": row.contract_type,
            "logical_id": row.logical_id,
            "revision": row.revision,
            "digest": row.digest,
            "status": row.status,
        }

    @app.get("/api/v1/contracts/revisions")
    async def contract_revisions(_: None = Depends(authorize)) -> list[dict[str, Any]]:
        return repository.read_model.list_contract_revisions()

    @app.post("/api/v1/contracts/revisions/{revision_id}/decisions")
    async def decide_contract(
        revision_id: str,
        payload: ContractDecisionRequest,
        _: None = Depends(authorize),
    ) -> dict[str, Any]:
        try:
            repository.read_model.get_contract_revision(revision_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="contract revision not found") from exc
        del payload
        raise HTTPException(
            status_code=503,
            detail=(
                "verified human authority is unavailable; a trusted WebAuthn verifier "
                "must complete this decision"
            ),
        )

    @app.post("/api/v1/studies/{revision_id}/compile")
    async def compile_study(
        revision_id: str, _: None = Depends(authorize)
    ) -> list[dict[str, Any]]:
        try:
            revision = repository.read_model.get_contract_revision(revision_id)
            if not isinstance(revision, StudyRevision):
                raise ValueError("contract revision is not a StudyRevision")
            registry = repository.registry.contract_registry(revision.project_id)
            specs = StudyCompiler(registry).compile(revision)
            rows = [repository.catalog.save_run_spec(spec) for spec in specs]
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Study revision not found") from exc
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return [
            {
                "id": row.id,
                "digest": row.digest,
                "variant_id": row.variant_id,
                "scenario_id": row.scenario_logical_id,
                "repetition_index": row.repetition_index,
            }
            for row in rows
        ]

    @app.post("/api/v1/run-specs/{run_spec_id}/admit")
    async def admit_run_spec(
        run_spec_id: str, _: None = Depends(authorize)
    ) -> dict[str, Any]:
        try:
            spec = repository.read_model.get_run_spec(run_spec_id)
            admission = service.admission_service.admit(spec)
            row = repository.catalog.save_admission_record(run_spec_id, admission)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="RunSpec not found") from exc
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {
            "id": row.id,
            "decision": admission.decision,
            "digest": admission.digest,
            "missing_requirements": admission.missing_requirements,
        }

    @app.get("/api/v1/run-specs/{run_spec_id}")
    async def run_spec(
        run_spec_id: str, _: None = Depends(authorize)
    ) -> dict[str, Any]:
        try:
            spec = repository.read_model.get_run_spec(run_spec_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="RunSpec not found") from exc
        return {**semantic_model_dump(spec), "digest": spec.digest}

    @app.get("/api/v1/admissions/{admission_id}")
    async def admission(
        admission_id: str, _: None = Depends(authorize)
    ) -> dict[str, Any]:
        try:
            record = repository.read_model.get_admission_record(admission_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="AdmissionRecord not found") from exc
        return {**semantic_model_dump(record), "digest": record.digest}

    @app.post("/api/v1/demo/bootstrap")
    async def bootstrap_demo(_: None = Depends(authorize)) -> dict[str, Any]:
        return await asyncio.to_thread(service.bootstrap_demo, benchmarks)

    @app.get("/api/v1/runs")
    async def runs(_: None = Depends(authorize)) -> list[dict[str, Any]]:
        return repository.read_model.latest_dashboard()["runs"]

    @app.post(
        "/api/v1/run-specs/{run_spec_id}/runs",
        status_code=status.HTTP_202_ACCEPTED,
    )
    async def enqueue_run(
        run_spec_id: str,
        payload: RunEnqueueRequest,
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
        _: None = Depends(authorize),
    ) -> dict[str, Any]:
        try:
            repository.read_model.get_run_spec(run_spec_id)
            repository.read_model.get_admission_record(payload.admission_id)
            run_id, job = service.runtime.coordinator.enqueue(
                run_spec_id=run_spec_id,
                admission_id=payload.admission_id,
                idempotency_key=idempotency_key,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="RunSpec or admission not found") from exc
        except ValueError as exc:
            if "idempotency key" in str(exc):
                raise HTTPException(status_code=409, detail=str(exc)) from exc
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {
            "run_id": run_id,
            "job_id": job.job_id,
            "run_spec_id": run_spec_id,
            "admission_id": payload.admission_id,
            "retry_of": None,
            "status": job.status,
        }

    @app.post(
        "/api/v1/runs/{run_id}/retries",
        status_code=status.HTTP_202_ACCEPTED,
    )
    async def retry_run(
        run_id: str,
        payload: RunEnqueueRequest,
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
        _: None = Depends(authorize),
    ) -> dict[str, Any]:
        try:
            source = repository.read_model.get_run(run_id)
            if source.run_spec_id is None:
                raise HTTPException(
                    status_code=409,
                    detail="legacy Run is not eligible for Runtime Kernel retry",
                )
            if source.status not in {
                "failed",
                "cancelled",
                "budget_exhausted",
                "guardrail_stopped",
            }:
                raise HTTPException(
                    status_code=409,
                    detail="only an unsuccessful terminal Run can be retried",
                )
            spec = repository.read_model.get_run_spec(source.run_spec_id)
            retry_admission = repository.read_model.get_admission_record(payload.admission_id)
            if (
                retry_admission.decision != "admitted"
                or retry_admission.run_spec_digest != spec.digest
            ):
                raise HTTPException(
                    status_code=422,
                    detail="retry admission does not admit the original RunSpec",
                )
            new_run_id, job = service.runtime.coordinator.enqueue(
                run_spec_id=source.run_spec_id,
                admission_id=payload.admission_id,
                idempotency_key=idempotency_key,
                retry_of=run_id,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Run or admission not found") from exc
        except HTTPException:
            raise
        except ValueError as exc:
            if any(
                marker in str(exc)
                for marker in (
                    "idempotency key",
                    "can be retried",
                    "retry requires",
                    "retry AdmissionRecord",
                )
            ):
                raise HTTPException(status_code=409, detail=str(exc)) from exc
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {
            "run_id": new_run_id,
            "job_id": job.job_id,
            "run_spec_id": source.run_spec_id,
            "admission_id": payload.admission_id,
            "retry_of": run_id,
            "status": job.status,
        }

    @app.get("/api/v1/runs/{run_id}")
    async def run_detail(
        run_id: str, _: None = Depends(authorize)
    ) -> dict[str, Any]:
        matches = [r for r in repository.read_model.latest_dashboard()["runs"] if r["id"] == run_id]
        if not matches:
            raise HTTPException(status_code=404, detail="run not found")
        record = repository.read_model.get_run_record(run_id)
        execution = repository.lease.get_run_execution(run_id)
        try:
            subject_envelope_digest = repository.read_model.get_subject_envelope(run_id).digest
        except KeyError:
            subject_envelope_digest = None
        return {
            **matches[0],
            "record": semantic_model_dump(record) if record is not None else None,
            "events": repository.read_model.get_run_events(run_id),
            "execution": (
                {
                    "job": {
                        **semantic_model_dump(execution[0]),
                        "digest": execution[0].digest,
                    },
                    "attempts": [
                        {**semantic_model_dump(item), "digest": item.digest}
                        for item in execution[1]
                    ],
                }
                if execution is not None
                else None
            ),
            "subject_envelope_digest": subject_envelope_digest,
        }

    @app.get("/api/v1/runs/{run_id}/events")
    async def run_events(
        run_id: str, _: None = Depends(authorize)
    ) -> list[dict[str, Any]]:
        return repository.read_model.get_run_events(run_id)

    @app.get("/api/v1/runs/{run_id}/evaluations")
    async def run_evaluations(
        run_id: str, _: None = Depends(authorize)
    ) -> list[dict[str, Any]]:
        return [
            {**semantic_model_dump(item), "digest": item.digest}
            for item in repository.read_model.get_evaluation_records(run_id)
        ]

    @app.get("/api/v1/runs/{run_id}/checkpoints")
    async def run_checkpoints(
        run_id: str, _: None = Depends(authorize)
    ) -> list[dict[str, Any]]:
        return [
            {**semantic_model_dump(item), "checkpoint_hash": item.checkpoint_hash}
            for item in repository.read_model.get_checkpoint_records(run_id)
        ]

    @app.get("/api/v1/runs/{run_id}/stream")
    async def run_stream(
        run_id: str, request: Request, _: None = Depends(authorize)
    ) -> StreamingResponse:
        async def event_stream() -> AsyncIterator[str]:
            emitted = 0
            while not await request.is_disconnected():
                events = repository.read_model.get_run_events(run_id)
                for event in events[emitted:]:
                    serialized = json.dumps(event, ensure_ascii=False)
                    yield f"event: {event['type']}\ndata: {serialized}\n\n"
                emitted = len(events)
                run = repository.read_model.get_run(run_id)
                if run.status in {
                    "completed",
                    "failed",
                    "cancelled",
                    "budget_exhausted",
                    "guardrail_stopped",
                } and emitted:
                    return
                yield ": heartbeat\n\n"
                await asyncio.sleep(1)

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    @app.get("/api/v1/comparisons")
    async def comparisons(_: None = Depends(authorize)) -> list[dict[str, Any]]:
        return repository.read_model.latest_dashboard()["comparisons"]

    @app.get("/api/v1/comparisons/{comparison_id}")
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

    @app.post("/api/v1/chat/sessions")
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

    @app.get("/api/v1/chat/sessions")
    async def chat_sessions(_: None = Depends(authorize)) -> list[dict[str, Any]]:
        return repository.read_model.latest_dashboard()["chats"]

    @app.post("/api/v1/chat/sessions/{session_id}/messages")
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

    @app.post("/api/v1/evidence-bundles/{comparison_id}")
    async def export_bundle(
        comparison_id: str, _: None = Depends(authorize)
    ) -> dict[str, Any]:
        target = settings.data_dir / "exports" / f"{comparison_id}.evidrun.zip"
        await asyncio.to_thread(bundles.export_comparison_v2, comparison_id, target)
        return {"path": str(target), "comparison_id": comparison_id}

    @app.post("/api/v1/runs/{run_id}/evidence-bundles")
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

    return app


def run() -> None:
    port = int(os.environ.get("EVIDRUN_PORT", "8765"))
    uvicorn.run(create_app(), host="127.0.0.1", port=port)
