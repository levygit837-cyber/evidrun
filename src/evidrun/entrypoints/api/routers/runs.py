"""Run lifecycle: enqueue, retry, inspect, and the live event stream.

`enqueue_run` and `retry_run` translate a named `TriageRejected` by its stable code:
the status comes from `HTTP_STATUS_BY_CODE`, never from inspecting message text.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Callable
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from evidrun.contracts import semantic_model_dump
from evidrun.contracts.triage import HTTP_STATUS_BY_CODE, TriageRejected
from evidrun.entrypoints.api.context import ApiContext
from evidrun.entrypoints.api.schemas import RunEnqueueRequest
from evidrun.infrastructure.database.ledger.transitions import (
    RETRYABLE_RUN_STATUSES,
    TERMINAL_RUN_STATUSES,
)
from evidrun.infrastructure.database.queue.enqueue_errors import (
    enqueue_admission_not_admitted,
    enqueue_admission_run_spec_mismatch,
    enqueue_retry_legacy_run,
    enqueue_retry_source_succeeded,
)


def _triage_http_error(rejection: TriageRejected) -> HTTPException:
    """One translation for every named enqueue refusal reaching HTTP."""

    return HTTPException(
        status_code=HTTP_STATUS_BY_CODE[rejection.error.code],
        detail=rejection.error.model_dump(mode="json"),
    )



def create_run_router(
    *, context: ApiContext, authorize: Callable[..., Any]
) -> APIRouter:
    router = APIRouter(prefix="/api/v1")
    repository = context.repository
    service = context.service
    benchmarks = context.benchmarks

    @router.post("/demo/bootstrap")
    async def bootstrap_demo(_: None = Depends(authorize)) -> dict[str, Any]:
        return await asyncio.to_thread(service.bootstrap_demo, benchmarks)

    @router.get("/runs")
    async def runs(_: None = Depends(authorize)) -> list[dict[str, Any]]:
        return repository.read_model.latest_dashboard()["runs"]

    @router.post("/run-specs/{run_spec_id}/runs", status_code=status.HTTP_202_ACCEPTED)
    async def enqueue_run(
        run_spec_id: str,
        payload: RunEnqueueRequest,
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
        _: None = Depends(authorize),
    ) -> dict[str, Any]:
        try:
            run_id, job = service.runtime.coordinator.enqueue(
                run_spec_id=run_spec_id,
                admission_id=payload.admission_id,
                idempotency_key=idempotency_key,
            )
        except TriageRejected as exc:
            raise _triage_http_error(exc) from exc
        return {
            "run_id": run_id,
            "job_id": job.job_id,
            "run_spec_id": run_spec_id,
            "admission_id": payload.admission_id,
            "retry_of": None,
            "status": job.status,
        }

    @router.post("/runs/{run_id}/retries", status_code=status.HTTP_202_ACCEPTED)
    async def retry_run(
        run_id: str,
        payload: RunEnqueueRequest,
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
        _: None = Depends(authorize),
    ) -> dict[str, Any]:
        try:
            source = repository.read_model.get_run(run_id)
            run_spec_id = _retryable_run_spec_id(source)
            spec = repository.read_model.get_run_spec(run_spec_id)
            retry_admission = repository.read_model.get_admission_record(payload.admission_id)
            if retry_admission.decision != "admitted":
                raise enqueue_admission_not_admitted()
            if retry_admission.run_spec_digest != spec.digest:
                raise enqueue_admission_run_spec_mismatch()
            new_run_id, job = service.runtime.coordinator.enqueue(
                run_spec_id=run_spec_id,
                admission_id=payload.admission_id,
                idempotency_key=idempotency_key,
                retry_of=run_id,
            )
        except TriageRejected as exc:
            raise _triage_http_error(exc) from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Run or admission not found") from exc
        return {
            "run_id": new_run_id,
            "job_id": job.job_id,
            "run_spec_id": run_spec_id,
            "admission_id": payload.admission_id,
            "retry_of": run_id,
            "status": job.status,
        }

    return router


def create_run_read_router(
    *, context: ApiContext, authorize: Callable[..., Any]
) -> APIRouter:
    """Projections of one Run: detail, ledger, evaluations, checkpoints, stream."""

    router = APIRouter(prefix="/api/v1")
    repository = context.repository

    @router.get("/runs/{run_id}")
    async def run_detail(run_id: str, _: None = Depends(authorize)) -> dict[str, Any]:
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
            "execution": _execution_view(execution),
            "subject_envelope_digest": subject_envelope_digest,
        }

    @router.get("/runs/{run_id}/events")
    async def run_events(run_id: str, _: None = Depends(authorize)) -> list[dict[str, Any]]:
        return repository.read_model.get_run_events(run_id)

    @router.get("/runs/{run_id}/evaluations")
    async def run_evaluations(
        run_id: str, _: None = Depends(authorize)
    ) -> list[dict[str, Any]]:
        return [
            {**semantic_model_dump(item), "digest": item.digest}
            for item in repository.read_model.get_evaluation_records(run_id)
        ]

    @router.get("/runs/{run_id}/checkpoints")
    async def run_checkpoints(
        run_id: str, _: None = Depends(authorize)
    ) -> list[dict[str, Any]]:
        return [
            {**semantic_model_dump(item), "checkpoint_hash": item.checkpoint_hash}
            for item in repository.read_model.get_checkpoint_records(run_id)
        ]

    @router.get("/runs/{run_id}/stream")
    async def run_stream(
        run_id: str, request: Request, _: None = Depends(authorize)
    ) -> StreamingResponse:
        # Replays the ledger prefix, then follows it until the Run is terminal.
        # A docstring here would leak into the generated OpenAPI description.
        async def event_stream() -> AsyncIterator[str]:
            emitted = 0
            while not await request.is_disconnected():
                events = repository.read_model.get_run_events(run_id)
                for event in events[emitted:]:
                    serialized = json.dumps(event, ensure_ascii=False)
                    yield f"event: {event['type']}\ndata: {serialized}\n\n"
                emitted = len(events)
                run = repository.read_model.get_run(run_id)
                if run.status in TERMINAL_RUN_STATUSES and emitted:
                    return
                yield ": heartbeat\n\n"
                await asyncio.sleep(1)

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    return router


def _retryable_run_spec_id(source: Any) -> str:
    """Return the RunSpec id only when this Run is eligible for a Runtime Kernel retry.

    Returning the id instead of asserting keeps the caller's type narrowed: a Run
    without a RunSpec is legacy and never reaches the coordinator.
    """

    run_spec_id: str | None = source.run_spec_id
    if run_spec_id is None:
        raise enqueue_retry_legacy_run()
    if source.status not in RETRYABLE_RUN_STATUSES:
        raise enqueue_retry_source_succeeded()
    return run_spec_id


def _execution_view(execution: Any) -> dict[str, Any] | None:
    if execution is None:
        return None
    job, attempts = execution
    return {
        "job": {**semantic_model_dump(job), "digest": job.digest},
        "attempts": [
            {**semantic_model_dump(item), "digest": item.digest} for item in attempts
        ],
    }
