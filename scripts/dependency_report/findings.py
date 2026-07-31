"""The single record every analysis emits."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .vocabulary import KIND_BY_CODE, FindingCode, FindingKind


@dataclass(frozen=True, order=True)
class Finding:
    """One structural observation, ordered so the report is stable.

    `subjects` names the nodes involved and is the ordering key after the code, which
    is what keeps a new finding from reformatting unrelated lines of the baseline.

    A finding carries no `DependencyState`: that vocabulary partitions *edges*, and a
    finding is an observation about a shape. Defaulting one here labelled every
    finding `suspicious`, including `dependency.new_edge` for an edge no rule forbids.
    `kind` is the honest axis, and it is derived from the code rather than passed in.
    """

    code: FindingCode
    subjects: tuple[str, ...]
    detail: str = field(compare=False)
    metrics: tuple[tuple[str, int], ...] = field(default=(), compare=False)

    @property
    def kind(self) -> FindingKind:
        return KIND_BY_CODE[self.code]

    def as_dict(self) -> dict[str, Any]:
        document: dict[str, Any] = {
            "code": self.code.value,
            "kind": self.kind.value,
            "subjects": list(self.subjects),
            "detail": self.detail,
        }
        if self.metrics:
            document["metrics"] = dict(self.metrics)
        return document
