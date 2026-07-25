"""The Run ledger: the normative authority over what happened in a Run.

Order, hash chain, phase validity and the reserved event types are all enforced
here, in one place. `append_event` runs the family checks (`handlers/`) and the
lifecycle machine (`transitions.py`) inside the same transaction that writes the
event, so a rejected fact leaves nothing behind — and an accepted one cannot land
without its chain link and status advance.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import select

from evidrun.contracts import (
    RunSpec,
    normalize_event_payload,
)
from evidrun.contracts.runtime import (
    EVENT_ALLOWED_RUN_STATUSES,
    UNSUPPORTED_RUNTIME_EVENT_TYPES,
)
from evidrun.infrastructure.database import clock
from evidrun.infrastructure.database.ledger.appender import append_event_once_in_session
from evidrun.infrastructure.database.ledger.handlers import (
    check_capability_offered,
    check_context_composed,
    check_evaluation_completed,
    check_run_queued,
    check_subject_invoked,
    check_subject_responded,
    check_terminal_event,
    check_tool_events,
)
from evidrun.infrastructure.database.ledger.transitions import (
    TERMINAL_EVENT_TYPES,
    TERMINAL_RUN_STATUSES,
    event_transition,
)
from evidrun.infrastructure.database.models import RunEventRow, RunRow, RunSpecRow
from evidrun.infrastructure.database.queue.fencing import (
    complete_active_lease,
    reject_active_lease,
    validate_optional_lease,
    validate_reason_code,
)
from evidrun.infrastructure.database.unit_of_work import LeaseFence, UnitOfWork
from evidrun.shared.types import canonical_json, new_id, sha256_json

__all__ = ["LedgerStore"]


class LedgerStore:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self.unit_of_work = unit_of_work

    def append_event(
        self,
        *,
        run_id: str,
        event_type: str,
        payload: Mapping[str, Any],
        actor_type: str = "system",
        actor_id: str = "evidrun",
        classification: str = "internal",
        correlation_id: str | None = None,
        causation_id: str | None = None,
        operation_key: str | None = None,
        lease: LeaseFence | None = None,
        complete_execution: bool = False,
        reject_execution_code: str | None = None,
    ) -> RunEventRow:
        normalized_payload = _validate_request(
            event_type=event_type,
            actor_type=actor_type,
            actor_id=actor_id,
            payload=payload,
            lease=lease,
            complete_execution=complete_execution,
            reject_execution_code=reject_execution_code,
        )
        with self.unit_of_work.session() as session:
            validate_optional_lease(session, lease=lease, run_id=run_id)
            run = session.get(RunRow, run_id)
            if run is None:
                raise KeyError(f"Run not found: {run_id}")
            if operation_key is not None:
                existing = _resolve_idempotent(
                    session,
                    run_id=run_id,
                    event_type=event_type,
                    operation_key=operation_key,
                    normalized_payload=normalized_payload,
                    lease=lease,
                    complete_execution=complete_execution,
                    reject_execution_code=reject_execution_code,
                )
                if existing is not None:
                    return existing
            prior_events = list(
                session.scalars(
                    select(RunEventRow)
                    .where(RunEventRow.run_id == run_id)
                    .order_by(RunEventRow.sequence)
                )
            )
            last = prior_events[-1] if prior_events else None
            prior_event_types = [item.event_type for item in prior_events]
            _validate_phase(run, event_type=event_type, prior_event_types=prior_event_types)
            _run_family_checks(
                session,
                run=run,
                run_id=run_id,
                event_type=event_type,
                normalized_payload=normalized_payload,
                prior_events=prior_events,
                prior_event_types=prior_event_types,
            )
            next_status = event_transition(
                run=run,
                event_type=event_type,
                payload=normalized_payload,
                has_prior_event=last is not None,
            )
            row = _persist_event(
                session,
                run=run,
                run_id=run_id,
                event_type=event_type,
                normalized_payload=normalized_payload,
                actor_type=actor_type,
                actor_id=actor_id,
                classification=classification,
                correlation_id=correlation_id,
                causation_id=causation_id,
                operation_key=operation_key,
                last=last,
                next_status=next_status,
                lease=lease,
                complete_execution=complete_execution,
                reject_execution_code=reject_execution_code,
            )
            session.commit()
            return row

    def save_subject_response(
        self,
        *,
        run_id: str,
        spec: RunSpec,
        response_payload: Mapping[str, Any],
        captured_output: str | None,
        lease: LeaseFence,
    ) -> RunEventRow:
        """Commit the Subject response, projection and evaluation transition together."""

        with self.unit_of_work.session() as session:
            validate_optional_lease(session, lease=lease, run_id=run_id)
            run = session.get(RunRow, run_id)
            if run is None or run.run_spec_id is None:
                raise ValueError("Subject response requires a canonical RunSpec")
            spec_row = session.get(RunSpecRow, run.run_spec_id)
            if spec_row is None or spec_row.digest != spec.digest:
                raise ValueError("Subject response RunSpec is not exact")
            normalized_response = normalize_event_payload(
                "subject.responded", dict(response_payload)
            )
            if normalized_response.get("capture_mode") != spec.capture_policy.default_mode:
                raise ValueError("Subject response capture mode does not match the RunSpec")
            turn_events = list(
                session.scalars(
                    select(RunEventRow).where(
                        RunEventRow.run_id == run_id,
                        RunEventRow.event_type.in_(("subject.invoked", "subject.responded")),
                    )
                )
            )
            response_existing = session.scalar(
                select(RunEventRow).where(
                    RunEventRow.run_id == run_id,
                    RunEventRow.operation_key == "subject:responded",
                )
            )
            if response_existing is None and (
                sum(item.event_type == "subject.invoked" for item in turn_events)
                != sum(item.event_type == "subject.responded" for item in turn_events) + 1
            ):
                raise ValueError("Subject response requires one unmatched Subject invocation")
            response = append_event_once_in_session(
                session,
                run=run,
                event_type="subject.responded",
                payload=normalized_response,
                operation_key="subject:responded",
                allowed_statuses={"running"},
            )
            run.output = captured_output
            append_event_once_in_session(
                session,
                run=run,
                event_type="run.evaluating",
                payload={
                    "from_status": "running",
                    "reason": "terminal Subject response captured",
                },
                operation_key="run:evaluating",
                allowed_statuses={"running"},
                next_status="evaluating",
            )
            session.commit()
            return response

    def update_run(
        self,
        run_id: str,
        *,
        output: str | None = None,
        context_hash: str | None = None,
        lease: LeaseFence | None = None,
    ) -> RunRow:
        with self.unit_of_work.session() as session:
            validate_optional_lease(session, lease=lease, run_id=run_id)
            row = session.get(RunRow, run_id)
            if row is None:
                raise KeyError(f"Run not found: {run_id}")
            if output is not None:
                row.output = output
            if context_hash is not None:
                row.context_hash = context_hash
            session.commit()
            return row


ALLOWED_ACTOR_TYPES = {
    "system",
    "subject",
    "evaluator",
    "tool",
    "skill",
    "observer",
}
FENCED_EVENT_TYPES = {
    "capability.offered",
    "tool.called",
    "tool.denied",
    "tool.completed",
    "tool.failed",
}


def _validate_request(
    *,
    event_type: str,
    actor_type: str,
    actor_id: str,
    payload: Mapping[str, Any],
    lease: LeaseFence | None,
    complete_execution: bool,
    reject_execution_code: str | None,
) -> Mapping[str, Any]:
    """Reject the request before any session opens, and normalize the payload."""
    if actor_type not in ALLOWED_ACTOR_TYPES:
        raise ValueError(
            "Run events cannot claim human authority without a typed attestation flow"
        )
    if not actor_id.strip():
        raise ValueError("Run event actor_id cannot be empty")
    if event_type in UNSUPPORTED_RUNTIME_EVENT_TYPES:
        raise ValueError(
            "Run event type is reserved until its coordinator/runtime is implemented"
        )
    if event_type in FENCED_EVENT_TYPES and lease is None:
        raise ValueError("runtime capability and tool events require an active lease fence")
    normalized_payload = normalize_event_payload(event_type, dict(payload))
    if complete_execution and lease is None:
        raise ValueError("atomic execution completion requires a lease fence")
    if reject_execution_code is not None:
        if complete_execution or lease is None:
            raise ValueError("atomic execution rejection requires only a lease fence")
        validate_reason_code(reject_execution_code)
    return normalized_payload


def _resolve_idempotent(
    session: Any,
    *,
    run_id: str,
    event_type: str,
    operation_key: str,
    normalized_payload: Mapping[str, Any],
    lease: LeaseFence | None,
    complete_execution: bool,
    reject_execution_code: str | None,
) -> RunEventRow | None:
    """Return the event this operation key already wrote, settling the lease first."""
    existing = session.scalar(
        select(RunEventRow).where(
            RunEventRow.run_id == run_id,
            RunEventRow.operation_key == operation_key,
        )
    )
    if existing is None:
        return None
    if existing.event_type != event_type or existing.payload_json != canonical_json(
        normalized_payload
    ):
        raise ValueError("Run operation key conflicts with an existing event")
    if complete_execution and lease is not None:
        complete_active_lease(
            session,
            lease=lease,
            run_id=run_id,
            completed_at=clock.utc_now(),
        )
        session.commit()
    elif reject_execution_code is not None and lease is not None:
        reject_active_lease(
            session,
            lease=lease,
            run_id=run_id,
            rejected_at=clock.utc_now(),
            reason_code=reject_execution_code,
        )
        session.commit()
    return existing


def _validate_phase(
    run: RunRow, *, event_type: str, prior_event_types: Sequence[str]
) -> None:
    """Phase validity and Subject turn pairing, independent of event family."""
    if run.status in TERMINAL_RUN_STATUSES:
        raise ValueError("no Run events may be appended after a terminal lifecycle event")
    allowed_statuses = EVENT_ALLOWED_RUN_STATUSES.get(event_type)
    if allowed_statuses is not None and run.status not in allowed_statuses:
        raise ValueError(f"{event_type} is not valid while the Run is {run.status}")
    if event_type == "subject.invoked" and prior_event_types.count(
        "subject.invoked"
    ) != prior_event_types.count("subject.responded"):
        raise ValueError("Subject invocation requires the prior turn to be complete")
    if (
        event_type == "subject.responded"
        and prior_event_types.count("subject.invoked")
        != prior_event_types.count("subject.responded") + 1
    ):
        raise ValueError("Subject response requires one unmatched Subject invocation")
    if event_type == "run.evaluating" and "subject.responded" not in prior_event_types:
        raise ValueError("Run cannot enter evaluation before a Subject response")


def _run_family_checks(
    session: Any,
    *,
    run: RunRow,
    run_id: str,
    event_type: str,
    normalized_payload: Mapping[str, Any],
    prior_events: Sequence[RunEventRow],
    prior_event_types: Sequence[str],
) -> None:
    """Dispatch to the one handler that owns this event family."""
    if event_type == "evaluation.completed":
        check_evaluation_completed(
            session,
            run_id=run_id,
            normalized_payload=normalized_payload,
            prior_events=prior_events,
        )
    if event_type == "run.queued":
        check_run_queued(session, run=run, normalized_payload=normalized_payload)
    if event_type == "context.composed":
        check_context_composed(
            session, run=run, run_id=run_id, normalized_payload=normalized_payload
        )
    if event_type == "subject.invoked":
        check_subject_invoked(
            session, run=run, run_id=run_id, normalized_payload=normalized_payload
        )
    if event_type == "capability.offered":
        check_capability_offered(session, run=run, normalized_payload=normalized_payload)
    if event_type.startswith("tool."):
        check_tool_events(
            event_type=event_type,
            normalized_payload=normalized_payload,
            prior_events=prior_events,
            prior_event_types=prior_event_types,
        )
    if event_type == "subject.responded":
        check_subject_responded(session, run=run, normalized_payload=normalized_payload)
    if event_type in TERMINAL_EVENT_TYPES:
        check_terminal_event(
            session,
            run=run,
            run_id=run_id,
            event_type=event_type,
            normalized_payload=normalized_payload,
            prior_events=prior_events,
            prior_event_types=prior_event_types,
        )


def _persist_event(
    session: Any,
    *,
    run: RunRow,
    run_id: str,
    event_type: str,
    normalized_payload: Mapping[str, Any],
    actor_type: str,
    actor_id: str,
    classification: str,
    correlation_id: str | None,
    causation_id: str | None,
    operation_key: str | None,
    last: RunEventRow | None,
    next_status: str | None,
    lease: LeaseFence | None,
    complete_execution: bool,
    reject_execution_code: str | None,
) -> RunEventRow:
    """Write the chain link, advance the status and settle the lease, uncommitted."""
    sequence = 1 if last is None else last.sequence + 1
    event_id = new_id("evt")
    occurred_at = clock.utc_now()
    envelope = {
        "event_id": event_id,
        "schema_version": "1",
        "run_id": run_id,
        "sequence": sequence,
        "type": event_type,
        "occurred_at_utc": occurred_at.replace(tzinfo=None).isoformat(),
        "actor_type": actor_type,
        "actor_id": actor_id,
        "classification": classification,
        "payload": normalized_payload,
        "correlation_id": correlation_id or run_id,
        "causation_id": causation_id,
        "prev_event_hash": last.event_hash if last else None,
    }
    row = RunEventRow(
        id=event_id,
        run_id=run_id,
        sequence=sequence,
        event_type=event_type,
        occurred_at=occurred_at,
        actor_type=actor_type,
        actor_id=actor_id,
        classification=classification,
        payload_json=canonical_json(normalized_payload),
        correlation_id=correlation_id or run_id,
        causation_id=causation_id,
        prev_event_hash=last.event_hash if last else None,
        event_hash=sha256_json(envelope),
        operation_key=operation_key,
    )
    session.add(row)
    if next_status is not None:
        run.status = next_status
        if next_status in TERMINAL_RUN_STATUSES:
            run.completed_at = occurred_at
    if complete_execution and lease is not None:
        complete_active_lease(
            session,
            lease=lease,
            run_id=run_id,
            completed_at=occurred_at,
        )
    elif reject_execution_code is not None and lease is not None:
        reject_active_lease(
            session,
            lease=lease,
            run_id=run_id,
            rejected_at=occurred_at,
            reason_code=reject_execution_code,
        )
    return row
