"""Deterministic machine-readable and printable ReviewPackage projections."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse

from evidrun.contracts import semantic_model_dump
from evidrun.entrypoints.api.context import ApiContext
from evidrun.entrypoints.review_html import render_review_package_html


def create_review_router(
    *, context: ApiContext, authorize: Callable[..., Any]
) -> APIRouter:
    router = APIRouter(prefix="/api/v1")
    service = context.service.review_packages

    def build(review_target_digest: str, compare_to: str | None):
        try:
            return service.build(
                review_target_digest,
                compare_to_digest=compare_to,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="ReviewTarget not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.get("/review-targets/{review_target_digest}/package")
    async def review_package(
        review_target_digest: str,
        compare_to: str | None = Query(default=None),
        _: None = Depends(authorize),
    ) -> dict[str, Any]:
        return semantic_model_dump(build(review_target_digest, compare_to))

    @router.get(
        "/review-targets/{review_target_digest}/package.html",
        response_class=HTMLResponse,
    )
    async def review_package_html(
        review_target_digest: str,
        compare_to: str | None = Query(default=None),
        _: None = Depends(authorize),
    ) -> HTMLResponse:
        return HTMLResponse(
            render_review_package_html(build(review_target_digest, compare_to))
        )

    return router
