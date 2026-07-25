from __future__ import annotations

from typing import Any

from sqlalchemy import func, select

from evidrun.infrastructure.database.models import (
    ChatSessionRow,
    ComparisonRow,
    ContextSnapshotRow,
    ExperimentRevisionRow,
    GradeRow,
    ProjectRow,
    RunEventRow,
    RunRow,
    WorkspaceRow,
)
from evidrun.infrastructure.database.read_model import projections
from evidrun.infrastructure.database.unit_of_work import UnitOfWork

__all__ = ["latest_dashboard"]


def latest_dashboard(unit_of_work: UnitOfWork) -> dict[str, Any]:
    """One read-only pass over every top-level entity the workspace view shows."""
    with unit_of_work.session() as session:
        workspaces = list(session.scalars(select(WorkspaceRow).order_by(WorkspaceRow.created_at)))
        projects = list(session.scalars(select(ProjectRow).order_by(ProjectRow.created_at)))
        experiments = list(
            session.scalars(
                select(ExperimentRevisionRow).order_by(ExperimentRevisionRow.created_at.desc())
            )
        )
        runs = list(session.scalars(select(RunRow).order_by(RunRow.created_at.desc())))
        comparisons = list(
            session.scalars(select(ComparisonRow).order_by(ComparisonRow.created_at.desc()))
        )
        chats = list(
            session.scalars(select(ChatSessionRow).order_by(ChatSessionRow.created_at.desc()))
        )
        grades = list(session.scalars(select(GradeRow).order_by(GradeRow.created_at.desc())))
        snapshots = list(
            session.scalars(
                select(ContextSnapshotRow).order_by(ContextSnapshotRow.created_at.desc())
            )
        )
        events_count = session.scalar(select(func.count()).select_from(RunEventRow)) or 0

    grade_by_run = {grade.run_id: grade for grade in grades}
    snapshot_by_run = {snapshot.run_id: snapshot for snapshot in snapshots}
    return {
        "workspaces": [projections.workspace_document(row) for row in workspaces],
        "projects": [projections.project_document(row) for row in projects],
        "experiments": [projections.experiment_document(row) for row in experiments],
        "runs": [
            projections.run_document(row, grade_by_run.get(row.id), snapshot_by_run.get(row.id))
            for row in runs
        ],
        "comparisons": [projections.comparison_document(row) for row in comparisons],
        "chats": [projections.chat_document(row) for row in chats],
        "summary": {
            "experiments": len(experiments),
            "runs": len(runs),
            "comparisons": len(comparisons),
            "events": events_count,
        },
    }
