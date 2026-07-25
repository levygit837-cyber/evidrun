"""The single wall-clock reading of an attempt.

This module is the clock seam for the coordinator: it is the only place that asks
what time it is while a Run executes, so freezing time in a test reaches every
budget decision by patching one module.

The elapsed window starts at the persisted `run.running` event, not at process
start, so a Run that crashed and resumed keeps spending the same budget.
"""

from __future__ import annotations

from datetime import UTC, datetime

from evidrun.contracts import RunSpec
from evidrun.infrastructure.database import Repository
from evidrun.shared.types import utc_now


def remaining_wall_seconds(
    repository: Repository, run_id: str, spec: RunSpec
) -> float:
    """Seconds left in `max_wall_seconds`, never negative."""

    events = repository.read_model.get_run_events(run_id)
    running = next(item for item in events if item["type"] == "run.running")
    started = datetime.fromisoformat(str(running["occurred_at_utc"]))
    if started.tzinfo is None:
        started = started.replace(tzinfo=UTC)
    elapsed = (utc_now() - started).total_seconds()
    return max(0.0, spec.budgets.max_wall_seconds - elapsed)
