from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Mapping

import httpx

from evidrun.infrastructure.providers import ProviderCredentialStore
from evidrun.providers import ProviderProfile
from evidrun.runs.adapters import ReadArtifactTextToolAdapter


async def probe(
    *,
    include_tools: bool = True,
    strict: bool = True,
    required: bool = True,
) -> dict[str, object]:
    """Probe the exact transport shape without printing credentials or free-form output."""

    profile = ProviderProfile.load_default()
    credential = ProviderCredentialStore().require(profile)
    payload: dict[str, object] = {
        "model": profile.model,
        "input": (
            "Call read_text once for input_id probe with start_line 1 and max_lines 1."
            if include_tools
            else "Reply with the single word READY."
        ),
        "instructions": (
            "Use the offered tool. Do not provide a final answer."
            if include_tools
            else "Return only READY."
        ),
        "reasoning": {"effort": profile.reasoning_effort},
        "max_output_tokens": 128,
    }
    if include_tools:
        tool_schema = dict(ReadArtifactTextToolAdapter().provider_schema)
        if not strict:
            tool_schema.pop("strict", None)
        payload["tools"] = [tool_schema]
        payload["tool_choice"] = "required" if required else "auto"
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{profile.base_url}/responses",
            headers={
                "Authorization": f"Bearer {credential}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
    try:
        document = response.json()
    except ValueError:
        return {"status": response.status_code, "shape": "non_json"}
    if response.status_code >= 400:
        error = document.get("error") if isinstance(document, Mapping) else None
        if not isinstance(error, Mapping):
            return {"status": response.status_code, "shape": "error_without_object"}
        message = error.get("message")
        return {
            "status": response.status_code,
            "error_type": error.get("type"),
            "error_code": error.get("code"),
            "parameter": error.get("param"),
            "message": str(message)[:300] if message is not None else None,
        }
    output = document.get("output") if isinstance(document, Mapping) else None
    if not isinstance(output, list):
        output = []
    output_types = [
        item.get("type")
        for item in output
        if isinstance(item, Mapping)
    ]
    return {
        "status": response.status_code,
        "response_id_present": bool(document.get("id")),
        "output_types": output_types,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plain", action="store_true")
    parser.add_argument("--no-strict", action="store_true")
    parser.add_argument("--auto-tool-choice", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            asyncio.run(
                probe(
                    include_tools=not args.plain,
                    strict=not args.no_strict,
                    required=not args.auto_tool_choice,
                )
            ),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
