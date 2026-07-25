"""Per-family factual checks for `append_event`.

Each function answers one question: given the Run, its prior events and the
normalized payload, may this event type be appended right now? They only raise —
the caller owns the session, the hash chain and the status advance, so an event
that fails here leaves nothing written.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from evidrun.infrastructure.database.models import (
    EvaluationRecordRow,
    RunEventRow,
)

__all__ = [
    "check_evaluation_completed",
]


def check_evaluation_completed(
    session: Any,
    run_id: str,
    normalized_payload: Mapping[str, Any],
    prior_events: Sequence[RunEventRow],
) -> None:
    evaluation_id = str(normalized_payload["evaluation_record_id"])
    evaluation = session.get(EvaluationRecordRow, evaluation_id)
    if (
        evaluation is None
        or evaluation.run_id != run_id
        or evaluation.record_digest != normalized_payload["evaluation_record_digest"]
        or json.loads(evaluation.record_json).get("gate_status")
        != normalized_payload["gate_status"]
    ):
        raise ValueError(
            "evaluation.completed requires the exact persisted EvaluationRecord"
        )
    if any(
        item.event_type == "evaluation.completed"
        and json.loads(item.payload_json).get("evaluation_record_id") == evaluation_id
        for item in prior_events
    ):
        raise ValueError("EvaluationRecord already has a completion event")
