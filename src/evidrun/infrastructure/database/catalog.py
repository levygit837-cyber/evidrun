"""Top-level entity writes: one transaction per write.

Nothing here advances a Run lifecycle or appends a ledger event — those belong to
`ledger` and `queue`. What this aggregate does enforce is that a stored contract
matches the digest it claims, so a Run can never be created against a RunSpec or
AdmissionRecord that drifted after it was written.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from sqlalchemy import select

from evidrun.contracts import (
    AdmissionRecord,
    RunSpec,
    SubjectEnvelope,
    SubjectEnvelopeRecord,
    semantic_model_dump,
)
from evidrun.infrastructure.database import clock
from evidrun.infrastructure.database.models import (
    AdmissionRecordRow,
    ChatMessageRow,
    ChatSessionRow,
    ComparisonRow,
    ExperimentRevisionRow,
    ProjectRow,
    RunRow,
    RunSpecRow,
    SubjectEnvelopeRow,
    WorkspaceRow,
)
from evidrun.infrastructure.database.queue.fencing import validate_optional_lease
from evidrun.infrastructure.database.timestamps import aware_utc
from evidrun.infrastructure.database.unit_of_work import LeaseFence, UnitOfWork
from evidrun.shared.types import canonical_json, new_id, sha256_json

__all__ = ["CatalogStore"]


def _provider_resolution_matches(run_spec: RunSpec, record: AdmissionRecord) -> bool:
    """Allow an unresolved provider only when the rejection proves that failure."""

    requested = run_spec.agent_inventory.provider_profile_id
    resolved = record.resolved_inventory.provider_profile_id
    if resolved == requested:
        return True
    if requested is None or resolved is not None or record.decision != "rejected":
        return False
    return f"provider:{requested}" in record.missing_requirements and any(
        item.blocking
        and item.category == "provider"
        and item.subject_ref == requested
        and item.reason.code == "unavailable"
        for item in record.issues
    )


class CatalogStore:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self.unit_of_work = unit_of_work

    def create_workspace(self, name: str) -> WorkspaceRow:
        row = WorkspaceRow(id=new_id("ws"), name=name, created_at=clock.utc_now())
        with self.unit_of_work.session() as session:
            session.add(row)
            session.commit()
        return row

    def create_project(self, workspace_id: str, name: str) -> ProjectRow:
        row = ProjectRow(
            id=new_id("prj"), workspace_id=workspace_id, name=name, created_at=clock.utc_now()
        )
        with self.unit_of_work.session() as session:
            session.add(row)
            session.commit()
        return row

    def save_run_spec(self, spec: RunSpec) -> RunSpecRow:
        with self.unit_of_work.session() as session:
            existing = session.scalar(select(RunSpecRow).where(RunSpecRow.digest == spec.digest))
            if existing is not None:
                return existing
            row = RunSpecRow(
                id=new_id("rspec"),
                study_logical_id=spec.study_ref.logical_id,
                scenario_logical_id=spec.scenario_ref.logical_id,
                variant_id=spec.variant_id,
                repetition_index=spec.repetition_index,
                spec_json=canonical_json(semantic_model_dump(spec)),
                digest=spec.digest,
                created_at=clock.utc_now(),
            )
            session.add(row)
            session.commit()
            return row

    def save_admission_record(
        self, run_spec_id: str, record: AdmissionRecord
    ) -> AdmissionRecordRow:
        with self.unit_of_work.session() as session:
            spec = session.get(RunSpecRow, run_spec_id)
            if spec is None:
                raise KeyError(f"RunSpec not found: {run_spec_id}")
            if spec.digest != record.run_spec_digest:
                raise ValueError("admission digest does not match its RunSpec")
            run_spec = RunSpec.model_validate(json.loads(spec.spec_json))
            inventory = record.resolved_inventory
            if (
                inventory.requirement_ref != run_spec.agent_inventory_ref
                or inventory.runner_ref != run_spec.agent_inventory.runner_ref
                or not _provider_resolution_matches(run_spec, record)
            ):
                raise ValueError("admission inventory does not match the RunSpec requirements")
            requirements = run_spec.agent_inventory.capability_requirements
            if len(inventory.capabilities) != len(requirements):
                raise ValueError("admission must resolve every requested capability exactly once")
            for requirement, resolved in zip(requirements, inventory.capabilities, strict=True):
                if (
                    resolved.kind != requirement.kind
                    or resolved.requested_ref != requirement.capability_ref
                    or resolved.required != requirement.required
                    or resolved.exposure != requirement.exposure
                ):
                    raise ValueError("admission capability does not match its RunSpec requirement")
                if not set(resolved.effective_permissions).issubset(
                    requirement.requested_permissions
                ):
                    raise ValueError("admission capability escalates requested permissions")
                if not set(resolved.satisfied_authority_constraints).issubset(
                    requirement.authority_constraints
                ):
                    raise ValueError("admission capability substitutes authority constraints")
                if resolved.status == "resolved" and (
                    resolved.resolved_ref != requirement.capability_ref
                    or resolved.context_refs
                    != (
                        requirement.instruction_refs
                        if requirement.exposure in {"instructions", "instructions_and_schema"}
                        else ()
                    )
                    or resolved.effective_interface_version != requirement.minimum_interface_version
                    or set(resolved.satisfied_authority_constraints)
                    != set(requirement.authority_constraints)
                ):
                    raise ValueError(
                        "admission capability does not satisfy its interface or authority contract"
                    )
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
                record_json=canonical_json(semantic_model_dump(record)),
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
        with self.unit_of_work.session() as session:
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
                created_at=clock.utc_now(),
            )
            session.add(row)
            session.commit()
            return row

    def create_run(
        self,
        *,
        experiment_revision_id: str | None = None,
        variant_id: str,
        runner: str,
        objective: str,
        repetition: int = 1,
        run_spec_id: str | None = None,
        admission_id: str | None = None,
        retry_of: str | None = None,
    ) -> RunRow:
        if run_spec_id is None or admission_id is None:
            raise ValueError("new Runs require an exact RunSpec and AdmissionRecord")
        with self.unit_of_work.session() as session:
            spec_row = session.get(RunSpecRow, run_spec_id)
            admission_row = session.get(AdmissionRecordRow, admission_id)
            if spec_row is None or admission_row is None:
                raise ValueError("RunSpec or AdmissionRecord does not exist")
            spec = RunSpec.model_validate(json.loads(spec_row.spec_json))
            admission = AdmissionRecord.model_validate(json.loads(admission_row.record_json))
            if spec.digest != spec_row.digest or admission.digest != admission_row.digest:
                raise ValueError("Run contracts failed stored digest verification")
            if (
                admission_row.run_spec_id != spec_row.id
                or admission_row.decision != "admitted"
                or admission.decision != "admitted"
                or admission.run_spec_digest != spec.digest
            ):
                raise ValueError("Run requires an admitted record for the exact RunSpec")
            expected_identity = (
                spec.variant_id,
                spec.repetition_index,
                spec.agent_inventory.runner_ref.name,
                spec.goal.instruction,
            )
            received_identity = (variant_id, repetition, runner, objective)
            if received_identity != expected_identity:
                raise ValueError("Run identity must match its immutable RunSpec")
            if retry_of is not None and session.get(RunRow, retry_of) is None:
                raise ValueError("retry_of must reference an existing Run")
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
            created_at=clock.utc_now(),
        )
        with self.unit_of_work.session() as session:
            session.add(row)
            session.commit()
        return row

    def save_subject_envelope(
        self,
        run_id: str,
        envelope: SubjectEnvelope,
        *,
        lease: LeaseFence | None = None,
    ) -> SubjectEnvelopeRecord:
        created_at = clock.utc_now()
        with self.unit_of_work.session() as session:
            validate_optional_lease(session, lease=lease, run_id=run_id)
            run = session.get(RunRow, run_id)
            if run is None or run.run_spec_id is None:
                raise ValueError("SubjectEnvelope requires a canonical Run")
            spec = session.get(RunSpecRow, run.run_spec_id)
            if spec is None or spec.digest != envelope.run_spec_digest:
                raise ValueError("SubjectEnvelope does not match the RunSpec")
            existing = session.get(SubjectEnvelopeRow, run_id)
            if existing is not None:
                stored = SubjectEnvelope.model_validate(json.loads(existing.envelope_json))
                if stored.digest != existing.digest or stored != envelope:
                    raise ValueError("a different SubjectEnvelope already exists for the Run")
                return SubjectEnvelopeRecord(
                    run_id=run_id,
                    envelope=stored,
                    created_at_utc=aware_utc(existing.created_at),
                )
            session.add(
                SubjectEnvelopeRow(
                    run_id=run_id,
                    envelope_json=canonical_json(semantic_model_dump(envelope)),
                    digest=envelope.digest,
                    created_at=created_at,
                )
            )
            session.commit()
        return SubjectEnvelopeRecord(run_id=run_id, envelope=envelope, created_at_utc=created_at)

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
            created_at=clock.utc_now(),
        )
        with self.unit_of_work.session() as session:
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
            created_at=clock.utc_now(),
        )
        with self.unit_of_work.session() as session:
            session.add(row)
            session.commit()
        return row

    def add_chat_message(self, session_id: str, role: str, content: str) -> ChatMessageRow:
        row = ChatMessageRow(
            id=new_id("msg"),
            session_id=session_id,
            role=role,
            content=content,
            created_at=clock.utc_now(),
        )
        with self.unit_of_work.session() as session:
            session.add(row)
            session.commit()
        return row
