from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import func, select

from evidrun.infrastructure.database.engine import Database
from evidrun.infrastructure.database.models import (
    ChatMessageRow,
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
from evidrun.shared.types import canonical_json, new_id, sha256_json, utc_now


class Repository:
    def __init__(self, database: Database):
        self.database = database

    def create_workspace(self, name: str) -> WorkspaceRow:
        row = WorkspaceRow(id=new_id("ws"), name=name, created_at=utc_now())
        with self.database.session() as session:
            session.add(row)
            session.commit()
        return row

    def create_project(self, workspace_id: str, name: str) -> ProjectRow:
        row = ProjectRow(
            id=new_id("prj"), workspace_id=workspace_id, name=name, created_at=utc_now()
        )
        with self.database.session() as session:
            session.add(row)
            session.commit()
        return row

    def save_experiment_revision(
        self, *, project_id: str, manifest: Mapping[str, Any], status: str = "accepted"
    ) -> ExperimentRevisionRow:
        digest = sha256_json(manifest)
        with self.database.session() as session:
            existing = session.scalar(
                select(ExperimentRevisionRow).where(ExperimentRevisionRow.manifest_hash == digest)
            )
            if existing:
                return existing
            row = ExperimentRevisionRow(
                id=new_id("expr"),
                experiment_id=str(manifest["id"]),
                project_id=project_id,
                title=str(manifest["title"]),
                status=status,
                manifest_json=canonical_json(manifest),
                manifest_hash=digest,
                created_at=utc_now(),
            )
            session.add(row)
            session.commit()
            return row

    def create_run(
        self,
        *,
        experiment_revision_id: str,
        variant_id: str,
        runner: str,
        objective: str,
        repetition: int = 1,
    ) -> RunRow:
        row = RunRow(
            id=new_id("run"),
            experiment_revision_id=experiment_revision_id,
            variant_id=variant_id,
            repetition=repetition,
            status="queued",
            runner=runner,
            objective=objective,
            created_at=utc_now(),
        )
        with self.database.session() as session:
            session.add(row)
            session.commit()
        return row

    def update_run(
        self,
        run_id: str,
        *,
        status: str,
        output: str | None = None,
        context_hash: str | None = None,
        completed_at: datetime | None = None,
    ) -> RunRow:
        with self.database.session() as session:
            row = session.get(RunRow, run_id)
            if row is None:
                raise KeyError(f"Run not found: {run_id}")
            row.status = status
            if output is not None:
                row.output = output
            if context_hash is not None:
                row.context_hash = context_hash
            if completed_at is not None:
                row.completed_at = completed_at
            session.commit()
            return row

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
    ) -> RunEventRow:
        with self.database.session() as session:
            last = session.scalar(
                select(RunEventRow)
                .where(RunEventRow.run_id == run_id)
                .order_by(RunEventRow.sequence.desc())
                .limit(1)
            )
            sequence = 1 if last is None else last.sequence + 1
            event_id = new_id("evt")
            occurred_at = utc_now()
            occurred_at_canonical = occurred_at.replace(tzinfo=None).isoformat()
            envelope = {
                "event_id": event_id,
                "schema_version": "1",
                "run_id": run_id,
                "sequence": sequence,
                "type": event_type,
                "occurred_at_utc": occurred_at_canonical,
                "actor_type": actor_type,
                "actor_id": actor_id,
                "classification": classification,
                "payload": payload,
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
                payload_json=canonical_json(payload),
                correlation_id=correlation_id or run_id,
                causation_id=causation_id,
                prev_event_hash=last.event_hash if last else None,
                event_hash=sha256_json(envelope),
            )
            session.add(row)
            session.commit()
            return row

    def save_snapshot(self, run_id: str, snapshot: Mapping[str, Any]) -> ContextSnapshotRow:
        row = ContextSnapshotRow(
            id=new_id("ctx"),
            run_id=run_id,
            policy_id=str(snapshot["policy_id"]),
            strategy=str(snapshot["strategy"]),
            max_chars=int(snapshot["max_chars"]),
            source_chars=int(snapshot["source_chars"]),
            selected_chars=int(snapshot["selected_chars"]),
            selected_content=str(snapshot["selected_content"]),
            omitted_json=canonical_json(snapshot["omitted"]),
            content_hash=str(snapshot["content_hash"]),
            created_at=utc_now(),
        )
        with self.database.session() as session:
            session.add(row)
            session.commit()
        return row

    def save_grade(
        self,
        *,
        run_id: str,
        grader_id: str,
        score: float,
        passed: bool,
        rationale: str,
        evidence: Sequence[str],
    ) -> GradeRow:
        row = GradeRow(
            id=new_id("grade"),
            run_id=run_id,
            grader_id=grader_id,
            score=score,
            passed=passed,
            rationale=rationale,
            evidence_json=canonical_json(list(evidence)),
            created_at=utc_now(),
        )
        with self.database.session() as session:
            session.add(row)
            session.commit()
        return row

    def save_comparison(
        self,
        *,
        experiment_revision_id: str,
        baseline_run_id: str,
        candidate_run_id: str,
        primary_variable: str,
        validity: str,
        baseline_score: float,
        candidate_score: float,
        report_markdown: str,
    ) -> ComparisonRow:
        row = ComparisonRow(
            id=new_id("cmp"),
            experiment_revision_id=experiment_revision_id,
            baseline_run_id=baseline_run_id,
            candidate_run_id=candidate_run_id,
            primary_variable=primary_variable,
            validity=validity,
            baseline_score=baseline_score,
            candidate_score=candidate_score,
            delta=candidate_score - baseline_score,
            report_markdown=report_markdown,
            created_at=utc_now(),
        )
        with self.database.session() as session:
            session.add(row)
            session.commit()
        return row

    def create_chat_session(
        self,
        *,
        workspace_id: str,
        title: str,
        scope_type: str | None = None,
        scope_id: str | None = None,
    ) -> ChatSessionRow:
        row = ChatSessionRow(
            id=new_id("chat"),
            workspace_id=workspace_id,
            title=title,
            scope_type=scope_type,
            scope_id=scope_id,
            created_at=utc_now(),
        )
        with self.database.session() as session:
            session.add(row)
            session.commit()
        return row

    def add_chat_message(self, session_id: str, role: str, content: str) -> ChatMessageRow:
        row = ChatMessageRow(
            id=new_id("msg"),
            session_id=session_id,
            role=role,
            content=content,
            created_at=utc_now(),
        )
        with self.database.session() as session:
            session.add(row)
            session.commit()
        return row

    def latest_dashboard(self) -> dict[str, Any]:
        with self.database.session() as session:
            workspaces = list(
                session.scalars(select(WorkspaceRow).order_by(WorkspaceRow.created_at))
            )
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
            "workspaces": [self._workspace_dict(row) for row in workspaces],
            "projects": [self._project_dict(row) for row in projects],
            "experiments": [self._experiment_dict(row) for row in experiments],
            "runs": [
                self._run_dict(row, grade_by_run.get(row.id), snapshot_by_run.get(row.id))
                for row in runs
            ],
            "comparisons": [self._comparison_dict(row) for row in comparisons],
            "chats": [self._chat_dict(row) for row in chats],
            "summary": {
                "experiments": len(experiments),
                "runs": len(runs),
                "comparisons": len(comparisons),
                "events": events_count,
            },
        }

    def get_run_events(self, run_id: str) -> list[dict[str, Any]]:
        with self.database.session() as session:
            rows = list(
                session.scalars(
                    select(RunEventRow)
                    .where(RunEventRow.run_id == run_id)
                    .order_by(RunEventRow.sequence)
                )
            )
        return [self._event_dict(row) for row in rows]

    def get_experiment(self, revision_id: str) -> ExperimentRevisionRow:
        with self.database.session() as session:
            row = session.get(ExperimentRevisionRow, revision_id)
            if row is None:
                raise KeyError(revision_id)
            session.expunge(row)
            return row

    def get_run(self, run_id: str) -> RunRow:
        with self.database.session() as session:
            row = session.get(RunRow, run_id)
            if row is None:
                raise KeyError(run_id)
            session.expunge(row)
            return row

    def get_grade(self, run_id: str) -> GradeRow:
        with self.database.session() as session:
            row = session.scalar(select(GradeRow).where(GradeRow.run_id == run_id))
            if row is None:
                raise KeyError(run_id)
            session.expunge(row)
            return row

    def get_comparison(self, comparison_id: str) -> ComparisonRow:
        with self.database.session() as session:
            row = session.get(ComparisonRow, comparison_id)
            if row is None:
                raise KeyError(comparison_id)
            session.expunge(row)
            return row

    @staticmethod
    def _workspace_dict(row: WorkspaceRow) -> dict[str, Any]:
        return {"id": row.id, "name": row.name, "created_at": row.created_at.isoformat()}

    @staticmethod
    def _project_dict(row: ProjectRow) -> dict[str, Any]:
        return {
            "id": row.id,
            "workspace_id": row.workspace_id,
            "name": row.name,
            "created_at": row.created_at.isoformat(),
        }

    @staticmethod
    def _experiment_dict(row: ExperimentRevisionRow) -> dict[str, Any]:
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

    @staticmethod
    def _run_dict(
        row: RunRow, grade: GradeRow | None, snapshot: ContextSnapshotRow | None
    ) -> dict[str, Any]:
        return {
            "id": row.id,
            "experiment_revision_id": row.experiment_revision_id,
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

    @staticmethod
    def _comparison_dict(row: ComparisonRow) -> dict[str, Any]:
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

    @staticmethod
    def _chat_dict(row: ChatSessionRow) -> dict[str, Any]:
        return {
            "id": row.id,
            "workspace_id": row.workspace_id,
            "scope_type": row.scope_type,
            "scope_id": row.scope_id,
            "title": row.title,
            "created_at": row.created_at.isoformat(),
        }

    @staticmethod
    def _event_dict(row: RunEventRow) -> dict[str, Any]:
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
