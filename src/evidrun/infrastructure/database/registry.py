"""Contract revisions and the human decisions that accept them.

Authority is the invariant here: a decision that claims human authority is
verified in the same transaction that persists it, and `repository_fixture`
acceptance stays reachable only through the dedicated legacy import.
"""

from __future__ import annotations

import json
import logging

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from evidrun.contracts import (
    RevisionDecisionRecord,
    RevisionEnvelope,
    parse_revision,
    semantic_model_dump,
)
from evidrun.contracts.authority import (
    HumanAttestationUnavailable,
    HumanAttestationVerifier,
)
from evidrun.contracts.legacy import LegacyStudyPackage
from evidrun.contracts.registry import InMemoryContractRegistry
from evidrun.infrastructure.database import clock
from evidrun.infrastructure.database.decide_errors import (
    decide_decision_conflict,
    decide_human_authority_unavailable,
    decide_repository_fixture_forbidden,
    decide_revision_not_found,
)
from evidrun.infrastructure.database.models import (
    ContractDecisionRow,
    ContractRevisionRow,
    ProjectRow,
)
from evidrun.infrastructure.database.register_errors import (
    RegisterRejected,
    RegisterStorageUnavailable,
    immutability_conflict,
    initial_status_invalid,
    project_not_found,
    revision_not_monotonic,
)
from evidrun.infrastructure.database.unit_of_work import UnitOfWork
from evidrun.shared.types import canonical_json, new_id

__all__ = ["ContractRegistryStore"]

LEGACY_PACKAGE_IDENTITIES = {
    ("goal", "crl-ctx-002-context-policy-goal", 1),
    ("scenario", "crl-ctx-002", 1),
    ("agent_inventory", "crl-ctx-002-context-policy-agent", 1),
    ("workspace_template", "crl-ctx-002-context-policy-workspace", 1),
    ("interaction_protocol", "crl-ctx-002-context-policy-interaction", 1),
    ("evaluation_plan", "crl-ctx-002-context-policy-evaluation", 1),
    ("study", "crl-ctx-002-context-policy", 1),
}
LEGACY_PACKAGE_STUDY_ID = "crl-ctx-002-context-policy"
logger = logging.getLogger(__name__)


