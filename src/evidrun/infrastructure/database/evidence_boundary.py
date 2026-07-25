"""Boundary checks shared by evaluation and checkpoint records.

A record claims evidence "up to" a ledger position. These verify that the claim
matches the ledger, so a record can never authorize evidence the Run never
produced.
"""

from __future__ import annotations

from sqlalchemy import select

from evidrun.contracts import EvaluationRecord
from evidrun.infrastructure.database.models import CheckpointRecordRow, RunEventRow
from evidrun.infrastructure.database.unit_of_work import UnitOfWork

__all__ = ["validate_evaluation_boundary", "validate_evidence_boundary"]


def validate_evidence_boundary(
    unit_of_work: UnitOfWork, *, run_id: str, sequence: int | None, event_hash: str | None
) -> None:
    if sequence is None and event_hash is None:
        return
    if sequence is None or event_hash is None:
        raise ValueError("event boundary requires sequence and hash")
    with unit_of_work.session() as session:
        event = session.scalar(
            select(RunEventRow).where(
                RunEventRow.run_id == run_id,
                RunEventRow.sequence == sequence,
            )
        )
    if event is None or event.event_hash != event_hash:
        raise ValueError("event boundary does not match the Run ledger")


def validate_evaluation_boundary(unit_of_work: UnitOfWork, record: EvaluationRecord) -> None:
    checkpoint_id = record.boundary.checkpoint_id
    if checkpoint_id is None:
        return
    with unit_of_work.session() as session:
        checkpoint = session.get(CheckpointRecordRow, checkpoint_id)
    if checkpoint is None or checkpoint.run_id != record.run_id:
        raise ValueError("evaluation checkpoint boundary does not belong to the Run")
