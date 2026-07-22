from __future__ import annotations

from typing import Any

from evidrun.experiments.models import ContextPolicySpec
from evidrun.shared.types import sha256_json


class ContextComposer:
    def compose(self, source: str, policy: ContextPolicySpec) -> dict[str, Any]:
        source_chars = len(source)
        if policy.strategy == "full" or source_chars <= policy.max_chars:
            selected = source
            omitted: list[dict[str, int]] = []
        elif policy.strategy == "head":
            selected = source[: policy.max_chars]
            omitted = [{"start": policy.max_chars, "end": source_chars}]
        else:
            start = max(0, source_chars - policy.max_chars)
            selected = source[start:]
            omitted = [{"start": 0, "end": start}]

        plan = {
            "policy_id": policy.id,
            "strategy": policy.strategy,
            "max_chars": policy.max_chars,
            "source_chars": source_chars,
            "selected_chars": len(selected),
            "selected_content": selected,
            "omitted": omitted,
        }
        plan["content_hash"] = sha256_json(
            {
                "policy_id": policy.id,
                "selected_content": selected,
                "omitted": omitted,
            }
        )
        return plan

    def diff(self, baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
        baseline_text = str(baseline["selected_content"])
        candidate_text = str(candidate["selected_content"])
        return {
            "strategy": {
                "before": baseline["strategy"],
                "after": candidate["strategy"],
            },
            "selected_chars": {
                "before": baseline["selected_chars"],
                "after": candidate["selected_chars"],
            },
            "added_root_cause": (
                "ROOT_CAUSE=" not in baseline_text and "ROOT_CAUSE=" in candidate_text
            ),
            "baseline_omitted": baseline["omitted"],
            "candidate_omitted": candidate["omitted"],
        }

