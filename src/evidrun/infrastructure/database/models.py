from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class WorkspaceRow(Base):
    __tablename__ = "workspaces"
    __table_args__ = (UniqueConstraint("name_key", name="uq_workspace_name_key"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    name_key: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False)


class ProjectRow(Base):
    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("workspace_id", "name_key", name="uq_project_workspace_name_key"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    name_key: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False)


class ContractRevisionRow(Base):
    __tablename__ = "contract_revisions"
    __table_args__ = (
        UniqueConstraint(
            "contract_type", "logical_id", "revision", name="uq_contract_revision_identity"
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    contract_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    logical_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="draft")
    document_json: Mapped[str] = mapped_column(Text, nullable=False)
    digest: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False)


class ContractDecisionRow(Base):
    __tablename__ = "contract_decisions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    contract_revision_id: Mapped[str] = mapped_column(
        ForeignKey("contract_revisions.id"), nullable=False, index=True
    )
    decision: Mapped[str] = mapped_column(String, nullable=False)
    actor_type: Mapped[str] = mapped_column(String, nullable=False)
    actor_id: Mapped[str] = mapped_column(String, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    decision_json: Mapped[str] = mapped_column(Text, nullable=False)
    decision_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(nullable=False)


class RunSpecRow(Base):
    __tablename__ = "run_specs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    study_logical_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    scenario_logical_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    variant_id: Mapped[str] = mapped_column(String, nullable=False)
    repetition_index: Mapped[int] = mapped_column(Integer, nullable=False)
    spec_json: Mapped[str] = mapped_column(Text, nullable=False)
    digest: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False)


class ExecutionTrustRecordRow(Base):
    __tablename__ = "execution_trust_records"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    kind: Mapped[str] = mapped_column(String, nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    study_logical_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    revision_set_digest: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    run_spec_digest: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    record_json: Mapped[str] = mapped_column(Text, nullable=False)
    digest: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    semantic_digest: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False)


class ExecutionReviewTargetRow(Base):
    __tablename__ = "execution_review_targets"

    digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    revision_set_digest: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False)


class AdmissionRecordRow(Base):
    __tablename__ = "admission_records"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_spec_id: Mapped[str] = mapped_column(ForeignKey("run_specs.id"), nullable=False, index=True)
    decision: Mapped[str] = mapped_column(String, nullable=False)
    record_json: Mapped[str] = mapped_column(Text, nullable=False)
    digest: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    execution_trust_id: Mapped[str | None] = mapped_column(
        ForeignKey("execution_trust_records.id"), nullable=True, index=True
    )
    execution_trust_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False)


class ExperimentRevisionRow(Base):
    __tablename__ = "experiment_revisions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    experiment_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    manifest_json: Mapped[str] = mapped_column(Text, nullable=False)
    manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False)


