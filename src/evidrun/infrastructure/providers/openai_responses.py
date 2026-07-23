from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, TypeAdapter

from evidrun.infrastructure.providers.credentials import ProviderCredentialStore
from evidrun.providers import ProviderProfile


class ProviderRequestError(RuntimeError):
    pass


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
    content: list[_OutputContent] | None = None


class _ResponseEnvelope(BaseModel):
    model_config = ConfigDict(extra="ignore")
    output_text: str | None = None
    output: list[_OutputItem] | None = None


_json_object = TypeAdapter(dict[str, Any])


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
        for name in ("instructions", "max_output_tokens", "tools", "tool_choice"):
            if name in request:
                payload[name] = request[name]
        return await self._request("POST", "/responses", json=payload)

    async def list_models(self) -> tuple[str, ...]:
        response = await self._request("GET", "/models")
        try:
            catalog = _ModelCatalog.model_validate(response)
        except ValueError:
            raise ProviderRequestError("Provider model catalog has an invalid shape") from None
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
                raise ProviderRequestError(
                    f"{self.profile.id} returned HTTP {response.status_code}"
                )
            try:
                payload = _json_object.validate_python(response.json())
            except ValueError:
                raise ProviderRequestError(
                    "Provider returned a non-object JSON response"
                ) from None
            return payload
        except httpx.HTTPError as exc:
            raise ProviderRequestError(f"Could not reach {self.profile.id}: {exc}") from exc
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
