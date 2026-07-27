"""Read-only projections of persisted contracts and ledger rows.

Every method here verifies the stored digest before handing a document back: a
projection that silently disagrees with its record would become a second source
of truth, which the ledger authority forbids.
"""

from __future__ import annotations

import json
from datetime import UTC
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from evidrun.contracts import (
    AdmissionRecord,
    CheckpointRecord,
    ContractRef,
    EvaluationRecord,
    RevisionEnvelope,
    RunRecord,
    RunSpec,
    SubjectEnvelope,
    SubjectEnvelopeRecord,
    parse_revision,
)
from evidrun.infrastructure.database.models import (
    AdmissionRecordRow,
    CheckpointRecordRow,
    ComparisonRow,
    ContractDecisionRow,
    ContractRevisionRow,
    EvaluationRecordRow,
    ExperimentRevisionRow,
    GradeRow,
    ProjectRow,
    RunEventRow,
    RunRow,
    RunSpecRow,
    SubjectEnvelopeRow,
    WorkspaceRow,
)
from evidrun.infrastructure.database.read_model import projections
from evidrun.infrastructure.database.read_model.dashboard import latest_dashboard
from evidrun.infrastructure.database.scope_errors import (
    ScopeStorageUnavailable,
    project_workspace_not_found,
)
from evidrun.infrastructure.database.timestamps import aware_utc
from evidrun.infrastructure.database.unit_of_work import UnitOfWork

__all__ = ["ReadModel"]


class ReadModel:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self.unit_of_work = unit_of_work

    def latest_dashboard(self) -> dict[str, Any]:
        return latest_dashboard(self.unit_of_work)

    def list_workspaces(self) -> list[dict[str, Any]]:
        try:
            with self.unit_of_work.session() as session:
                rows = list(
                    session.scalars(
                        select(WorkspaceRow).order_by(
                            WorkspaceRow.created_at, WorkspaceRow.id
                        )
                    )
                )
        except SQLAlchemyError as exc:
            raise ScopeStorageUnavailable() from exc
        return [projections.workspace_document(row) for row in rows]

    def list_projects(self, workspace_id: str | None = None) -> list[dict[str, Any]]:
        try:
            with self.unit_of_work.session() as session:
                if workspace_id is not None and session.get(WorkspaceRow, workspace_id) is None:
                    raise project_workspace_not_found()
                query = select(ProjectRow).order_by(ProjectRow.created_at, ProjectRow.id)
                if workspace_id is not None:
                    query = query.where(ProjectRow.workspace_id == workspace_id)
                rows = list(session.scalars(query))
        except SQLAlchemyError as exc:
            raise ScopeStorageUnavailable() from exc
        return [projections.project_document(row) for row in rows]

    def get_run_events(self, run_id: str) -> list[dict[str, Any]]:
        with self.unit_of_work.session() as session:
            rows = list(
                session.scalars(
                    select(RunEventRow)
                    .where(RunEventRow.run_id == run_id)
                    .order_by(RunEventRow.sequence)
                )
            )
        return [projections.event_document(row) for row in rows]

    def get_experiment(self, revision_id: str) -> ExperimentRevisionRow:
        with self.unit_of_work.session() as session:
            row = session.get(ExperimentRevisionRow, revision_id)
            if row is None:
                raise KeyError(revision_id)
            session.expunge(row)
            return row

    def get_run(self, run_id: str) -> RunRow:
        with self.unit_of_work.session() as session:
            row = session.get(RunRow, run_id)
            if row is None:
                raise KeyError(run_id)
            session.expunge(row)
            return row

    def get_run_spec(self, run_spec_id: str) -> RunSpec:
        with self.unit_of_work.session() as session:
            row = session.get(RunSpecRow, run_spec_id)
            if row is None:
                raise KeyError(run_spec_id)
            spec = RunSpec.model_validate(json.loads(row.spec_json))
        if spec.digest != row.digest:
            raise ValueError(f"stored RunSpec digest mismatch: {run_spec_id}")
        return spec

    def get_admission_record(self, admission_id: str) -> AdmissionRecord:
        with self.unit_of_work.session() as session:
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
        with self.unit_of_work.session() as session:
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
        with self.unit_of_work.session() as session:
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
        with self.unit_of_work.session() as session:
            row = session.scalar(select(GradeRow).where(GradeRow.run_id == run_id))
            if row is None:
                raise KeyError(run_id)
            session.expunge(row)
            return row

    def get_comparison(self, comparison_id: str) -> ComparisonRow:
        with self.unit_of_work.session() as session:
            row = session.get(ComparisonRow, comparison_id)
            if row is None:
                raise KeyError(comparison_id)
            session.expunge(row)
            return row

    def get_subject_envelope(self, run_id: str) -> SubjectEnvelopeRecord:
        with self.unit_of_work.session() as session:
            row = session.get(SubjectEnvelopeRow, run_id)
            if row is None:
                raise KeyError(run_id)
            envelope = SubjectEnvelope.model_validate(json.loads(row.envelope_json))
            if envelope.digest != row.digest:
                raise ValueError("stored SubjectEnvelope digest mismatch")
            return SubjectEnvelopeRecord(
                run_id=run_id,
                envelope=envelope,
                created_at_utc=aware_utc(row.created_at),
            )

    def get_contract_revision(self, revision_id: str) -> RevisionEnvelope:
        with self.unit_of_work.session() as session:
            row = session.get(ContractRevisionRow, revision_id)
            if row is None:
                raise KeyError(revision_id)
            revision = parse_revision(json.loads(row.document_json))
        if revision.digest != row.digest:
            raise ValueError(f"stored contract digest mismatch: {revision_id}")
        return revision

    def get_contract_revision_by_ref(self, reference: ContractRef) -> RevisionEnvelope:
        with self.unit_of_work.session() as session:
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

    def list_contract_revisions(self, project_id: str | None = None) -> list[dict[str, Any]]:
        with self.unit_of_work.session() as session:
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

    def project_id_for_run(self, run_id: str) -> str:
        run = self.get_run(run_id)
        if run.run_spec_id is None:
            if run.experiment_revision_id is None:
                raise ValueError("Run has no project-bearing contract")
            return self.get_experiment(run.experiment_revision_id).project_id
        spec = self.get_run_spec(run.run_spec_id)
        return self.get_contract_revision_by_ref(spec.study_ref).project_id

    def project_id_for_run_spec(self, spec: RunSpec) -> str:
        return self.get_contract_revision_by_ref(spec.study_ref).project_id
