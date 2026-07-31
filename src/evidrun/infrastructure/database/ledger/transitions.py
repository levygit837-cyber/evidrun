"""The Run lifecycle state machine.

This is the single point that decides whether an event may advance the Run and to
which status. Keeping the rule here rather than inside a SQL write is what lets
the ledger stay the one authority over phase validity.
"""

from __future__ import annotations

from collections.abc import Mapping

from evidrun.infrastructure.database.models import RunRow

__all__ = [
    "RETRYABLE_RUN_STATUSES",
    "TERMINAL_EVENT_TYPES",
    "TERMINAL_RUN_STATUSES",
    "event_transition",
]

#: The Run statuses past which no further event may be appended.
TERMINAL_RUN_STATUSES = frozenset(
    {
        "completed",
        "failed",
        "cancelled",
        "budget_exhausted",
        "guardrail_stopped",
    }
)
#: The terminal statuses a retry may start from: every terminal status except success.
#: Derived rather than relisted so a new terminal status cannot silently become retryable.
RETRYABLE_RUN_STATUSES = TERMINAL_RUN_STATUSES - {"completed"}
#: The lifecycle events that drive a Run into one of those statuses.
TERMINAL_EVENT_TYPES = frozenset(f"run.{status}" for status in TERMINAL_RUN_STATUSES)


def event_transition(
    *,
    run: RunRow,
    event_type: str,
    payload: Mapping[str, object],
    has_prior_event: bool,
) -> str | None:
    if run.status in TERMINAL_RUN_STATUSES:
        raise ValueError("no Run events may be appended after a terminal lifecycle event")
    transition: dict[str, tuple[frozenset[str], str]] = {
        "run.preparing": (frozenset({"queued"}), "preparing"),
        "run.running": (frozenset({"preparing"}), "running"),
        "run.paused": (frozenset({"running"}), "paused"),
        "run.resumed": (frozenset({"paused"}), "running"),
        "run.evaluating": (frozenset({"running"}), "evaluating"),
        "run.completed": (frozenset({"evaluating"}), "completed"),
        "run.failed": (
            frozenset({"queued", "preparing", "running", "paused", "evaluating"}),
            "failed",
        ),
        "run.cancelled": (
            frozenset({"queued", "preparing", "running", "paused", "evaluating"}),
            "cancelled",
        ),
        "run.budget_exhausted": (
            frozenset({"queued", "preparing", "running", "paused", "evaluating"}),
            "budget_exhausted",
        ),
        "run.guardrail_stopped": (
            frozenset({"queued", "preparing", "running", "paused", "evaluating"}),
            "guardrail_stopped",
        ),
    }
    if not has_prior_event and event_type != "run.queued":
        raise ValueError("run.queued must be the first Run event")
    if event_type == "run.queued":
        if has_prior_event or run.status != "queued":
            raise ValueError("run.queued must be the first lifecycle event")
        if payload.get("run_id") != run.id or payload.get("variant_id") != run.variant_id:
            raise ValueError("run.queued identity does not match the RunRecord")
        return None
    rule = transition.get(event_type)
    if rule is None:
        return None
    allowed_from, target = rule
    if run.status not in allowed_from:
        raise ValueError(f"invalid Run lifecycle transition: {run.status} -> {target}")
    declared_from = payload.get("from_status")
    if declared_from is not None and declared_from != run.status:
        raise ValueError("Run lifecycle payload has an incorrect from_status")
    declared_terminal = payload.get("status")
    if declared_terminal is not None and declared_terminal != target:
        raise ValueError("terminal event type and payload status do not match")
    return target
