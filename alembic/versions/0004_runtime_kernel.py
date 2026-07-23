"""Add the durable generic Run execution kernel.

Revision ID: 0004_runtime_kernel
Revises: 0003_human_authority
Create Date: 2026-07-23
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0004_runtime_kernel"
down_revision: str | None = "0003_human_authority"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    if "run_execution_jobs" not in tables:
        op.create_table(
            "run_execution_jobs",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("run_id", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("idempotency_key", sa.String(), nullable=False),
            sa.Column("request_digest", sa.String(length=64), nullable=False),
            sa.Column("available_at", sa.DateTime(), nullable=False),
            sa.Column("active_attempt_id", sa.String(), nullable=True),
            sa.Column("lease_generation", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.Column("rejection_code", sa.String(), nullable=True),
            sa.ForeignKeyConstraint(["run_id"], ["runs.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("idempotency_key"),
            sa.UniqueConstraint("run_id"),
        )
        op.create_index(
            "ix_run_execution_jobs_available_at",
            "run_execution_jobs",
            ["available_at"],
        )
        op.create_index(
            "ix_run_execution_jobs_status",
            "run_execution_jobs",
            ["status"],
        )
    if "run_execution_attempts" not in tables:
        op.create_table(
            "run_execution_attempts",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("job_id", sa.String(), nullable=False),
            sa.Column("ordinal", sa.Integer(), nullable=False),
            sa.Column("worker_id", sa.String(), nullable=False),
            sa.Column("lease_generation", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("leased_at", sa.DateTime(), nullable=False),
            sa.Column("lease_expires_at", sa.DateTime(), nullable=False),
            sa.Column("last_heartbeat_at", sa.DateTime(), nullable=False),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.Column("reason_code", sa.String(), nullable=True),
            sa.ForeignKeyConstraint(["job_id"], ["run_execution_jobs.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("job_id", "lease_generation", name="uq_run_attempt_generation"),
            sa.UniqueConstraint("job_id", "ordinal", name="uq_run_attempt_ordinal"),
        )
        op.create_index(
            "ix_run_execution_attempts_job_id",
            "run_execution_attempts",
            ["job_id"],
        )
        op.create_index(
            "ix_run_execution_attempts_lease_expires_at",
            "run_execution_attempts",
            ["lease_expires_at"],
        )
        op.create_index(
            "ix_run_execution_attempts_status",
            "run_execution_attempts",
            ["status"],
        )
    if "subject_envelopes" not in tables:
        op.create_table(
            "subject_envelopes",
            sa.Column("run_id", sa.String(), nullable=False),
            sa.Column("envelope_json", sa.Text(), nullable=False),
            sa.Column("digest", sa.String(length=64), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["run_id"], ["runs.id"]),
            sa.PrimaryKeyConstraint("run_id"),
        )
        op.create_index("ix_subject_envelopes_digest", "subject_envelopes", ["digest"])

    inspector = inspect(bind)
    event_columns = {item["name"] for item in inspector.get_columns("run_events")}
    if "operation_key" not in event_columns:
        op.add_column("run_events", sa.Column("operation_key", sa.String(), nullable=True))
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_run_event_operation "
        "ON run_events (run_id, operation_key)"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_context_snapshot_run ON context_snapshots (run_id)"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_evaluation_stage_source "
        "ON evaluation_records (run_id, stage_id, source_type)"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_grade_run_grader ON grades (run_id, grader_id)"
    )
    run_columns = {item["name"]: item for item in inspector.get_columns("runs")}
    if run_columns["experiment_revision_id"].get("nullable") is False:
        with op.batch_alter_table("runs") as batch:
            batch.alter_column(
                "experiment_revision_id",
                existing_type=sa.String(),
                nullable=True,
            )


def downgrade() -> None:
    bind = op.get_bind()
    study_native_runs = bind.execute(
        sa.text("SELECT COUNT(*) FROM runs WHERE experiment_revision_id IS NULL")
    ).scalar_one()
    if study_native_runs:
        raise RuntimeError(
            "cannot downgrade runtime kernel while Study-native Runs have no legacy "
            "experiment_revision_id"
        )
    for table in (
        "subject_envelopes",
        "run_execution_attempts",
        "run_execution_jobs",
    ):
        op.drop_table(table)
    with op.batch_alter_table("runs") as batch:
        batch.alter_column("experiment_revision_id", existing_type=sa.String(), nullable=False)
    with op.batch_alter_table("run_events") as batch:
        batch.drop_column("operation_key")
