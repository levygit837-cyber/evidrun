"""The declared vocabulary a change contract is written in.

Kept apart from `model` so a policy module can read a classification or an impact level
without importing the contract loader that assembles them. `model` composes these into a
`ChangeContract`; `merge_gate` derives review depth from them. Neither imports the other.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

__all__ = [
    "REFACTOR_PRESERVES",
    "ChangeClassification",
    "ContractError",
    "ImpactDeclaration",
    "ImpactLevel",
    "QuestionStatus",
]


class ContractError(ValueError):
    """The contract cannot be evaluated safely."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = tuple(errors)
        super().__init__("; ".join(errors))


class ChangeClassification(StrEnum):
    REFACTOR = "refactor"
    BEHAVIOR_COMPATIBLE = "behavior-compatible"
    FEATURE = "feature"
    BREAKING = "breaking"
    DOCS_ONLY = "docs-only"
    GENERATED = "generated"


class ImpactLevel(StrEnum):
    NONE = "none"
    ADDITIVE = "additive"
    CHANGED = "changed"
    REMOVED = "removed"
    BREAKING = "breaking"


class QuestionStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"


REFACTOR_PRESERVES = {"capability", "persisted-contract", "fail-closed"}


@dataclass(frozen=True)
class ImpactDeclaration:
    capability: ImpactLevel
    persisted_contract: ImpactLevel
    normative: ImpactLevel
    notes: tuple[str, ...]
