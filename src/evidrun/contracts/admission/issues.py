"""Canonical admission issue construction and the value every checker returns.

Each checker is a pure `(spec, envelope) -> findings` function. It never sees a
shared accumulator: it reports only what it found, and `AdmissionService` folds
the results in call order.

That order is observable. `AdmissionRecord.issues`, `missing_requirements`, and
`denied_policies` are persisted tuples the ledger and the evidence bundle read
back, so the sequence the service concatenates in is part of the contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from evidrun.contracts.runtime.spec import AdmissionIssue, ResolutionReason

IssueCategory = Literal[
    "runner",
    "provider",
    "capability",
    "runtime",
    "workspace",
    "interaction",
    "policy",
    "observer",
    "authority",
]
ReasonCode = Literal["unsupported", "denied", "unavailable", "digest_mismatch"]

WorkspaceStatus = Literal["resolved", "unsupported", "denied", "unavailable"]
InteractionStatus = Literal["resolved", "unsupported"]


def issue(
    category: IssueCategory,
    subject_ref: str,
    detail: str,
    *,
    code: ReasonCode = "unsupported",
    blocking: bool = True,
) -> AdmissionIssue:
    """Build an admission issue with its canonical reason shape."""

    return AdmissionIssue(
        category=category,
        subject_ref=subject_ref,
        reason=ResolutionReason(code=code, detail=detail),
        blocking=blocking,
    )


@dataclass(frozen=True, slots=True)
class AdmissionFindings:
    """What one checker found: four ordered sequences, nothing shared."""

    missing: tuple[str, ...] = ()
    denied_policies: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    issues: tuple[AdmissionIssue, ...] = ()

    def merge(self, other: AdmissionFindings) -> AdmissionFindings:
        """Concatenate in call order; `self` always precedes `other`."""

        return AdmissionFindings(
            missing=self.missing + other.missing,
            denied_policies=self.denied_policies + other.denied_policies,
            warnings=self.warnings + other.warnings,
            issues=self.issues + other.issues,
        )

    @property
    def blocks(self) -> bool:
        """Any accumulated obstacle blocks; a warning alone never does."""

        return bool(
            self.missing
            or self.denied_policies
            or any(item.blocking for item in self.issues)
        )


EMPTY_FINDINGS = AdmissionFindings()


@dataclass(frozen=True, slots=True)
class CheckResult[T]:
    """A checker that also resolves a value returns it beside its findings."""

    value: T
    findings: AdmissionFindings = EMPTY_FINDINGS


@dataclass(slots=True)
class FindingsBuilder:
    """Checker-local scratch space; never shared across checkers.

    Each checker builds its own and freezes it on return, which keeps the check
    bodies as readable as the sequential baseline without exposing mutation.
    """

    _missing: list[str] = field(default_factory=list[str])
    _denied: list[str] = field(default_factory=list[str])
    _warnings: list[str] = field(default_factory=list[str])
    _issues: list[AdmissionIssue] = field(default_factory=list[AdmissionIssue])

    def reject(
        self,
        category: IssueCategory,
        subject_ref: str,
        detail: str,
        *,
        code: ReasonCode = "unsupported",
    ) -> None:
        self._issues.append(issue(category, subject_ref, detail, code=code))

    def require(self, requirement: str) -> None:
        self._missing.append(requirement)

    def deny(self, policy: str) -> None:
        self._denied.append(policy)

    def warn(self, message: str) -> None:
        self._warnings.append(message)

    def freeze(self) -> AdmissionFindings:
        return AdmissionFindings(
            missing=tuple(self._missing),
            denied_policies=tuple(self._denied),
            warnings=tuple(self._warnings),
            issues=tuple(self._issues),
        )
