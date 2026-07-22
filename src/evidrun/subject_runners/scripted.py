from __future__ import annotations

import re

from evidrun.shared.ports import SubjectResult


class ScriptedLogInvestigator:
    """Deterministic runner used to verify Evidrun infrastructure, not LLM ability."""

    name = "scripted-log-investigator-v1"
    _marker = re.compile(r"ROOT_CAUSE=([A-Z0-9_]+)")

    async def execute(self, objective: str, context: str) -> SubjectResult:
        match = self._marker.search(context)
        if match is None:
            return SubjectResult(
                output="Não foi possível identificar a causa-raiz com o contexto disponível.",
                evidence=(),
                metadata={"objective": objective, "marker_visible": False},
            )
        cause = match.group(1)
        evidence = tuple(
            line.strip() for line in context.splitlines() if f"ROOT_CAUSE={cause}" in line
        )
        return SubjectResult(
            output=f"A causa-raiz é {cause}.",
            evidence=evidence,
            metadata={"objective": objective, "marker_visible": True},
        )

