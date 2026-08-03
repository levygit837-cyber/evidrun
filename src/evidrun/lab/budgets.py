"""Contadores e relógio monotônico dos budgets de um turno."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol


class TurnLimits(Protocol):
    max_tool_calls_per_turn: int
    max_provider_round_trips_per_turn: int
    max_wall_seconds_per_turn: int
    max_refusals_per_turn: int
    max_output_tokens_per_round_trip: int


@dataclass(slots=True)
class TurnBudgetGuard:
    limits: TurnLimits
    clock: Callable[[], float] = time.monotonic
    started_at: float = field(init=False)

    def __post_init__(self) -> None:
        self.started_at = self.clock()

    def wall_exhausted(self) -> bool:
        return self.clock() - self.started_at >= self.limits.max_wall_seconds_per_turn

    def round_trip_denied(self, completed: int) -> bool:
        return completed >= self.limits.max_provider_round_trips_per_turn

    def tool_call_denied(self, attempted: int) -> bool:
        return attempted > self.limits.max_tool_calls_per_turn

    def refusal_exhausted(self, recorded: int) -> bool:
        return recorded >= self.limits.max_refusals_per_turn
