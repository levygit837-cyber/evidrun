"""Contract validation, revision registration, compilation, and admission."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import yaml
from fastapi import APIRouter, Depends, HTTPException

from evidrun.contracts import StudyRevision, parse_revision, semantic_model_dump
from evidrun.contracts.compiler import StudyCompiler
from evidrun.contracts.triage import HTTP_STATUS_BY_CODE
from evidrun.entrypoints.api.context import ApiContext
from evidrun.entrypoints.api.schemas import (
    ContractDecisionRequest,
    ContractDocumentRequest,
    ContractRegistrationRequest,
    ManifestRequest,
)
from evidrun.experiments import ExperimentManifest
from evidrun.infrastructure.database.register_errors import (
    RegisterRejected,
    RegisterStorageUnavailable,
)


def create_contract_router(
    *, context: ApiContext, authorize: Callable[..., Any]
) -> APIRouter:
    router = APIRouter(prefix="/api/v1")
    repository = context.repository

    @router.post("/experiments/validate")
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

    @router.post("/contracts/validate")
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

    @router.post("/contracts/revisions")
    async def register_contract(
        payload: ContractRegistrationRequest, _: None = Depends(authorize)
    ) -> dict[str, Any]:
        try:
            revision = parse_revision(payload.document)
            row = repository.registry.save_contract_revision(revision, status=payload.status)
        except RegisterRejected as exc:
            raise HTTPException(
                status_code=HTTP_STATUS_BY_CODE[exc.error.code],
                detail=exc.error.model_dump(mode="json"),
            ) from exc
        except RegisterStorageUnavailable as exc:
            raise HTTPException(
                status_code=HTTP_STATUS_BY_CODE[exc.error.code],
                detail=exc.error.model_dump(mode="json"),
            ) from exc
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

    @router.get("/contracts/revisions")
    async def contract_revisions(_: None = Depends(authorize)) -> list[dict[str, Any]]:
        return repository.read_model.list_contract_revisions()

    @router.post("/contracts/revisions/{revision_id}/decisions")
    async def decide_contract(
        revision_id: str,
        payload: ContractDecisionRequest,
        _: None = Depends(authorize),
    ) -> dict[str, Any]:
        # Always 503: the real path is POST /api/v1/authority/revisions/decisions.
        # The lookup runs first so an unknown revision still answers 404, which is
        # the observable behaviour this route has always had. A docstring here
        # would leak into the generated OpenAPI description.
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

    @router.post("/studies/{revision_id}/compile")
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

    return router


def create_admission_router(
    *, context: ApiContext, authorize: Callable[..., Any]
) -> APIRouter:
    router = APIRouter(prefix="/api/v1")
    repository = context.repository
    service = context.service

    @router.post("/run-specs/{run_spec_id}/admit")
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

    @router.get("/run-specs/{run_spec_id}")
    async def run_spec(run_spec_id: str, _: None = Depends(authorize)) -> dict[str, Any]:
        try:
            spec = repository.read_model.get_run_spec(run_spec_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="RunSpec not found") from exc
        return {**semantic_model_dump(spec), "digest": spec.digest}

    @router.get("/admissions/{admission_id}")
    async def admission(admission_id: str, _: None = Depends(authorize)) -> dict[str, Any]:
        try:
            record = repository.read_model.get_admission_record(admission_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="AdmissionRecord not found") from exc
        return {**semantic_model_dump(record), "digest": record.digest}

    return router
