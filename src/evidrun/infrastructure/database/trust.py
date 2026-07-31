"""Append-only persistence for execution trust and canonical review targets."""

from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from evidrun.contracts import (
    ContractRef,
    ExecutionTrustRecord,
    ReviewTarget,
    RevisionDecisionRecord,
    RevisionEnvelope,
    RunSpec,
    parse_revision,
    semantic_model_dump,
    validate_execution_trust_lineage,
    validate_review_target_lineage,
    validate_verified_trust,
)
from evidrun.contracts.authority import HumanAttestationVerifier
from evidrun.infrastructure.database import clock
from evidrun.infrastructure.database.models import (
    ContractDecisionRow,
    ContractRevisionRow,
    ExecutionReviewTargetRow,
    ExecutionTrustRecordRow,
    ProjectRow,
    RunSpecRow,
)
from evidrun.infrastructure.database.unit_of_work import UnitOfWork
from evidrun.shared.types import canonical_json

__all__ = ["ExecutionReviewMaterial", "ExecutionTrustStore"]


@dataclass(frozen=True, slots=True)
class ExecutionReviewMaterial:
    target: ReviewTarget
    revisions: tuple[RevisionEnvelope, ...]
    run_specs: tuple[RunSpec, ...]
    trust_records: tuple[ExecutionTrustRecord, ...]


