from __future__ import annotations

from collections.abc import Sequence
from typing import Any


class ExactCauseGrader:
    def __init__(self, grader_id: str, expected: str):
        self.name = grader_id
        self.expected = expected

    def grade(self, output: str, evidence: Sequence[str]) -> dict[str, Any]:
        answer_match = self.expected in output
        evidence_match = any(self.expected in item for item in evidence)
        passed = answer_match and evidence_match
        return {
            "grader_id": self.name,
            "score": 1.0 if passed else 0.0,
            "passed": passed,
            "rationale": (
                "Resposta e evidência contêm a causa-raiz esperada."
                if passed
                else "A causa-raiz esperada não está simultaneamente na resposta e na evidência."
            ),
            "evidence": list(evidence),
        }