class ContractRegistryStore:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
        human_attestation_verifier: HumanAttestationVerifier,
    ) -> None:
        self.unit_of_work = unit_of_work
        self.human_attestation_verifier = human_attestation_verifier

    def save_contract_revision(
        self, revision: RevisionEnvelope, *, status: str = "draft"
    ) -> ContractRevisionRow:
        if status not in {"draft", "proposed"}:
            raise initial_status_invalid()
        document = revision.semantic_document()
        try:
            with self.unit_of_work.immediate() as session:
                existing = session.scalar(
                    select(ContractRevisionRow).where(
                        ContractRevisionRow.contract_type == revision.ref.contract_type.value,
                        ContractRevisionRow.logical_id == revision.logical_id,
                        ContractRevisionRow.revision == revision.revision,
                    )
                )
                if existing is not None:
                    return self._resolve_existing_revision(
                        existing,
                        revision=revision,
                        document=document,
                        status=status,
                        session=session,
                    )
                latest_revision = session.scalar(
                    select(func.max(ContractRevisionRow.revision)).where(
                        ContractRevisionRow.contract_type == revision.ref.contract_type.value,
                        ContractRevisionRow.logical_id == revision.logical_id,
                    )
                )
                expected_revision = (latest_revision or 0) + 1
                if revision.revision != expected_revision:
                    raise revision_not_monotonic(
                        expected=expected_revision, received=revision.revision
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
                    created_at=clock.utc_now(),
                )
                session.add(row)
                try:
                    session.commit()
                except IntegrityError as exc:
                    session.rollback()
                    logger.exception("contract revision registration failed")
                    return self._recover_integrity_error(
                        session,
                        revision=revision,
                        document=document,
                        status=status,
                        cause=exc,
                    )
                return row
        except (RegisterRejected, RegisterStorageUnavailable):
            raise
        except SQLAlchemyError as exc:
            logger.exception("contract revision storage unavailable")
            raise RegisterStorageUnavailable() from exc

    def _recover_integrity_error(
        self,
        session: Session,
        *,
        revision: RevisionEnvelope,
        document: dict[str, object],
        status: str,
        cause: IntegrityError,
    ) -> ContractRevisionRow:
        if session.get(ProjectRow, revision.project_id) is None:
            raise project_not_found() from cause
        existing = session.scalar(
            select(ContractRevisionRow).where(
                ContractRevisionRow.contract_type == revision.ref.contract_type.value,
                ContractRevisionRow.logical_id == revision.logical_id,
                ContractRevisionRow.revision == revision.revision,
            )
        )
        if existing is None:
            raise RegisterStorageUnavailable() from cause
        return self._resolve_existing_revision(
            existing, revision=revision, document=document, status=status, session=session
        )

    @staticmethod
    def _resolve_existing_revision(
        existing: ContractRevisionRow,
        *,
        revision: RevisionEnvelope,
        document: dict[str, object],
        status: str,
        session: Session,
    ) -> ContractRevisionRow:
        if existing.digest != revision.digest or existing.document_json != canonical_json(document):
            raise immutability_conflict()
        if existing.status == "draft" and status == "proposed":
            existing.status = "proposed"
            session.commit()
        return existing

    def decide_contract_revision(
        self, decision: RevisionDecisionRecord
    ) -> ContractDecisionRow:
        if decision.authority.kind == "repository_fixture":
            raise decide_repository_fixture_forbidden()
        return self._persist_contract_decision(decision)

    def import_legacy_contract_package(
        self, package: LegacyStudyPackage
    ) -> tuple[ContractDecisionRow, ...]:
        decisions = package.acceptance_decisions()
        package_identities = {
            (
                revision.ref.contract_type.value,
                revision.ref.logical_id,
                revision.ref.revision,
            )
            for revision in package.revisions
        }
        expected_refs = {
            (
                revision.ref.contract_type.value,
                revision.ref.logical_id,
                revision.ref.revision,
                revision.ref.digest,
            )
            for revision in package.revisions
        }
        decision_refs = {
            (
                decision.revision_ref.contract_type.value,
                decision.revision_ref.logical_id,
                decision.revision_ref.revision,
                decision.revision_ref.digest,
            )
            for decision in decisions
        }
        if (
            not decisions
            or package_identities != LEGACY_PACKAGE_IDENTITIES
            or decision_refs != expected_refs
            or package.study.logical_id != LEGACY_PACKAGE_STUDY_ID
            or any(
                decision.authority.kind != "repository_fixture"
                or decision.authority.fixture_digest != package.fixture_digest
                for decision in decisions
            )
        ):
            raise ValueError("legacy package decisions do not cover the exact package digest")
        for revision in package.revisions:
            self.save_contract_revision(revision)
        return tuple(
            self._persist_contract_decision(
                decision,
                repository_fixture_digest=package.fixture_digest,
            )
            for decision in decisions
        )

    def _authorize_decision(
        self,
        decision: RevisionDecisionRecord,
        *,
        repository_fixture_digest: str | None,
    ) -> None:
        """Establish authority, or refuse by name without writing anything."""

        if decision.authority.kind == "verified_human":
            try:
                self.human_attestation_verifier.verify(
                    decision.authority.attestation,
                    expected_subject_digest=decision.human_subject_digest(),
                )
            except HumanAttestationUnavailable as exc:
                # Naming the refusal does not relax it: no verifier means nothing is
                # persisted, exactly as before. Only the cause becomes readable.
                raise decide_human_authority_unavailable() from exc
        elif repository_fixture_digest != decision.authority.fixture_digest:
            raise decide_repository_fixture_forbidden()

    def _persist_contract_decision(
        self,
        decision: RevisionDecisionRecord,
        *,
        repository_fixture_digest: str | None = None,
    ) -> ContractDecisionRow:
        with self.unit_of_work.session() as session:
            revision = session.scalar(
                select(ContractRevisionRow).where(
                    ContractRevisionRow.contract_type == decision.revision_ref.contract_type.value,
                    ContractRevisionRow.logical_id == decision.revision_ref.logical_id,
                    ContractRevisionRow.revision == decision.revision_ref.revision,
                )
            )
            if revision is None or revision.digest != decision.revision_ref.digest:
                raise decide_revision_not_found()
            # Authority is established inside the transaction that persists the decision,
            # and only after the revision is known to exist.
            self._authorize_decision(
                decision, repository_fixture_digest=repository_fixture_digest
            )
            previous = session.scalar(
                select(ContractDecisionRow)
                .where(ContractDecisionRow.contract_revision_id == revision.id)
                .order_by(ContractDecisionRow.decided_at.desc())
                .limit(1)
            )
            if previous is None and decision.decision == "superseded":
                raise decide_decision_conflict()
            if previous is not None:
                if previous.decision != decision.decision:
                    if not (previous.decision == "accepted" and decision.decision == "superseded"):
                        raise decide_decision_conflict()
                elif not (
                    previous.actor_type == "repository_fixture"
                    and decision.authority.kind == "verified_human"
                    and decision.decision == "accepted"
                ):
                    return previous
            row = ContractDecisionRow(
                id=new_id("cdec"),
                contract_revision_id=revision.id,
                decision=decision.decision,
                actor_type=decision.authority.kind,
                actor_id=(
                    decision.authority.principal_id
                    if decision.authority.kind == "verified_human"
                    else decision.authority.fixture_id
                ),
                rationale=decision.rationale,
                decision_json=canonical_json(semantic_model_dump(decision)),
                decision_digest=decision.digest,
                decided_at=decision.decided_at_utc,
            )
            revision.status = decision.decision
            session.add(row)
            session.commit()
            return row

    def contract_registry(self, project_id: str | None = None) -> InMemoryContractRegistry:
        with self.unit_of_work.session() as session:
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
        registry = InMemoryContractRegistry(
            self.human_attestation_verifier,
            allow_repository_fixture=True,
        )
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