class ExecutionTrustStore:
    """Persist trust documents without turning a projection into authority."""

    def __init__(
        self,
        unit_of_work: UnitOfWork,
        human_attestation_verifier: HumanAttestationVerifier,
    ) -> None:
        self.unit_of_work = unit_of_work
        self._human_attestation_verifier = human_attestation_verifier

    def save_record(self, record: ExecutionTrustRecord) -> ExecutionTrustRecordRow:
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
                self._validate_verified_record(session, stored, verify_attestation=False)
                return existing
            collision = session.get(ExecutionTrustRecordRow, record.trust_id)
            if collision is not None:
                raise ValueError("execution trust id already has different content")
            self._validate_hydrated_lineage(session, record)
            self._validate_verified_record(session, record, verify_attestation=True)
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
            record = self._validate_record_row(row)
            self._validate_hydrated_lineage(session, record)
            self._validate_verified_record(session, record, verify_attestation=False)
            return record

    def get_verified_decisions(
        self, record: ExecutionTrustRecord
    ) -> tuple[RevisionDecisionRecord, ...]:
        """Read the exact persisted decisions bound by a verified trust record."""

        if record.kind == "unverified_revision_set":
            return ()
        with self.unit_of_work.session() as session:
            decisions = self._hydrate_bound_decisions(session, record)
            self._validate_bound_decisions(record, decisions)
            return decisions

    def verified_decisions_for(
        self, references: tuple[ContractRef, ...]
    ) -> tuple[RevisionDecisionRecord, ...] | None:
        """Return complete, current human coverage or no verified coverage at all."""

        with self.unit_of_work.session() as session:
            decisions: list[RevisionDecisionRecord] = []
            for reference in references:
                revision = session.scalar(
                    select(ContractRevisionRow).where(
                        ContractRevisionRow.contract_type
                        == reference.contract_type.value,
                        ContractRevisionRow.logical_id == reference.logical_id,
                        ContractRevisionRow.revision == reference.revision,
                    )
                )
                if revision is None or revision.digest != reference.digest:
                    raise ValueError("verified trust references an unknown revision")
                row = session.scalar(
                    select(ContractDecisionRow)
                    .where(ContractDecisionRow.contract_revision_id == revision.id)
                    .order_by(ContractDecisionRow.decided_at.desc())
                    .limit(1)
                )
                if row is None or row.decision != "accepted" or row.actor_type != "verified_human":
                    return None
                decision = self._validate_decision_row(row)
                if decision.revision_ref != reference or decision.decision != "accepted":
                    raise ValueError("stored human decision does not cover the exact revision")
                if decision.authority.kind != "verified_human":
                    raise ValueError("stored human decision authority was swapped")
                self._human_attestation_verifier.verify(
                    decision.authority.attestation,
                    expected_subject_digest=decision.human_subject_digest(),
                )
                decisions.append(decision)
            return tuple(decisions)

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
            for record in records:
                self._validate_verified_record(
                    session,
                    record,
                    verify_attestation=False,
                )
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

    def get_review_material(self, digest: str) -> ExecutionReviewMaterial:
        """Hydrate one persisted target without accepting caller-supplied refs."""

        with self.unit_of_work.session() as session:
            row = session.get(ExecutionReviewTargetRow, digest)
            if row is None:
                raise KeyError(digest)
            target = self._validate_target_row(row)
            record_rows = tuple(
                session.scalars(
                    select(ExecutionTrustRecordRow)
                    .where(
                        ExecutionTrustRecordRow.project_id == target.project_id,
                        ExecutionTrustRecordRow.revision_set_digest
                        == target.revision_set_digest,
                        ExecutionTrustRecordRow.run_spec_digest.in_(
                            target.run_spec_digests
                        ),
                    )
                    .order_by(
                        ExecutionTrustRecordRow.created_at,
                        ExecutionTrustRecordRow.id,
                    )
                )
            )
            first_by_spec: dict[str, ExecutionTrustRecord] = {}
            for record_row in record_rows:
                record = self._validate_record_row(record_row)
                self._validate_verified_record(
                    session,
                    record,
                    verify_attestation=False,
                )
                first_by_spec.setdefault(record.run_spec_digest, record)
            try:
                records = tuple(
                    first_by_spec[run_spec_digest]
                    for run_spec_digest in target.run_spec_digests
                )
            except KeyError as exc:
                raise ValueError(
                    "ReviewTarget trust records do not cover its RunSpecs"
                ) from exc
            revisions = self._hydrate_revisions(session, records[0].revision_refs)
            run_specs = tuple(
                self._hydrate_run_spec(session, run_spec_digest)
                for run_spec_digest in target.run_spec_digests
            )
            validate_review_target_lineage(target, records, run_specs, revisions)
            return ExecutionReviewMaterial(
                target=target,
                revisions=revisions,
                run_specs=run_specs,
                trust_records=records,
            )

    @classmethod
    def _validate_hydrated_lineage(
        cls, session: Session, record: ExecutionTrustRecord
    ) -> None:
        if session.get(ProjectRow, record.project_id) is None:
            raise ValueError("execution trust Project does not exist")
        run_spec = cls._hydrate_run_spec(session, record.run_spec_digest)
        revisions = cls._hydrate_revisions(session, record.revision_refs)
        validate_execution_trust_lineage(record, run_spec, revisions)

    def _validate_verified_record(
        self,
        session: Session,
        record: ExecutionTrustRecord,
        *,
        verify_attestation: bool,
    ) -> None:
        if record.kind == "unverified_revision_set":
            return
        decisions = self._hydrate_bound_decisions(session, record)
        if verify_attestation:
            validate_verified_trust(
                record,
                decisions,
                self._human_attestation_verifier,
            )
        else:
            self._validate_bound_decisions(record, decisions)

    @staticmethod
    def _validate_bound_decisions(
        record: ExecutionTrustRecord,
        decisions: tuple[RevisionDecisionRecord, ...],
    ) -> None:
        if len(decisions) != len(record.verified_decisions):
            raise ValueError("verified execution trust decision count is incomplete")
        for binding, decision in zip(
            record.verified_decisions, decisions, strict=True
        ):
            if (
                decision.revision_ref != binding.revision_ref
                or decision.digest != binding.decision_digest
                or decision.decision != "accepted"
                or decision.authority.kind != "verified_human"
            ):
                raise ValueError(
                    "verified execution trust binding does not match its human decision"
                )

    @classmethod
    def _hydrate_bound_decisions(
        cls, session: Session, record: ExecutionTrustRecord
    ) -> tuple[RevisionDecisionRecord, ...]:
        decisions: list[RevisionDecisionRecord] = []
        for binding in record.verified_decisions:
            row = session.scalar(
                select(ContractDecisionRow).where(
                    ContractDecisionRow.decision_digest == binding.decision_digest
                )
            )
            if row is None:
                raise ValueError("verified trust references an unknown decision")
            decision = cls._validate_decision_row(row)
            if decision.revision_ref != binding.revision_ref:
                raise ValueError("verified trust decision binding was swapped")
            decisions.append(decision)
        return tuple(decisions)

    @staticmethod
    def _validate_decision_row(row: ContractDecisionRow) -> RevisionDecisionRecord:
        decision = RevisionDecisionRecord.model_validate(json.loads(row.decision_json))
        if (
            decision.digest != row.decision_digest
            or decision.decision != row.decision
            or decision.authority.kind != row.actor_type
        ):
            raise ValueError("stored contract decision digest mismatch")
        return decision

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
