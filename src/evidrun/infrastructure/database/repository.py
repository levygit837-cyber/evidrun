from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy import func, select

from evidrun.contracts import (
    AdmissionRecord,
    CheckpointRecord,
    ContractRef,
    EvaluationRecord,
    EvaluationValidator,
    RevisionDecisionRecord,
    RevisionEnvelope,
    RunRecord,
    RunSpec,
    normalize_event_payload,
    parse_revision,
    semantic_model_dump,
)
from evidrun.contracts.compiler import InMemoryContractRegistry
from evidrun.infrastructure.database.engine import Database
from evidrun.infrastructure.database.models import (
    AdmissionRecordRow,
    ChatMessageRow,
    ChatSessionRow,
    CheckpointRecordRow,
    ComparisonRow,
    ContextSnapshotRow,
    ContractDecisionRow,
    ContractRevisionRow,
    EvaluationRecordRow,
    ExperimentRevisionRow,
    GradeRow,
    ProjectRow,
    RunEventRow,
    RunRow,
    RunSpecRow,
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

    def save_contract_revision(
        self, revision: RevisionEnvelope, *, status: str = "draft"
    ) -> ContractRevisionRow:
        if status not in {"draft", "proposed"}:
            raise ValueError("new contract revision status must be draft or proposed")
        document = revision.semantic_document()
        with self.database.session() as session:
            existing = session.scalar(
                select(ContractRevisionRow).where(
                    ContractRevisionRow.contract_type == revision.ref.contract_type.value,
                    ContractRevisionRow.logical_id == revision.logical_id,
                    ContractRevisionRow.revision == revision.revision,
                )
            )
            if existing is not None:
                if existing.digest != revision.digest or existing.document_json != canonical_json(
                    document
                ):
                    raise ValueError(
                        "an immutable contract revision already exists with different content"
                    )
                if existing.status == "draft" and status == "proposed":
                    existing.status = "proposed"
                    session.commit()
                return existing
            latest_revision = session.scalar(
                select(func.max(ContractRevisionRow.revision)).where(
                    ContractRevisionRow.contract_type == revision.ref.contract_type.value,
                    ContractRevisionRow.logical_id == revision.logical_id,
                )
            )
            expected_revision = (latest_revision or 0) + 1
            if revision.revision != expected_revision:
                raise ValueError(
                    "contract revision must be monotonic; "
                    f"expected {expected_revision}, received {revision.revision}"
                )
            row = ContractRevisionRow(
                id=new_id("crev"),
                contract_type=revision.ref.contract_type.value,
                logical_id=revision.logical_id,
                revision=revision.revision,
                project_id=revision.project_id,
                title=revision.title,
                status=status,
                document_json=canonical_json(document),
                digest=revision.digest,
                created_at=utc_now(),
            )
            session.add(row)
            session.commit()
            return row

    def decide_contract_revision(
        self, decision: RevisionDecisionRecord
    ) -> ContractDecisionRow:
        with self.database.session() as session:
            revision = session.scalar(
                select(ContractRevisionRow).where(
                    ContractRevisionRow.contract_type
                    == decision.revision_ref.contract_type.value,
                    ContractRevisionRow.logical_id == decision.revision_ref.logical_id,
                    ContractRevisionRow.revision == decision.revision_ref.revision,
                )
            )
            if revision is None or revision.digest != decision.revision_ref.digest:
                raise ValueError("decision references an unknown or mismatched revision")
            previous = session.scalar(
                select(ContractDecisionRow)
                .where(ContractDecisionRow.contract_revision_id == revision.id)
                .order_by(ContractDecisionRow.decided_at.desc())
                .limit(1)
            )
            if previous is None and decision.decision == "superseded":
                raise ValueError("only an accepted revision can be superseded")
            if previous is not None:
                if previous.decision != decision.decision:
                    if not (
                        previous.decision == "accepted"
                        and decision.decision == "superseded"
                    ):
                        raise ValueError("contract revision already has a conflicting decision")
                else:
                    return previous
            row = ContractDecisionRow(
                id=new_id("cdec"),
                contract_revision_id=revision.id,
                decision=decision.decision,
                actor_type=decision.actor_type,
                actor_id=decision.actor_id,
                rationale=decision.rationale,
                decision_json=canonical_json(
                    semantic_model_dump(decision)
                ),
                decision_digest=decision.digest,
                decided_at=decision.decided_at_utc,
            )
            revision.status = decision.decision
            session.add(row)
            session.commit()
            return row

    def contract_registry(self, project_id: str | None = None) -> InMemoryContractRegistry:
        with self.database.session() as session:
            query = select(ContractRevisionRow).order_by(
                ContractRevisionRow.contract_type,
                ContractRevisionRow.logical_id,
                ContractRevisionRow.revision,
            )
            if project_id is not None:
                query = query.where(ContractRevisionRow.project_id == project_id)
            revisions = list(session.scalars(query))
            decisions = list(
                session.scalars(
                    select(ContractDecisionRow).order_by(ContractDecisionRow.decided_at)
                )
            )
        registry = InMemoryContractRegistry()
        row_by_id: dict[str, RevisionEnvelope] = {}
        for row in revisions:
            revision = parse_revision(json.loads(row.document_json))
            if revision.digest != row.digest:
                raise ValueError(f"stored contract digest mismatch: {row.id}")
            registry.add(revision)
            row_by_id[row.id] = revision
        for row in decisions:
            revision = row_by_id.get(row.contract_revision_id)
            if revision is None:
                continue
            decision = RevisionDecisionRecord.model_validate(json.loads(row.decision_json))
            if decision.digest != row.decision_digest:
                raise ValueError(f"stored contract decision digest mismatch: {row.id}")
            registry.decide(decision)
        return registry

    def get_contract_revision(self, revision_id: str) -> RevisionEnvelope:
        with self.database.session() as session:
            row = session.get(ContractRevisionRow, revision_id)
            if row is None:
                raise KeyError(revision_id)
            revision = parse_revision(json.loads(row.document_json))
        if revision.digest != row.digest:
            raise ValueError(f"stored contract digest mismatch: {revision_id}")
        return revision

    def list_contract_revisions(self, project_id: str | None = None) -> list[dict[str, Any]]:
        with self.database.session() as session:
            query = select(ContractRevisionRow).order_by(
                ContractRevisionRow.contract_type,
                ContractRevisionRow.logical_id,
                ContractRevisionRow.revision,
            )
            if project_id is not None:
                query = query.where(ContractRevisionRow.project_id == project_id)
            rows = list(session.scalars(query))
            decisions = list(session.scalars(select(ContractDecisionRow)))
        decision_by_revision = {
            decision.contract_revision_id: decision.decision for decision in decisions
        }
        return [
            {
                "id": row.id,
                "contract_type": row.contract_type,
                "logical_id": row.logical_id,
                "revision": row.revision,
                "project_id": row.project_id,
                "title": row.title,
                "digest": row.digest,
                "status": row.status,
                "decision": decision_by_revision.get(row.id),
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ]

    def get_contract_revision_by_ref(self, reference: ContractRef) -> RevisionEnvelope:
        with self.database.session() as session:
            row = session.scalar(
                select(ContractRevisionRow).where(
                    ContractRevisionRow.contract_type == str(reference.contract_type.value),
                    ContractRevisionRow.logical_id == str(reference.logical_id),
                    ContractRevisionRow.revision == int(reference.revision),
                )
            )
            if row is None:
                raise KeyError(str(reference.logical_id))
            revision = parse_revision(json.loads(row.document_json))
        if revision.digest != reference.digest or row.digest != reference.digest:
            raise ValueError("stored contract does not match its reference")
        return revision

    def save_run_spec(self, spec: RunSpec) -> RunSpecRow:
        with self.database.session() as session:
            existing = session.scalar(
                select(RunSpecRow).where(RunSpecRow.digest == spec.digest)
            )
            if existing is not None:
                return existing
            row = RunSpecRow(
                id=new_id("rspec"),
                study_logical_id=spec.study_ref.logical_id,
                scenario_logical_id=spec.scenario_ref.logical_id,
                variant_id=spec.variant_id,
                repetition_index=spec.repetition_index,
                spec_json=canonical_json(
                    semantic_model_dump(spec)
                ),
                digest=spec.digest,
                created_at=utc_now(),
            )
            session.add(row)
            session.commit()
            return row

    def save_admission_record(
        self, run_spec_id: str, record: AdmissionRecord
    ) -> AdmissionRecordRow:
        with self.database.session() as session:
            spec = session.get(RunSpecRow, run_spec_id)
            if spec is None:
                raise KeyError(f"RunSpec not found: {run_spec_id}")
            if spec.digest != record.run_spec_digest:
                raise ValueError("admission digest does not match its RunSpec")
            existing = session.scalar(
                select(AdmissionRecordRow).where(
                    AdmissionRecordRow.run_spec_id == run_spec_id,
                    AdmissionRecordRow.digest == record.digest,
                )
            )
            if existing is not None:
                return existing
            row = AdmissionRecordRow(
                id=new_id("adm"),
                run_spec_id=run_spec_id,
                decision=record.decision,
                record_json=canonical_json(
                    semantic_model_dump(record)
                ),
                digest=record.digest,
                created_at=record.created_at_utc,
            )
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
        run_spec_id: str | None = None,
        admission_id: str | None = None,
        retry_of: str | None = None,
    ) -> RunRow:
        if (run_spec_id is None) != (admission_id is None):
            raise ValueError("RunSpec and AdmissionRecord must be linked together")
        if run_spec_id is not None and admission_id is not None:
            with self.database.session() as session:
                spec = session.get(RunSpecRow, run_spec_id)
                admission = session.get(AdmissionRecordRow, admission_id)
                if spec is None or admission is None:
                    raise ValueError("RunSpec or AdmissionRecord does not exist")
                if admission.run_spec_id != spec.id or admission.decision != "admitted":
                    raise ValueError("Run requires an admitted record for the exact RunSpec")
        row = RunRow(
            id=new_id("run"),
            experiment_revision_id=experiment_revision_id,
            variant_id=variant_id,
            repetition=repetition,
            status="queued",
            runner=runner,
            objective=objective,
            run_spec_id=run_spec_id,
            admission_id=admission_id,
            retry_of=retry_of,
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
        normalized_payload = normalize_event_payload(event_type, dict(payload))
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

    def save_evaluation_record(self, record: EvaluationRecord) -> EvaluationRecordRow:
        self._validate_evaluation_boundary(record)
        self._validate_evidence_boundary(
            run_id=record.run_id,
            sequence=record.boundary.up_to_event_sequence,
            event_hash=record.boundary.event_hash,
        )
        with self.database.session() as session:
            run = session.get(RunRow, record.run_id)
            if run is None:
                raise KeyError(f"Run not found: {record.run_id}")
            if run.run_spec_id is None:
                raise ValueError("legacy Run does not have an EvaluationPlanRevision")
            spec_row = session.get(RunSpecRow, run.run_spec_id)
            if spec_row is None:
                raise ValueError("Run references a missing RunSpec")
            spec = RunSpec.model_validate(json.loads(spec_row.spec_json))
            if spec.evaluation_plan_ref != record.plan_ref:
                raise ValueError("evaluation plan does not belong to the RunSpec")
            EvaluationValidator.validate(spec.evaluation_plan, record)
            if record.source_type == "human_adjudicator":
                prior_adjudicated = session.get(
                    EvaluationRecordRow, record.supersedes_record_ref
                )
                if prior_adjudicated is None or prior_adjudicated.run_id != record.run_id:
                    raise ValueError(
                        "human adjudication must reference an existing record from the same Run"
                    )
            prior_rows = list(
                session.scalars(
                    select(EvaluationRecordRow)
                    .where(EvaluationRecordRow.run_id == record.run_id)
                    .order_by(EvaluationRecordRow.created_at)
                )
            )
            prior_gate_results: dict[
                str, Literal["passed", "failed", "not_applicable"]
            ] = {
                prior.stage_id: EvaluationRecord.model_validate(
                    json.loads(prior.record_json)
                ).gate_status
                for prior in prior_rows
            }
            visible_stages = EvaluationValidator.stages_visible_after_gates(
                spec.evaluation_plan, prior_gate_results
            )
            if record.stage_id not in visible_stages:
                raise ValueError("evaluation stage is blocked by a failed hard gate")
            existing = session.scalar(
                select(EvaluationRecordRow).where(
                    EvaluationRecordRow.record_digest == record.digest
                )
            )
            if existing is not None:
                return existing
            row = EvaluationRecordRow(
                id=record.record_id,
                run_id=record.run_id,
                source_type=record.source_type,
                stage_id=record.stage_id,
                record_json=canonical_json(
                    semantic_model_dump(record)
                ),
                record_digest=record.digest,
                created_at=record.created_at_utc,
            )
            session.add(row)
            session.commit()
            return row

    def save_checkpoint_record(self, record: CheckpointRecord) -> CheckpointRecordRow:
        self._validate_evidence_boundary(
            run_id=record.run_id,
            sequence=record.up_to_event_sequence,
            event_hash=record.event_hash,
        )
        with self.database.session() as session:
            run = session.get(RunRow, record.run_id)
            if run is None:
                raise KeyError(f"Run not found: {record.run_id}")
            if run.run_spec_id is None:
                raise ValueError("legacy Run does not have a checkpoint policy")
            spec_row = session.get(RunSpecRow, run.run_spec_id)
            if spec_row is None:
                raise ValueError("Run references a missing RunSpec")
            spec = RunSpec.model_validate(json.loads(spec_row.spec_json))
            if spec.checkpoint_policy_ref != record.policy_ref or spec.checkpoint_policy is None:
                raise ValueError("checkpoint policy does not belong to the RunSpec")
            definition = next(
                (
                    item
                    for item in spec.checkpoint_policy.definitions
                    if item.id == record.definition_id
                ),
                None,
            )
            if definition is None:
                raise ValueError("checkpoint definition does not belong to the RunSpec")
            expected_definition_digest = sha256_json(semantic_model_dump(definition))
            if record.definition_digest != expected_definition_digest:
                raise ValueError("checkpoint definition digest does not match the RunSpec")
            existing = session.scalar(
                select(CheckpointRecordRow).where(
                    CheckpointRecordRow.checkpoint_hash == record.checkpoint_hash
                )
            )
            if existing is not None:
                return existing
            row = CheckpointRecordRow(
                id=record.checkpoint_id,
                run_id=record.run_id,
                definition_id=record.definition_id,
                up_to_event_sequence=record.up_to_event_sequence,
                record_json=canonical_json(
                    semantic_model_dump(record)
                ),
                checkpoint_hash=record.checkpoint_hash,
                created_at=record.created_at_utc,
            )
            session.add(row)
            session.commit()
            return row

    def _validate_evidence_boundary(
        self, *, run_id: str, sequence: int | None, event_hash: str | None
    ) -> None:
        if sequence is None and event_hash is None:
            return
        if sequence is None or event_hash is None:
            raise ValueError("event boundary requires sequence and hash")
        with self.database.session() as session:
            event = session.scalar(
                select(RunEventRow).where(
                    RunEventRow.run_id == run_id,
                    RunEventRow.sequence == sequence,
                )
            )
        if event is None or event.event_hash != event_hash:
            raise ValueError("event boundary does not match the Run ledger")

    def _validate_evaluation_boundary(self, record: EvaluationRecord) -> None:
        checkpoint_id = record.boundary.checkpoint_id
        if checkpoint_id is None:
            return
        with self.database.session() as session:
            checkpoint = session.get(CheckpointRecordRow, checkpoint_id)
        if checkpoint is None or checkpoint.run_id != record.run_id:
            raise ValueError("evaluation checkpoint boundary does not belong to the Run")

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

    def get_run_spec(self, run_spec_id: str) -> RunSpec:
        with self.database.session() as session:
            row = session.get(RunSpecRow, run_spec_id)
            if row is None:
                raise KeyError(run_spec_id)
            spec = RunSpec.model_validate(json.loads(row.spec_json))
        if spec.digest != row.digest:
            raise ValueError(f"stored RunSpec digest mismatch: {run_spec_id}")
        return spec

    def get_admission_record(self, admission_id: str) -> AdmissionRecord:
        with self.database.session() as session:
            row = session.get(AdmissionRecordRow, admission_id)
            if row is None:
                raise KeyError(admission_id)
            record = AdmissionRecord.model_validate(json.loads(row.record_json))
        if record.digest != row.digest:
            raise ValueError(f"stored admission digest mismatch: {admission_id}")
        return record

    def get_run_contracts(self, run_id: str) -> tuple[RunSpec, AdmissionRecord] | None:
        row = self.get_run(run_id)
        if row.run_spec_id is None or row.admission_id is None:
            return None
        return self.get_run_spec(row.run_spec_id), self.get_admission_record(row.admission_id)

    def get_run_record(self, run_id: str) -> RunRecord | None:
        row = self.get_run(run_id)
        contracts = self.get_run_contracts(run_id)
        if contracts is None or row.run_spec_id is None or row.admission_id is None:
            return None
        spec, admission = contracts
        created_at = row.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        return RunRecord(
            run_id=row.id,
            run_spec_id=row.run_spec_id,
            run_spec_digest=spec.digest,
            admission_id=row.admission_id,
            admission_digest=admission.digest,
            study_ref=spec.study_ref,
            scenario_ref=spec.scenario_ref,
            variant_id=row.variant_id,
            repetition_index=row.repetition,
            retry_of=row.retry_of,
            created_at_utc=created_at,
        )

    def get_evaluation_records(self, run_id: str) -> list[EvaluationRecord]:
        with self.database.session() as session:
            rows = list(
                session.scalars(
                    select(EvaluationRecordRow)
                    .where(EvaluationRecordRow.run_id == run_id)
                    .order_by(EvaluationRecordRow.created_at)
                )
            )
        records: list[EvaluationRecord] = []
        for row in rows:
            record = EvaluationRecord.model_validate(json.loads(row.record_json))
            if record.digest != row.record_digest:
                raise ValueError(f"stored evaluation digest mismatch: {row.id}")
            records.append(record)
        return records

    def get_checkpoint_records(self, run_id: str) -> list[CheckpointRecord]:
        with self.database.session() as session:
            rows = list(
                session.scalars(
                    select(CheckpointRecordRow)
                    .where(CheckpointRecordRow.run_id == run_id)
                    .order_by(CheckpointRecordRow.up_to_event_sequence)
                )
            )
        records: list[CheckpointRecord] = []
        for row in rows:
            record = CheckpointRecord.model_validate(json.loads(row.record_json))
            if record.checkpoint_hash != row.checkpoint_hash:
                raise ValueError(f"stored checkpoint digest mismatch: {row.id}")
            records.append(record)
        return records

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
