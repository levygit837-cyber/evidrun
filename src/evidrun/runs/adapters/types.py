"""Values and ports the adapters exchange, with no adapter behaviour of their own."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from evidrun.contracts import (
    CapabilityDescriptorRef,
    EvaluationRecord,
    GoalStateTerminalResult,
)
from evidrun.shared.types import Classification


@dataclass(frozen=True)
class EvaluationOutcome:
    record: EvaluationRecord
    score: float
    passed: bool
    rationale: str
    evidence: tuple[str, ...]
    goal_result: GoalStateTerminalResult


class SubjectBudgetExceeded(RuntimeError):
    """A declared scientific budget was exhausted by the Subject adapter."""


class ToolTraceSink(Protocol):
    """Where a fenced tool call is recorded; the Run ledger is the real sink."""

    def called(
        self,
        *,
        capability_ref: CapabilityDescriptorRef,
        call_id: str,
        arguments: str,
    ) -> None: ...

    def completed(
        self,
        *,
        capability_ref: CapabilityDescriptorRef,
        call_id: str,
        result: str,
        classification: Classification,
    ) -> None: ...

    def denied(self, *, call_id: str, reason: str) -> None: ...

    def failed(
        self,
        *,
        capability_ref: CapabilityDescriptorRef,
        call_id: str,
        reason: str,
    ) -> None: ...


@dataclass(frozen=True)
class ReadToolResult:
    output: str
    evidence: str
    classification: Classification
