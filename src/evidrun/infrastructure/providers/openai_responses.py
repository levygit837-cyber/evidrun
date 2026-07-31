from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from typing import Any, cast

import httpx
from pydantic import BaseModel, ConfigDict, TypeAdapter

from evidrun.infrastructure.providers.credentials import ProviderCredentialStore
from evidrun.providers import ProviderProfile
from evidrun.security import emit_secure_log

logger = logging.getLogger(__name__)


class ProviderRequestError(RuntimeError):
    def __init__(self, message: str, *, code: str = "provider_request_failed") -> None:
        super().__init__(message)
        self.code = code


class _ModelItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str


class _ModelCatalog(BaseModel):
    model_config = ConfigDict(extra="ignore")
    data: list[_ModelItem]


class _OutputContent(BaseModel):
    model_config = ConfigDict(extra="ignore")
    type: str
    text: str | None = None


class _OutputItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    type: str | None = None
    id: str | None = None
    call_id: str | None = None
    name: str | None = None
    arguments: str | None = None
    status: str | None = None
    content: list[_OutputContent] | None = None


class _ResponseEnvelope(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str | None = None
    status: str | None = None
    output_text: str | None = None
    output: list[_OutputItem] | None = None


_json_object = TypeAdapter(dict[str, object])


class OpenAIResponsesProvider:
    def __init__(
        self,
        profile: ProviderProfile,
        credentials: ProviderCredentialStore,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.profile = profile
        self.credentials = credentials
        self.client = client

    async def invoke(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        provider_input = request.get("input")
        if not isinstance(provider_input, (str, list)):
            raise ValueError("Provider request requires string or list input")
        payload: dict[str, Any] = {
            "model": self.profile.model,
            "input": provider_input,
            "reasoning": {"effort": self.profile.reasoning_effort},
        }
        for name in (
            "instructions",
            "max_output_tokens",
            "tools",
            "tool_choice",
            "previous_response_id",
        ):
            if name in request:
                payload[name] = request[name]
        return await self._request("POST", "/responses", json=payload)

    async def list_models(self) -> tuple[str, ...]:
        response = await self._request("GET", "/models")
        try:
            catalog = _ModelCatalog.model_validate(response)
        except ValueError:
            raise ProviderRequestError(
                "Provider model catalog has an invalid shape",
                code="invalid_model_catalog",
            ) from None
        return tuple(item.id for item in catalog.data)

    async def check(self) -> dict[str, object]:
        models = await self.list_models()
        return {
            **self.profile.public_dict(),
            "reachable": True,
            "credential_available": True,
            "model_available": self.profile.model in models,
            "catalog_size": len(models),
        }

    async def _request(
        self, method: str, path: str, *, json: Mapping[str, Any] | None = None
    ) -> Mapping[str, Any]:
        api_key = self.credentials.require(self.profile)
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        owns_client = self.client is None
        client = self.client or httpx.AsyncClient(timeout=60.0)
        try:
            response = await client.request(
                method, f"{self.profile.base_url}{path}", headers=headers, json=json
            )
            if response.status_code >= 400:
                provider_code: str | None = None
                try:
                    error_payload = _json_object.validate_python(response.json())
                    error_value = error_payload.get("error")
                except ValueError:
                    error_value = None
                if isinstance(error_value, Mapping):
                    error_document = cast(Mapping[str, object], error_value)
                    candidate = error_document.get("code") or error_document.get("type")
                    if isinstance(candidate, str) and re.fullmatch(
                        r"[A-Za-z0-9_.-]{1,64}", candidate
                    ):
                        provider_code = candidate
                    parameter = error_document.get("param")
                    if isinstance(parameter, str) and re.fullmatch(
                        r"[A-Za-z0-9_.-]{1,64}", parameter
                    ):
                        provider_code = (
                            f"{provider_code}_{parameter}"
                            if provider_code is not None
                            else parameter
                        )
                error = ProviderRequestError(
                    f"{self.profile.id} returned HTTP {response.status_code}",
                    code=(
                        f"http_{response.status_code}_{provider_code}"
                        if provider_code is not None
                        else f"http_{response.status_code}"
                    ),
                )
                emit_secure_log(
                    logger,
                    logging.ERROR,
                    "provider.http_error",
                    error_code=error.code,
                    error=error,
                    fields={
                        "provider_id": self.profile.id,
                        "status_code": response.status_code,
                    },
                )
                raise error
            try:
                payload = _json_object.validate_python(response.json())
            except ValueError:
                error = ProviderRequestError(
                    "Provider returned a non-object JSON response",
                    code="invalid_response_shape",
                )
                emit_secure_log(
                    logger,
                    logging.ERROR,
                    "provider.invalid_response",
                    error_code=error.code,
                    error=error,
                    fields={"provider_id": self.profile.id},
                )
                raise error from None
            return payload
        except httpx.HTTPError as exc:
            error = ProviderRequestError(
                f"Could not reach {self.profile.id}",
                code="transport_error",
            )
            emit_secure_log(
                logger,
                logging.ERROR,
                "provider.transport_error",
                error_code=error.code,
                error=exc,
                fields={"provider_id": self.profile.id},
            )
            raise error from exc
        finally:
            if owns_client:
                await client.aclose()


def extract_output_text(response: Mapping[str, Any]) -> str:
    envelope = _ResponseEnvelope.model_validate(response)
    if envelope.output_text:
        return envelope.output_text
    return "".join(
        content.text
        for item in envelope.output or ()
        for content in item.content or ()
        if content.type in {"output_text", "text"} and content.text
    )


class ProviderFunctionCall(BaseModel):
    """Normalized function call emitted by an OpenAI Responses-compatible provider."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    item_id: str | None = None
    call_id: str
    name: str
    arguments: str


def extract_function_calls(
    response: Mapping[str, Any],
) -> tuple[ProviderFunctionCall, ...]:
    envelope = _ResponseEnvelope.model_validate(response)
    calls: list[ProviderFunctionCall] = []
    for item in envelope.output or ():
        if item.type != "function_call":
            continue
        if not item.call_id or not item.name or item.arguments is None:
            raise ProviderRequestError(
                "Provider returned an invalid function call",
                code="invalid_function_call",
            )
        calls.append(
            ProviderFunctionCall(
                item_id=item.id,
                call_id=item.call_id,
                name=item.name,
                arguments=item.arguments,
            )
        )
    return tuple(calls)


def extract_response_id(response: Mapping[str, Any]) -> str:
    envelope = _ResponseEnvelope.model_validate(response)
    if not envelope.id:
        raise ProviderRequestError(
            "Provider response is missing its response id",
            code="missing_response_id",
        )
    return envelope.id


def extract_usage(response: Mapping[str, Any]) -> dict[str, int]:
    usage_value: object = response.get("usage")
    if not isinstance(usage_value, Mapping):
        return {}
    usage = cast(Mapping[str, object], usage_value)
    normalized: dict[str, int] = {}
    for key in ("input_tokens", "output_tokens", "total_tokens"):
        value = usage.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            normalized[key] = value
    return normalized
