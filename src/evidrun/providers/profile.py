from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from typing import Literal, cast

ReasoningEffort = Literal["none", "low", "medium", "high", "max"]


@dataclass(frozen=True)
class ProviderProfile:
    id: str
    display_name: str
    api: Literal["openai_responses"]
    base_url: str
    model: str
    reasoning_effort: ReasoningEffort
    local_only: bool
    credential_service: str

    @classmethod
    def load_default(cls) -> ProviderProfile:
        reasoning = os.environ.get("EVIDRUN_PROVIDER_REASONING_EFFORT", "max")
        if reasoning not in {"none", "low", "medium", "high", "max"}:
            raise ValueError("EVIDRUN_PROVIDER_REASONING_EFFORT is invalid")
        return cls(
            id="cliproxyapi-local",
            display_name="CLIProxyAPI local",
            api="openai_responses",
            base_url=os.environ.get(
                "EVIDRUN_PROVIDER_BASE_URL", "http://127.0.0.1:8318/v1"
            ).rstrip("/"),
            model=os.environ.get("EVIDRUN_PROVIDER_MODEL", "deepseek-v4-flash"),
            reasoning_effort=cast(ReasoningEffort, reasoning),
            local_only=True,
            credential_service="dev.evidrun.providers",
        )

    def public_dict(self) -> dict[str, object]:
        return asdict(self)
