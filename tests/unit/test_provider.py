from __future__ import annotations

import json

import httpx
import pytest

from evidrun.infrastructure.providers import (
    OpenAIResponsesProvider,
    ProviderCredentialStore,
    extract_output_text,
)
from evidrun.providers import ProviderProfile


def test_default_provider_is_cliproxy_deepseek_max(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "EVIDRUN_PROVIDER_BASE_URL",
        "EVIDRUN_PROVIDER_MODEL",
        "EVIDRUN_PROVIDER_REASONING_EFFORT",
    ):
        monkeypatch.delenv(name, raising=False)
    profile = ProviderProfile.load_default()
    assert profile.id == "cliproxyapi-local"
    assert profile.base_url == "http://127.0.0.1:8318/v1"
    assert profile.model == "deepseek-v4-flash"
    assert profile.reasoning_effort == "max"


@pytest.mark.asyncio
async def test_responses_adapter_locks_model_and_reasoning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EVIDRUN_PROVIDER_API_KEY", "test-secret")

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "http://127.0.0.1:8318/v1/responses"
        assert request.headers["Authorization"] == "Bearer test-secret"
        payload = json.loads(request.content)
        assert payload["model"] == "deepseek-v4-flash"
        assert payload["reasoning"] == {"effort": "max"}
        assert payload["input"] == "hello"
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "world"}],
                    }
                ],
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = OpenAIResponsesProvider(
            ProviderProfile.load_default(), ProviderCredentialStore(), client=client
        )
        response = await provider.invoke({"input": "hello"})
    assert extract_output_text(response) == "world"


@pytest.mark.asyncio
async def test_provider_catalog_check_requires_configured_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EVIDRUN_PROVIDER_API_KEY", "test-secret")

    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [{"id": "deepseek-v4-flash"}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = OpenAIResponsesProvider(
            ProviderProfile.load_default(), ProviderCredentialStore(), client=client
        )
        status = await provider.check()
    assert status["reachable"] is True
    assert status["model_available"] is True
    assert status["catalog_size"] == 1
