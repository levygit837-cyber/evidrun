"""Append one ledger event inside a caller-owned session.

This is the seam that lets an aggregate publish a fact atomically with its own
write: the caller passes its live `Session`, so the event, the hash chain link
and any status advance commit together or not at all. `operation_key` makes the
append idempotent — a replayed operation returns the existing event instead of
forking the chain.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import select

from evidrun.contracts import normalize_event_payload
from evidrun.infrastructure.database import clock
from evidrun.infrastructure.database.models import RunEventRow, RunRow
from evidrun.shared.types import canonical_json, new_id, sha256_json

__all__ = ["append_event_once_in_session"]


def append_event_once_in_session(
    session: Any,
    *,
    run: RunRow,
    event_type: str,
    payload: Mapping[str, Any],
    operation_key: str,
    allowed_statuses: set[str],
    next_status: str | None = None,
) -> RunEventRow:
    normalized_payload = normalize_event_payload(event_type, dict(payload))
    existing = session.scalar(
        select(RunEventRow).where(
            RunEventRow.run_id == run.id,
            RunEventRow.operation_key == operation_key,
        )
    )
    if existing is not None:
        if existing.event_type != event_type or existing.payload_json != canonical_json(
            normalized_payload
        ):
            raise ValueError("Run operation key conflicts with an existing event")
        return existing
    if run.status not in allowed_statuses:
        raise ValueError(f"{event_type} is not valid while the Run is {run.status}")
    last = session.scalar(
        select(RunEventRow)
        .where(RunEventRow.run_id == run.id)
        .order_by(RunEventRow.sequence.desc())
        .limit(1)
    )
    if last is None:
        raise ValueError("prepared Run is missing run.queued")
    event_id = new_id("evt")
    occurred_at = clock.utc_now()
    envelope_document = {
        "event_id": event_id,
        "schema_version": "1",
        "run_id": run.id,
        "sequence": last.sequence + 1,
        "type": event_type,
        "occurred_at_utc": occurred_at.replace(tzinfo=None).isoformat(),
        "actor_type": "system",
        "actor_id": "evidrun",
        "classification": "internal",
        "payload": normalized_payload,
        "correlation_id": run.id,
        "causation_id": None,
        "prev_event_hash": last.event_hash,
    }
    row = RunEventRow(
        id=event_id,
        run_id=run.id,
        sequence=last.sequence + 1,
        event_type=event_type,
        occurred_at=occurred_at,
        actor_type="system",
        actor_id="evidrun",
        classification="internal",
        payload_json=canonical_json(normalized_payload),
        correlation_id=run.id,
        causation_id=None,
        prev_event_hash=last.event_hash,
        event_hash=sha256_json(envelope_document),
        operation_key=operation_key,
    )
    session.add(row)
    session.flush()
    if next_status is not None:
        run.status = next_status
    return row
