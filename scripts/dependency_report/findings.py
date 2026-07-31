"""The single record every analysis emits."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .vocabulary import KIND_BY_CODE, DependencyState, FindingCode, FindingKind


@dataclass(frozen=True, order=True)
class Finding:
    """One structural observation, ordered so the report is stable.

    `subjects` names the nodes involved and is the ordering key after the code, which
    is what keeps a new finding from reformatting unrelated lines of the baseline.
    """

    code: FindingCode
    subjects: tuple[str, ...]
    detail: str = field(compare=False)
    state: DependencyState = field(default=DependencyState.SUSPICIOUS, compare=False)
    metrics: tuple[tuple[str, int], ...] = field(default=(), compare=False)

    @property
    def kind(self) -> FindingKind:
        return KIND_BY_CODE[self.code]

    def as_dict(self) -> dict[str, Any]:
        document: dict[str, Any] = {
            "code": self.code.value,
            "kind": self.kind.value,
            "state": self.state.value,
            "subjects": list(self.subjects),
            "detail": self.detail,
        }
        if self.metrics:
            document["metrics"] = dict(self.metrics)
        return document
