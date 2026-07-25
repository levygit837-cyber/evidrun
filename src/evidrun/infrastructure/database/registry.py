"""Contract revisions and the human decisions that accept them.

Authority is the invariant here: a decision that claims human authority is
verified in the same transaction that persists it, and `repository_fixture`
acceptance stays reachable only through the dedicated legacy import.
"""

from __future__ import annotations

import json

from sqlalchemy import func, select

from evidrun.contracts import (
    RevisionDecisionRecord,
    RevisionEnvelope,
    parse_revision,
    semantic_model_dump,
)
from evidrun.contracts.authority import HumanAttestationVerifier
from evidrun.contracts.legacy import LegacyStudyPackage
from evidrun.contracts.registry import InMemoryContractRegistry
from evidrun.infrastructure.database import clock
from evidrun.infrastructure.database.models import ContractDecisionRow, ContractRevisionRow
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
            raise ValueError("new contract revision status must be draft or proposed")
        document = revision.semantic_document()
        with self.unit_of_work.session() as session:
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
                created_at=clock.utc_now(),
            )
            session.add(row)
            session.commit()
            return row

    def decide_contract_revision(
        self, decision: RevisionDecisionRecord
    ) -> ContractDecisionRow:
        if decision.authority.kind == "repository_fixture":
            raise PermissionError(
                "repository fixture acceptance requires import_legacy_contract_package"
            )
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

    def _persist_contract_decision(
        self,
        decision: RevisionDecisionRecord,
        *,
        repository_fixture_digest: str | None = None,
    ) -> ContractDecisionRow:
        if decision.authority.kind == "verified_human":
            self.human_attestation_verifier.verify(
                decision.authority.attestation,
                expected_subject_digest=decision.human_subject_digest(),
            )
        elif repository_fixture_digest != decision.authority.fixture_digest:
            raise PermissionError(
                "repository fixture acceptance is restricted to the internal legacy adapter"
            )
        with self.unit_of_work.session() as session:
            revision = session.scalar(
                select(ContractRevisionRow).where(
                    ContractRevisionRow.contract_type == decision.revision_ref.contract_type.value,
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
                    if not (previous.decision == "accepted" and decision.decision == "superseded"):
                        raise ValueError("contract revision already has a conflicting decision")
                else:
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
