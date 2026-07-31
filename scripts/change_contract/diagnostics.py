"""The diagnostic vocabulary every policy in this package reports through.

Kept apart from `checker` so a policy module can emit findings without importing the
checker that aggregates them, which would be a cycle.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

__all__ = ["Diagnostic", "Severity"]


class Severity(StrEnum):
    BLOCKER = "blocker"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class Diagnostic:
    code: str
    severity: Severity
    message: str
    paths: tuple[str, ...] = ()
    remediation: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity.value,
            "message": self.message,
            "paths": list(self.paths),
            "remediation": self.remediation,
        }
