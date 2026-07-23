from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class WorkspaceRow(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False)


class ProjectRow(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
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


class AdmissionRecordRow(Base):
    __tablename__ = "admission_records"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_spec_id: Mapped[str] = mapped_column(ForeignKey("run_specs.id"), nullable=False, index=True)
    decision: Mapped[str] = mapped_column(String, nullable=False)
    record_json: Mapped[str] = mapped_column(Text, nullable=False)
    digest: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
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
    experiment_revision_id: Mapped[str] = mapped_column(
        ForeignKey("experiment_revisions.id"), nullable=False
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
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column()


class RunEventRow(Base):
    __tablename__ = "run_events"
    __table_args__ = (UniqueConstraint("run_id", "sequence", name="uq_run_event_sequence"),)

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


class ContextSnapshotRow(Base):
    __tablename__ = "context_snapshots"

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
    scope_type: Mapped[str | None] = mapped_column(String)
    scope_id: Mapped[str | None] = mapped_column(String)
    title: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False)


class ChatMessageRow(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("chat_sessions.id"), nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
