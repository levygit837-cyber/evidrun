from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import UTC
from typing import Any, cast

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
from evidrun.contracts.authority import (
    HumanAttestationVerifier,
    UnavailableHumanAttestationVerifier,
)
from evidrun.contracts.compiler import InMemoryContractRegistry
from evidrun.contracts.legacy import LegacyStudyPackage
from evidrun.contracts.runtime import (
    EVENT_ALLOWED_RUN_STATUSES,
    UNSUPPORTED_RUNTIME_EVENT_TYPES,
)
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
    def __init__(
        self,
        database: Database,
        human_attestation_verifier: HumanAttestationVerifier | None = None,
    ):
        self.database = database
        self.human_attestation_verifier = (
            human_attestation_verifier or UnavailableHumanAttestationVerifier()
        )

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
        self,
        decision: RevisionDecisionRecord,
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
        allowed_identities = {
            ("goal", "crl-ctx-002-context-policy-goal", 1),
            ("scenario", "crl-ctx-002", 1),
            ("agent_inventory", "crl-ctx-002-context-policy-agent", 1),
            ("workspace_template", "crl-ctx-002-context-policy-workspace", 1),
            ("interaction_protocol", "crl-ctx-002-context-policy-interaction", 1),
            ("evaluation_plan", "crl-ctx-002-context-policy-evaluation", 1),
            ("study", "crl-ctx-002-context-policy", 1),
        }
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
            or package_identities != allowed_identities
            or decision_refs != expected_refs
            or package.study.logical_id != "crl-ctx-002-context-policy"
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
                actor_type=decision.authority.kind,
                actor_id=(
                    decision.authority.principal_id
                    if decision.authority.kind == "verified_human"
                    else decision.authority.fixture_id
                ),
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
            run_spec = RunSpec.model_validate(json.loads(spec.spec_json))
            inventory = record.resolved_inventory
            if (
                inventory.requirement_ref != run_spec.agent_inventory_ref
                or inventory.runner_ref != run_spec.agent_inventory.runner_ref
                or inventory.provider_profile_id
                != run_spec.agent_inventory.provider_profile_id
            ):
                raise ValueError("admission inventory does not match the RunSpec requirements")
            requirements = run_spec.agent_inventory.capability_requirements
            if len(inventory.capabilities) != len(requirements):
                raise ValueError("admission must resolve every requested capability exactly once")
            for requirement, resolved in zip(
                requirements, inventory.capabilities, strict=True
            ):
                if (
                    resolved.kind != requirement.kind
                    or resolved.requested_ref != requirement.capability_ref
                    or resolved.required != requirement.required
                    or resolved.exposure != requirement.exposure
                ):
                    raise ValueError(
                        "admission capability does not match its RunSpec requirement"
                    )
                if not set(resolved.effective_permissions).issubset(
                    requirement.requested_permissions
                ):
                    raise ValueError("admission capability escalates requested permissions")
                if not set(resolved.satisfied_authority_constraints).issubset(
                    requirement.authority_constraints
                ):
                    raise ValueError(
                        "admission capability substitutes authority constraints"
                    )
                if resolved.status == "resolved" and (
                    resolved.resolved_ref != requirement.capability_ref
                    or resolved.context_refs
                    != (
                        requirement.instruction_refs
                        if requirement.exposure
                        in {"instructions", "instructions_and_schema"}
                        else ()
                    )
                    or resolved.effective_interface_version
                    != requirement.minimum_interface_version
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
        if run_spec_id is None or admission_id is None:
            raise ValueError("new Runs require an exact RunSpec and AdmissionRecord")
        with self.database.session() as session:
            spec_row = session.get(RunSpecRow, run_spec_id)
            admission_row = session.get(AdmissionRecordRow, admission_id)
            if spec_row is None or admission_row is None:
                raise ValueError("RunSpec or AdmissionRecord does not exist")
            spec = RunSpec.model_validate(json.loads(spec_row.spec_json))
            admission = AdmissionRecord.model_validate(
                json.loads(admission_row.record_json)
            )
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
        output: str | None = None,
        context_hash: str | None = None,
    ) -> RunRow:
        with self.database.session() as session:
            row = session.get(RunRow, run_id)
            if row is None:
                raise KeyError(f"Run not found: {run_id}")
            if output is not None:
                row.output = output
            if context_hash is not None:
                row.context_hash = context_hash
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
        allowed_actor_types = {
            "system",
            "subject",
            "evaluator",
            "tool",
            "skill",
            "observer",
        }
        if actor_type not in allowed_actor_types:
            raise ValueError(
                "Run events cannot claim human authority without a typed attestation flow"
            )
        if not actor_id.strip():
            raise ValueError("Run event actor_id cannot be empty")
        if event_type in UNSUPPORTED_RUNTIME_EVENT_TYPES:
            raise ValueError(
                "Run event type is reserved until its coordinator/runtime is implemented"
            )
        normalized_payload = normalize_event_payload(event_type, dict(payload))
        with self.database.session() as session:
            run = session.get(RunRow, run_id)
            if run is None:
                raise KeyError(f"Run not found: {run_id}")
            prior_events = list(
                session.scalars(
                    select(RunEventRow)
                    .where(RunEventRow.run_id == run_id)
                    .order_by(RunEventRow.sequence)
                )
            )
            last = prior_events[-1] if prior_events else None
            if run.status in {
                "completed",
                "failed",
                "cancelled",
                "budget_exhausted",
                "guardrail_stopped",
            }:
                raise ValueError(
                    "no Run events may be appended after a terminal lifecycle event"
                )
            allowed_statuses = EVENT_ALLOWED_RUN_STATUSES.get(event_type)
            if allowed_statuses is not None and run.status not in allowed_statuses:
                raise ValueError(
                    f"{event_type} is not valid while the Run is {run.status}"
                )
            prior_event_types = [item.event_type for item in prior_events]
            if event_type == "subject.invoked" and prior_event_types.count(
                "subject.invoked"
            ) != prior_event_types.count("subject.responded"):
                raise ValueError("Subject invocation requires the prior turn to be complete")
            if event_type == "subject.responded" and prior_event_types.count(
                "subject.invoked"
            ) != prior_event_types.count("subject.responded") + 1:
                raise ValueError("Subject response requires one unmatched Subject invocation")
            if event_type == "run.evaluating" and "subject.responded" not in prior_event_types:
                raise ValueError("Run cannot enter evaluation before a Subject response")
            if event_type == "evaluation.completed":
                evaluation_id = str(normalized_payload["evaluation_record_id"])
                evaluation = session.get(EvaluationRecordRow, evaluation_id)
                if (
                    evaluation is None
                    or evaluation.run_id != run_id
                    or evaluation.record_digest
                    != normalized_payload["evaluation_record_digest"]
                    or json.loads(evaluation.record_json).get("gate_status")
                    != normalized_payload["gate_status"]
                ):
                    raise ValueError(
                        "evaluation.completed requires the exact persisted EvaluationRecord"
                    )
                if any(
                    item.event_type == "evaluation.completed"
                    and json.loads(item.payload_json).get("evaluation_record_id")
                    == evaluation_id
                    for item in prior_events
                ):
                    raise ValueError("EvaluationRecord already has a completion event")
            if event_type == "run.queued":
                if run.run_spec_id is None or run.admission_id is None:
                    raise ValueError("run.queued requires canonical Run contracts")
                spec_row = session.get(RunSpecRow, run.run_spec_id)
                admission_row = session.get(AdmissionRecordRow, run.admission_id)
                if spec_row is None or admission_row is None:
                    raise ValueError("run.queued references missing Run contracts")
                if (
                    normalized_payload.get("run_spec_digest") != spec_row.digest
                    or normalized_payload.get("admission_digest") != admission_row.digest
                ):
                    raise ValueError("run.queued contract digests do not match the RunRecord")
            if event_type == "context.composed":
                snapshot = session.get(
                    ContextSnapshotRow, str(normalized_payload["snapshot_id"])
                )
                if (
                    snapshot is None
                    or snapshot.run_id != run_id
                    or snapshot.policy_id != normalized_payload["policy_id"]
                    or snapshot.strategy != normalized_payload["strategy"]
                    or snapshot.content_hash != normalized_payload["content_hash"]
                    or snapshot.source_chars != normalized_payload["source_chars"]
                    or snapshot.selected_chars != normalized_payload["selected_chars"]
                    or bool(json.loads(snapshot.omitted_json))
                    != normalized_payload["omitted"]
                ):
                    raise ValueError(
                        "context.composed requires the exact persisted ContextSnapshot"
                    )
                if run.run_spec_id is None:
                    raise ValueError("context.composed requires a canonical RunSpec")
                context_spec_row = session.get(RunSpecRow, run.run_spec_id)
                if context_spec_row is None:
                    raise ValueError("context.composed references a missing RunSpec")
                context_spec = RunSpec.model_validate(
                    json.loads(context_spec_row.spec_json)
                )
                if (
                    context_spec.context_policy is None
                    or context_spec.context_policy.id != snapshot.policy_id
                    or context_spec.context_policy.strategy != snapshot.strategy
                ):
                    raise ValueError(
                        "ContextSnapshot policy does not match the admitted RunSpec"
                    )
            if event_type == "subject.responded":
                if run.run_spec_id is None:
                    raise ValueError("Subject response requires a canonical RunSpec")
                response_spec_row = session.get(RunSpecRow, run.run_spec_id)
                if response_spec_row is None:
                    raise ValueError("Subject response references a missing RunSpec")
                response_spec = RunSpec.model_validate(
                    json.loads(response_spec_row.spec_json)
                )
                if (
                    normalized_payload.get("capture_mode")
                    != response_spec.capture_policy.default_mode
                ):
                    raise ValueError(
                        "Subject response capture mode does not match the RunSpec policy"
                    )
            if event_type in {
                "run.completed",
                "run.failed",
                "run.cancelled",
                "run.budget_exhausted",
                "run.guardrail_stopped",
            }:
                if run.run_spec_id is None:
                    raise ValueError("terminal event requires a canonical RunSpec")
                terminal_spec_row = session.get(RunSpecRow, run.run_spec_id)
                if terminal_spec_row is None:
                    raise ValueError("terminal event references a missing RunSpec")
                terminal_spec = RunSpec.model_validate(
                    json.loads(terminal_spec_row.spec_json)
                )
                goal_result = cast(
                    Mapping[str, object], normalized_payload["goal_result"]
                )
                if goal_result.get("goal_mode") != terminal_spec.goal.mode:
                    raise ValueError(
                        "terminal Goal result mode does not match the RunSpec Goal"
                    )
                if goal_result.get("goal_mode") == "bounded_exploration":
                    declared_stop = goal_result.get("stop_condition_kind")
                    if declared_stop not in {
                        item.kind for item in terminal_spec.stop_conditions
                    }:
                        raise ValueError(
                            "bounded exploration terminal references an undeclared stop condition"
                        )
                evaluation_refs = cast(
                    list[object],
                    normalized_payload.get("evaluation_record_refs", []),
                )
                persisted_evaluation_ids = set(
                    session.scalars(
                        select(EvaluationRecordRow.id).where(
                            EvaluationRecordRow.run_id == run_id
                        )
                    )
                )
                if {str(item) for item in evaluation_refs} != persisted_evaluation_ids:
                    raise ValueError(
                        "terminal event must reference every persisted EvaluationRecord exactly"
                    )
                if event_type == "run.completed" and (
                    "subject.responded" not in prior_event_types or not evaluation_refs
                ):
                    raise ValueError(
                        "completed Run requires a Subject response and evaluation records"
                    )
                referenced_evaluations: list[EvaluationRecord] = []
                for evaluation_id in evaluation_refs:
                    evaluation = session.get(
                        EvaluationRecordRow, str(evaluation_id)
                    )
                    if evaluation is None or evaluation.run_id != run_id:
                        raise ValueError(
                            "terminal event references an evaluation outside the Run"
                        )
                    referenced_evaluations.append(
                        EvaluationRecord.model_validate(
                            json.loads(evaluation.record_json)
                        )
                    )
                    if not any(
                        item.event_type == "evaluation.completed"
                        and json.loads(item.payload_json).get("evaluation_record_id")
                        == str(evaluation_id)
                        and json.loads(item.payload_json).get(
                            "evaluation_record_digest"
                        )
                        == evaluation.record_digest
                        for item in prior_events
                    ):
                        raise ValueError(
                            "terminal evaluation ref has no matching completion event"
                        )
                if event_type == "run.completed":
                    gate_results = EvaluationValidator.gate_results(
                        terminal_spec.evaluation_plan,
                        referenced_evaluations,
                    )
                    required_stages = EvaluationValidator.stages_visible_after_gates(
                        terminal_spec.evaluation_plan,
                        gate_results,
                    )
                    if not set(required_stages).issubset(gate_results):
                        raise ValueError(
                            "completed Run does not cover the required EvaluationPlan stages"
                        )
                if terminal_spec.evaluation_plan.human_adjudication_policy.required:
                    referenced_records = [
                        session.get(EvaluationRecordRow, str(evaluation_id))
                        for evaluation_id in evaluation_refs
                    ]
                    if not any(
                        record is not None
                        and record.source_type == "human_adjudicator"
                        for record in referenced_records
                    ):
                        raise ValueError(
                            "terminal event requires the planned verified human adjudication"
                        )
                checkpoint_refs = cast(
                    list[object], normalized_payload.get("checkpoint_refs", [])
                )
                for checkpoint_id in checkpoint_refs:
                    checkpoint = session.get(CheckpointRecordRow, str(checkpoint_id))
                    if checkpoint is None or checkpoint.run_id != run_id:
                        raise ValueError(
                            "terminal event references a checkpoint outside the Run"
                        )
            next_status = self._event_transition(
                run=run,
                event_type=event_type,
                payload=normalized_payload,
                has_prior_event=last is not None,
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
            if next_status is not None:
                run.status = next_status
                if next_status in {
                    "completed",
                    "failed",
                    "cancelled",
                    "budget_exhausted",
                    "guardrail_stopped",
                }:
                    run.completed_at = occurred_at
            session.commit()
            return row

    @staticmethod
    def _event_transition(
        *,
        run: RunRow,
        event_type: str,
        payload: Mapping[str, object],
        has_prior_event: bool,
    ) -> str | None:
        terminal_states = {
            "completed",
            "failed",
            "cancelled",
            "budget_exhausted",
            "guardrail_stopped",
        }
        if run.status in terminal_states:
            raise ValueError("no Run events may be appended after a terminal lifecycle event")
        transition: dict[str, tuple[frozenset[str], str]] = {
            "run.preparing": (frozenset({"queued"}), "preparing"),
            "run.running": (frozenset({"preparing"}), "running"),
            "run.paused": (frozenset({"running"}), "paused"),
            "run.resumed": (frozenset({"paused"}), "running"),
            "run.evaluating": (frozenset({"running"}), "evaluating"),
            "run.completed": (frozenset({"evaluating"}), "completed"),
            "run.failed": (
                frozenset({"queued", "preparing", "running", "paused", "evaluating"}),
                "failed",
            ),
            "run.cancelled": (
                frozenset({"queued", "preparing", "running", "paused", "evaluating"}),
                "cancelled",
            ),
            "run.budget_exhausted": (
                frozenset({"queued", "preparing", "running", "paused", "evaluating"}),
                "budget_exhausted",
            ),
            "run.guardrail_stopped": (
                frozenset({"queued", "preparing", "running", "paused", "evaluating"}),
                "guardrail_stopped",
            ),
        }
        if not has_prior_event and event_type != "run.queued":
            raise ValueError("run.queued must be the first Run event")
        if event_type == "run.queued":
            if has_prior_event or run.status != "queued":
                raise ValueError("run.queued must be the first lifecycle event")
            if payload.get("run_id") != run.id or payload.get("variant_id") != run.variant_id:
                raise ValueError("run.queued identity does not match the RunRecord")
            return None
        rule = transition.get(event_type)
        if rule is None:
            return None
        allowed_from, target = rule
        if run.status not in allowed_from:
            raise ValueError(
                f"invalid Run lifecycle transition: {run.status} -> {target}"
            )
        declared_from = payload.get("from_status")
        if declared_from is not None and declared_from != run.status:
            raise ValueError("Run lifecycle payload has an incorrect from_status")
        declared_terminal = payload.get("status")
        if declared_terminal is not None and declared_terminal != target:
            raise ValueError("terminal event type and payload status do not match")
        return target

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
        if record.source_type in {"human_reviewer", "human_adjudicator"}:
            if record.human_attestation is None:
                raise ValueError("human evaluation requires attestation evidence")
            self.human_attestation_verifier.verify(
                record.human_attestation,
                expected_subject_digest=record.human_subject_digest(),
            )
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
            stage = next(
                item
                for item in spec.evaluation_plan.stages
                if item.id == record.stage_id
            )
            boundary_event: RunEventRow | None = None
            boundary_checkpoint: CheckpointRecordRow | None = None
            if record.boundary.up_to_event_sequence is not None:
                boundary_event = session.scalar(
                    select(RunEventRow).where(
                        RunEventRow.run_id == record.run_id,
                        RunEventRow.sequence
                        == record.boundary.up_to_event_sequence,
                    )
                )
            if record.boundary.checkpoint_id is not None:
                boundary_checkpoint = session.get(
                    CheckpointRecordRow, record.boundary.checkpoint_id
                )
            if stage.trigger.kind == "event":
                if (
                    boundary_event is None
                    or boundary_event.event_type != stage.trigger.reference
                ):
                    raise ValueError("evaluation boundary does not satisfy its event trigger")
            elif stage.trigger.kind == "checkpoint":
                if boundary_checkpoint is None:
                    raise ValueError(
                        "evaluation checkpoint trigger requires a checkpoint boundary"
                    )
                if stage.trigger.reference is not None:
                    checkpoint = CheckpointRecord.model_validate(
                        json.loads(boundary_checkpoint.record_json)
                    )
                    if checkpoint.definition_id != stage.trigger.reference:
                        raise ValueError(
                            "evaluation boundary does not satisfy its checkpoint trigger"
                        )
            elif stage.trigger.kind == "run_terminal" and (
                boundary_event is None
                or boundary_event.event_type
                not in {
                    "run.completed",
                    "run.failed",
                    "run.cancelled",
                    "run.budget_exhausted",
                    "run.guardrail_stopped",
                }
            ):
                raise ValueError(
                    "run-terminal evaluation requires a terminal event boundary"
                )
            max_evidence_sequence = (
                boundary_event.sequence
                if boundary_event is not None
                else boundary_checkpoint.up_to_event_sequence
                if boundary_checkpoint is not None
                else 0
            )
            for dimension in record.dimension_values:
                for evidence_ref in dimension.evidence_refs:
                    scheme, target = evidence_ref.ref.split(":", 1)
                    if scheme == "run" and target != record.run_id:
                        raise ValueError("evaluation evidence references a different Run")
                    if scheme == "event":
                        evidence_event = session.get(RunEventRow, target)
                        if (
                            evidence_event is None
                            or evidence_event.run_id != record.run_id
                            or evidence_event.sequence > max_evidence_sequence
                        ):
                            raise ValueError(
                                "evaluation evidence event is outside its authorized boundary"
                            )
            existing = session.scalar(
                select(EvaluationRecordRow).where(
                    EvaluationRecordRow.record_digest == record.digest
                )
            )
            if existing is not None:
                return existing
            related_records: list[tuple[EvaluationRecord, int]] = []

            def related_boundary_sequence(related: EvaluationRecord) -> int:
                if related.boundary.up_to_event_sequence is not None:
                    return related.boundary.up_to_event_sequence
                checkpoint_id = related.boundary.checkpoint_id
                checkpoint = (
                    session.get(CheckpointRecordRow, checkpoint_id)
                    if checkpoint_id is not None
                    else None
                )
                if checkpoint is None or checkpoint.run_id != record.run_id:
                    raise ValueError(
                        "related evaluation record has an unverifiable boundary"
                    )
                return checkpoint.up_to_event_sequence

            if record.source_type == "human_adjudicator":
                if record.relation is None or record.relation.kind != "adjudicates":
                    raise ValueError("human adjudication requires explicit target records")
                adjudication_policy = spec.evaluation_plan.human_adjudication_policy
                if (
                    not adjudication_policy.required
                    or record.stage_id
                    not in adjudication_policy.adjudicable_stage_ids
                    or record.evaluator_ref != adjudication_policy.adjudicator_ref
                    or record.human_attestation is None
                    or record.human_attestation.verifier_ref
                    != adjudication_policy.attestation_verifier_ref
                ):
                    raise ValueError(
                        "human adjudication is not authorized by the EvaluationPlan"
                    )
                for target_ref in record.relation.target_record_refs:
                    target = session.get(EvaluationRecordRow, target_ref)
                    if target is None or target.run_id != record.run_id:
                        raise ValueError(
                            "human adjudication target must belong to the same Run"
                        )
                    target_record = EvaluationRecord.model_validate(
                        json.loads(target.record_json)
                    )
                    if (
                        target_record.plan_ref != record.plan_ref
                        or target_record.stage_id != record.stage_id
                    ):
                        raise ValueError(
                            "human adjudication target must use the same plan and stage"
                        )
                    related_records.append(
                        (target_record, related_boundary_sequence(target_record))
                    )
            if record.source_type == "human_reviewer":
                if record.relation is None or record.relation.kind != "independent_review":
                    raise ValueError("human review requires an independent review relation")
                for considered_ref in record.relation.considers_record_refs:
                    considered = session.get(EvaluationRecordRow, considered_ref)
                    if considered is None or considered.run_id != record.run_id:
                        raise ValueError(
                            "human review can only consider records from the same Run"
                        )
                    considered_record = EvaluationRecord.model_validate(
                        json.loads(considered.record_json)
                    )
                    related_records.append(
                        (
                            considered_record,
                            related_boundary_sequence(considered_record),
                        )
                    )
            EvaluationValidator.validate_human_relation_boundary(
                record,
                boundary_sequence=max_evidence_sequence,
                related_records=related_records,
            )
            prior_rows = list(
                session.scalars(
                    select(EvaluationRecordRow)
                    .where(EvaluationRecordRow.run_id == record.run_id)
                    .order_by(EvaluationRecordRow.id)
                )
            )
            prior_records = [
                EvaluationRecord.model_validate(json.loads(prior.record_json))
                for prior in prior_rows
            ]
            if record.source_type == "human_adjudicator" and any(
                prior.stage_id == record.stage_id
                and prior.source_type == "human_adjudicator"
                for prior in prior_records
            ):
                raise ValueError("v1 permits only one human adjudication per stage")
            prior_gate_results = EvaluationValidator.gate_results(
                spec.evaluation_plan,
                prior_records,
            )
            visible_stages = EvaluationValidator.stages_visible_after_gates(
                spec.evaluation_plan, prior_gate_results
            )
            if record.stage_id not in visible_stages:
                raise ValueError("evaluation stage is blocked by a failed hard gate")
            if record.source_type != "human_adjudicator" and any(
                prior.stage_id == record.stage_id
                and prior.source_type == record.source_type
                for prior in prior_rows
            ):
                raise ValueError(
                    "evaluation stage already has a record from this source type"
                )
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
            if record.replayability == "deterministic":
                raise ValueError(
                    "deterministic checkpoint replayability is unsupported in this runtime"
                )
            expected_definition_digest = sha256_json(semantic_model_dump(definition))
            if record.definition_digest != expected_definition_digest:
                raise ValueError("checkpoint definition digest does not match the RunSpec")
            validation_refs = tuple(item.validator_ref for item in record.validations)
            if set(validation_refs) != set(definition.validator_refs) or len(
                validation_refs
            ) != len(definition.validator_refs):
                raise ValueError(
                    "checkpoint validations must match the definition validators"
                )
            boundary_event = session.scalar(
                select(RunEventRow).where(
                    RunEventRow.run_id == record.run_id,
                    RunEventRow.sequence == record.up_to_event_sequence,
                )
            )
            if boundary_event is None:
                raise ValueError("checkpoint boundary event is missing")
            trigger = definition.trigger
            if trigger.kind == "event" and boundary_event.event_type != trigger.event_type:
                raise ValueError("checkpoint boundary does not satisfy its event trigger")
            if trigger.kind not in {"manual", "event"}:
                raise ValueError(
                    "checkpoint trigger is representable but unsupported by this runtime"
                )
            capture = definition.capture
            capture_pairs = (
                (capture.context_snapshot, bool(record.context_snapshot_refs), "context snapshot"),
                (capture.protocol_state, record.protocol_state_ref is not None, "protocol state"),
                (
                    capture.artifact_manifest,
                    record.artifact_manifest_ref is not None,
                    "artifact manifest",
                ),
                (
                    capture.workspace_snapshot,
                    record.workspace_snapshot_ref is not None,
                    "workspace snapshot",
                ),
                (
                    capture.evaluation_records,
                    bool(record.evaluation_record_refs),
                    "evaluation records",
                ),
            )
            for requested, present, label in capture_pairs:
                if requested != present:
                    raise ValueError(
                        f"checkpoint {label} capture does not match its definition"
                    )
            admission_capture = capture.provider_resolution or capture.agent_inventory
            if admission_capture != (record.admission_record_id is not None):
                raise ValueError(
                    "checkpoint admission capture does not match provider/inventory request"
                )
            if record.admission_record_id is not None:
                admission_row = session.get(
                    AdmissionRecordRow, record.admission_record_id
                )
                if (
                    admission_row is None
                    or admission_row.id != run.admission_id
                    or admission_row.digest != record.admission_record_digest
                ):
                    raise ValueError(
                        "checkpoint admission capture does not belong to the Run"
                    )
            for snapshot_id in record.context_snapshot_refs:
                snapshot = session.get(ContextSnapshotRow, snapshot_id)
                if snapshot is None or snapshot.run_id != record.run_id:
                    raise ValueError(
                        "checkpoint context snapshot does not belong to the Run"
                    )
            for evaluation_id in record.evaluation_record_refs:
                evaluation = session.get(EvaluationRecordRow, evaluation_id)
                if evaluation is None or evaluation.run_id != record.run_id:
                    raise ValueError(
                        "checkpoint evaluation record does not belong to the Run"
                    )
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
