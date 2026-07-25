"""Row-to-document projections.

These are derived views of persisted rows, never a second source of truth: every
field here is read straight off the row it projects.
"""

from __future__ import annotations

import json
from typing import Any

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

__all__ = [
    "chat_document",
    "comparison_document",
    "event_document",
    "experiment_document",
    "project_document",
    "run_document",
    "workspace_document",
]


def workspace_document(row: WorkspaceRow) -> dict[str, Any]:
    return {"id": row.id, "name": row.name, "created_at": row.created_at.isoformat()}


def project_document(row: ProjectRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "workspace_id": row.workspace_id,
        "name": row.name,
        "created_at": row.created_at.isoformat(),
    }


def experiment_document(row: ExperimentRevisionRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "experiment_id": row.experiment_id,
        "project_id": row.project_id,
        "title": row.title,
        "status": row.status,
        "manifest_hash": row.manifest_hash,
        "manifest": json.loads(row.manifest_json),
        "created_at": row.created_at.isoformat(),
    }


def run_document(
    row: RunRow, grade: GradeRow | None, snapshot: ContextSnapshotRow | None
) -> dict[str, Any]:
    return {
        "id": row.id,
        "experiment_revision_id": row.experiment_revision_id,
        "contract_mode": "study_v1" if row.run_spec_id else "legacy_v1",
        "run_spec_id": row.run_spec_id,
        "admission_id": row.admission_id,
        "variant_id": row.variant_id,
        "status": row.status,
        "runner": row.runner,
        "output": row.output,
        "context_hash": row.context_hash,
        "created_at": row.created_at.isoformat(),
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        "grade": (
            {
                "id": grade.id,
                "score": grade.score,
                "passed": grade.passed,
                "rationale": grade.rationale,
                "evidence": json.loads(grade.evidence_json),
            }
            if grade
            else None
        ),
        "context_snapshot": (
            {
                "id": snapshot.id,
                "policy_id": snapshot.policy_id,
                "strategy": snapshot.strategy,
                "max_chars": snapshot.max_chars,
                "source_chars": snapshot.source_chars,
                "selected_chars": snapshot.selected_chars,
                "selected_content": snapshot.selected_content,
                "omitted": json.loads(snapshot.omitted_json),
                "content_hash": snapshot.content_hash,
            }
            if snapshot
            else None
        ),
    }


def comparison_document(row: ComparisonRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "experiment_revision_id": row.experiment_revision_id,
        "baseline_run_id": row.baseline_run_id,
        "candidate_run_id": row.candidate_run_id,
        "primary_variable": row.primary_variable,
        "validity": row.validity,
        "baseline_score": row.baseline_score,
        "candidate_score": row.candidate_score,
        "delta": row.delta,
        "report_markdown": row.report_markdown,
        "created_at": row.created_at.isoformat(),
    }


def chat_document(row: ChatSessionRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "workspace_id": row.workspace_id,
        "scope_type": row.scope_type,
        "scope_id": row.scope_id,
        "title": row.title,
        "created_at": row.created_at.isoformat(),
    }


def event_document(row: RunEventRow) -> dict[str, Any]:
    return {
        "event_id": row.id,
        "schema_version": "1",
        "run_id": row.run_id,
        "sequence": row.sequence,
        "type": row.event_type,
        "occurred_at_utc": row.occurred_at.replace(tzinfo=None).isoformat(),
        "actor_type": row.actor_type,
        "actor_id": row.actor_id,
        "classification": row.classification,
        "payload": json.loads(row.payload_json),
        "correlation_id": row.correlation_id,
        "causation_id": row.causation_id,
        "prev_event_hash": row.prev_event_hash,
        "event_hash": row.event_hash,
    }
