"""Append-only persistence for execution trust and canonical review targets."""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from evidrun.contracts import (
    ContractRef,
    ExecutionTrustRecord,
    ReviewTarget,
    RevisionEnvelope,
    RunSpec,
    parse_revision,
    semantic_model_dump,
    validate_execution_trust_lineage,
    validate_review_target_lineage,
)
from evidrun.infrastructure.database import clock
from evidrun.infrastructure.database.models import (
    ContractRevisionRow,
    ExecutionReviewTargetRow,
    ExecutionTrustRecordRow,
    ProjectRow,
    RunSpecRow,
)
from evidrun.infrastructure.database.unit_of_work import UnitOfWork
from evidrun.shared.types import canonical_json

__all__ = ["ExecutionTrustStore"]


class ExecutionTrustStore:
    """Persist trust documents without turning a projection into authority."""

    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self.unit_of_work = unit_of_work

    def save_record(self, record: ExecutionTrustRecord) -> ExecutionTrustRecordRow:
        if record.kind != "unverified_revision_set":
            raise PermissionError(
                "verified execution trust requires validated human decisions"
            )
        with self.unit_of_work.session() as session:
            existing = session.scalar(
                select(ExecutionTrustRecordRow).where(
                    ExecutionTrustRecordRow.semantic_digest
                    == record.semantic_identity_digest
                )
            )
            if existing is not None:
                stored = self._validate_record_row(existing)
                self._validate_hydrated_lineage(session, stored)
                return existing
            collision = session.get(ExecutionTrustRecordRow, record.trust_id)
            if collision is not None:
                raise ValueError("execution trust id already has different content")
            self._validate_hydrated_lineage(session, record)
            row = ExecutionTrustRecordRow(
                id=record.trust_id,
                kind=record.kind,
                project_id=record.project_id,
                study_logical_id=record.study_ref.logical_id,
                revision_set_digest=record.revision_set_digest,
                run_spec_digest=record.run_spec_digest,
                record_json=canonical_json(semantic_model_dump(record)),
                digest=record.digest,
                semantic_digest=record.semantic_identity_digest,
                created_at=record.created_at_utc,
            )
            session.add(row)
            session.commit()
            return row

    def get_record(self, trust_id: str) -> ExecutionTrustRecord:
        with self.unit_of_work.session() as session:
            row = session.get(ExecutionTrustRecordRow, trust_id)
            if row is None:
                raise KeyError(trust_id)
            return self._validate_record_row(row)

    def save_review_target(self, target: ReviewTarget) -> ExecutionReviewTargetRow:
        digest = target.review_target_digest
        with self.unit_of_work.session() as session:
            existing = session.get(ExecutionReviewTargetRow, digest)
            if existing is not None:
                self._validate_target_row(existing)
                return existing
            if session.get(ProjectRow, target.project_id) is None:
                raise ValueError("ReviewTarget Project does not exist")
            run_specs = tuple(
                self._hydrate_run_spec(session, digest)
                for digest in target.run_spec_digests
            )
            record_rows = tuple(
                session.scalars(
                    select(ExecutionTrustRecordRow).where(
                        ExecutionTrustRecordRow.project_id == target.project_id,
                        ExecutionTrustRecordRow.revision_set_digest
                        == target.revision_set_digest,
                    )
                )
            )
            records = tuple(self._validate_record_row(row) for row in record_rows)
            if not records:
                raise ValueError("ReviewTarget requires execution trust records")
            revisions = self._hydrate_revisions(session, records[0].revision_refs)
            validate_review_target_lineage(target, records, run_specs, revisions)
            row = ExecutionReviewTargetRow(
                digest=digest,
                project_id=target.project_id,
                revision_set_digest=target.revision_set_digest,
                target_json=canonical_json(semantic_model_dump(target)),
                created_at=clock.utc_now(),
            )
            session.add(row)
            session.commit()
            return row

    def get_review_target(self, digest: str) -> ReviewTarget:
        with self.unit_of_work.session() as session:
            row = session.get(ExecutionReviewTargetRow, digest)
            if row is None:
                raise KeyError(digest)
            return self._validate_target_row(row)

    @classmethod
    def _validate_hydrated_lineage(
        cls, session: Session, record: ExecutionTrustRecord
    ) -> None:
        if session.get(ProjectRow, record.project_id) is None:
            raise ValueError("execution trust Project does not exist")
        run_spec = cls._hydrate_run_spec(session, record.run_spec_digest)
        revisions = cls._hydrate_revisions(session, record.revision_refs)
        validate_execution_trust_lineage(record, run_spec, revisions)

    @staticmethod
    def _hydrate_run_spec(session: Session, digest: str) -> RunSpec:
        row = session.scalar(select(RunSpecRow).where(RunSpecRow.digest == digest))
        if row is None:
            raise ValueError("execution trust RunSpec does not exist")
        run_spec = RunSpec.model_validate(json.loads(row.spec_json))
        if run_spec.digest != row.digest:
            raise ValueError("stored RunSpec digest mismatch")
        return run_spec

    @staticmethod
    def _hydrate_revisions(
        session: Session, references: tuple[ContractRef, ...]
    ) -> tuple[RevisionEnvelope, ...]:
        revisions: list[RevisionEnvelope] = []
        for reference in references:
            row = session.scalar(
                select(ContractRevisionRow).where(
                    ContractRevisionRow.contract_type == reference.contract_type.value,
                    ContractRevisionRow.logical_id == reference.logical_id,
                    ContractRevisionRow.revision == reference.revision,
                )
            )
            if row is None:
                raise ValueError("execution trust references an unknown revision")
            revision = parse_revision(json.loads(row.document_json))
            if row.digest != reference.digest or revision.ref != reference:
                raise ValueError("stored revision does not match its reference")
            revisions.append(revision)
        return tuple(revisions)

    @staticmethod
    def _validate_record_row(row: ExecutionTrustRecordRow) -> ExecutionTrustRecord:
        record = ExecutionTrustRecord.model_validate(json.loads(row.record_json))
        if (
            record.digest != row.digest
            or record.semantic_identity_digest != row.semantic_digest
            or record.trust_id != row.id
        ):
            raise ValueError("stored execution trust digest mismatch")
        return record

    @staticmethod
    def _validate_target_row(row: ExecutionReviewTargetRow) -> ReviewTarget:
        target = ReviewTarget.model_validate(json.loads(row.target_json))
        if target.review_target_digest != row.digest:
            raise ValueError("stored ReviewTarget digest mismatch")
        return target