class RunRow(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    experiment_revision_id: Mapped[str | None] = mapped_column(
        ForeignKey("experiment_revisions.id"), nullable=True
    )
    variant_id: Mapped[str] = mapped_column(String, nullable=False)
    repetition: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String, nullable=False)
    runner: Mapped[str] = mapped_column(String, nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    output: Mapped[str | None] = mapped_column(Text)
    context_hash: Mapped[str | None] = mapped_column(String(64))
    retry_of: Mapped[str | None] = mapped_column(ForeignKey("runs.id"))
    run_spec_id: Mapped[str | None] = mapped_column(ForeignKey("run_specs.id"))
    admission_id: Mapped[str | None] = mapped_column(ForeignKey("admission_records.id"))
    execution_trust_id: Mapped[str | None] = mapped_column(
        ForeignKey("execution_trust_records.id"), nullable=True, index=True
    )
    execution_trust_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column()


class RunEventRow(Base):
    __tablename__ = "run_events"
    __table_args__ = (
        UniqueConstraint("run_id", "sequence", name="uq_run_event_sequence"),
        UniqueConstraint("run_id", "operation_key", name="uq_run_event_operation"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), nullable=False, index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(nullable=False)
    actor_type: Mapped[str] = mapped_column(String, nullable=False)
    actor_id: Mapped[str] = mapped_column(String, nullable=False)
    classification: Mapped[str] = mapped_column(String, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    correlation_id: Mapped[str] = mapped_column(String, nullable=False)
    causation_id: Mapped[str | None] = mapped_column(String)
    prev_event_hash: Mapped[str | None] = mapped_column(String(64))
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    operation_key: Mapped[str | None] = mapped_column(String, nullable=True)


class RunExecutionJobRow(Base):
    __tablename__ = "run_execution_jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    request_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    available_at: Mapped[datetime] = mapped_column(nullable=False, index=True)
    active_attempt_id: Mapped[str | None] = mapped_column(String, nullable=True)
    lease_generation: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column()
    rejection_code: Mapped[str | None] = mapped_column(String)


class RunExecutionAttemptRow(Base):
    __tablename__ = "run_execution_attempts"
    __table_args__ = (
        UniqueConstraint("job_id", "ordinal", name="uq_run_attempt_ordinal"),
        UniqueConstraint("job_id", "lease_generation", name="uq_run_attempt_generation"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    job_id: Mapped[str] = mapped_column(
        ForeignKey("run_execution_jobs.id"), nullable=False, index=True
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    worker_id: Mapped[str] = mapped_column(String, nullable=False)
    lease_generation: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)
    leased_at: Mapped[datetime] = mapped_column(nullable=False)
    lease_expires_at: Mapped[datetime] = mapped_column(nullable=False, index=True)
    last_heartbeat_at: Mapped[datetime] = mapped_column(nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column()
    reason_code: Mapped[str | None] = mapped_column(String)


class SubjectEnvelopeRow(Base):
    __tablename__ = "subject_envelopes"

    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), primary_key=True)
    envelope_json: Mapped[str] = mapped_column(Text, nullable=False)
    digest: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False)


class ContextSnapshotRow(Base):
    __tablename__ = "context_snapshots"
    __table_args__ = (UniqueConstraint("run_id", name="uq_context_snapshot_run"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), nullable=False, index=True)
    policy_id: Mapped[str] = mapped_column(String, nullable=False)
    strategy: Mapped[str] = mapped_column(String, nullable=False)
    max_chars: Mapped[int] = mapped_column(Integer, nullable=False)
    source_chars: Mapped[int] = mapped_column(Integer, nullable=False)
    selected_chars: Mapped[int] = mapped_column(Integer, nullable=False)
    selected_content: Mapped[str] = mapped_column(Text, nullable=False)
    omitted_json: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False)


class GradeRow(Base):
    __tablename__ = "grades"
    __table_args__ = (UniqueConstraint("run_id", "grader_id", name="uq_grade_run_grader"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), nullable=False, index=True)
    grader_id: Mapped[str] = mapped_column(String, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False)


class CheckpointRecordRow(Base):
    __tablename__ = "checkpoint_records"
    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "definition_id",
            "up_to_event_sequence",
            name="uq_checkpoint_record_boundary",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), nullable=False, index=True)
    definition_id: Mapped[str] = mapped_column(String, nullable=False)
    up_to_event_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    record_json: Mapped[str] = mapped_column(Text, nullable=False)
    checkpoint_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False)


class EvaluationRecordRow(Base):
    __tablename__ = "evaluation_records"
    __table_args__ = (
        UniqueConstraint("run_id", "stage_id", "source_type", name="uq_evaluation_stage_source"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    stage_id: Mapped[str] = mapped_column(String, nullable=False)
    record_json: Mapped[str] = mapped_column(Text, nullable=False)
    record_digest: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False)


class ComparisonRow(Base):
    __tablename__ = "comparisons"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    experiment_revision_id: Mapped[str] = mapped_column(
        ForeignKey("experiment_revisions.id"), nullable=False, index=True
    )
    baseline_run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), nullable=False)
    candidate_run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), nullable=False)
    primary_variable: Mapped[str] = mapped_column(String, nullable=False)
    validity: Mapped[str] = mapped_column(String, nullable=False)
    baseline_score: Mapped[float] = mapped_column(Float, nullable=False)
    candidate_score: Mapped[float] = mapped_column(Float, nullable=False)
    delta: Mapped[float] = mapped_column(Float, nullable=False)
    report_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False)


class ChatSessionRow(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    project_id: Mapped[str | None] = mapped_column(
        ForeignKey("projects.id"), nullable=True, index=True
    )
    focus_kind: Mapped[str | None] = mapped_column(String, nullable=True)
    focus_id: Mapped[str | None] = mapped_column(String, nullable=True)
    scope_type: Mapped[str | None] = mapped_column(String)
    scope_id: Mapped[str | None] = mapped_column(String)
    title: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False)


class ChatMessageRow(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (UniqueConstraint("session_id", "sequence", name="uq_chat_message_sequence"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("chat_sessions.id"), nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False)


class LabToolTraceRow(Base):
    __tablename__ = "lab_tool_traces"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("chat_sessions.id"), nullable=False, index=True
    )
    turn_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    tool_name: Mapped[str] = mapped_column(String, nullable=False)
    arguments_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_refs_json: Mapped[str] = mapped_column(Text, nullable=False)
    returned_refs_json: Mapped[str] = mapped_column(Text, nullable=False)
    outcome: Mapped[str] = mapped_column(String, nullable=False)
    refusal_code: Mapped[str | None] = mapped_column(String, nullable=True)
    scope_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
