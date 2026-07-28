"""Add explicit execution-trust and ReviewTarget persistence.

Revision ID: 0007_execution_trust_foundation
Revises: 0006_project_name_identity
Create Date: 2026-07-28
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0007_execution_trust_foundation"
down_revision: str | None = "0006_project_name_identity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    if "execution_trust_records" not in tables:
        op.create_table(
            "execution_trust_records",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("kind", sa.String(), nullable=False),
            sa.Column("project_id", sa.String(), nullable=False),
            sa.Column("study_logical_id", sa.String(), nullable=False),
            sa.Column("revision_set_digest", sa.String(length=64), nullable=False),
            sa.Column("run_spec_digest", sa.String(length=64), nullable=False),
            sa.Column("record_json", sa.Text(), nullable=False),
            sa.Column("digest", sa.String(length=64), nullable=False),
            sa.Column("semantic_digest", sa.String(length=64), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("digest"),
            sa.UniqueConstraint("semantic_digest"),
        )
        for name in (
            "kind",
            "project_id",
            "study_logical_id",
            "revision_set_digest",
            "run_spec_digest",
        ):
            op.create_index(f"ix_execution_trust_records_{name}", "execution_trust_records", [name])
    if "execution_review_targets" not in tables:
        op.create_table(
            "execution_review_targets",
            sa.Column("digest", sa.String(length=64), nullable=False),
            sa.Column("project_id", sa.String(), nullable=False),
            sa.Column("revision_set_digest", sa.String(length=64), nullable=False),
            sa.Column("target_json", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
            sa.PrimaryKeyConstraint("digest"),
        )
        op.create_index(
            "ix_execution_review_targets_project_id",
            "execution_review_targets",
            ["project_id"],
        )
        op.create_index(
            "ix_execution_review_targets_revision_set_digest",
            "execution_review_targets",
            ["revision_set_digest"],
        )
    _add_trust_columns("admission_records")
    _add_trust_columns("runs")


def _add_trust_columns(table: str) -> None:
    bind = op.get_bind()
    if table not in inspect(bind).get_table_names():
        return
    columns = {item["name"] for item in inspect(bind).get_columns(table)}
    with op.batch_alter_table(table) as batch:
        if "execution_trust_id" not in columns:
            batch.add_column(sa.Column("execution_trust_id", sa.String(), nullable=True))
            batch.create_foreign_key(
                f"fk_{table}_execution_trust",
                "execution_trust_records",
                ["execution_trust_id"],
                ["id"],
            )
        if "execution_trust_digest" not in columns:
            batch.add_column(
                sa.Column("execution_trust_digest", sa.String(length=64), nullable=True)
            )
    op.execute(
        f"CREATE INDEX IF NOT EXISTS ix_{table}_execution_trust_id "
        f"ON {table} (execution_trust_id)"
    )


def downgrade() -> None:
    bind = op.get_bind()
    for table in ("execution_trust_records", "execution_review_targets"):
        if table in inspect(bind).get_table_names():
            count = bind.execute(sa.text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
            if count:
                raise RuntimeError(
                    "cannot downgrade execution trust while canonical trust data exists"
                )
    for table in ("runs", "admission_records"):
        if table not in inspect(bind).get_table_names():
            continue
        op.execute(f"DROP INDEX IF EXISTS ix_{table}_execution_trust_id")
        columns = {item["name"] for item in inspect(bind).get_columns(table)}
        foreign_keys = {
            item["name"] for item in inspect(bind).get_foreign_keys(table) if item["name"]
        }
        with op.batch_alter_table(table) as batch:
            constraint = f"fk_{table}_execution_trust"
            if constraint in foreign_keys:
                batch.drop_constraint(constraint, type_="foreignkey")
            if "execution_trust_digest" in columns:
                batch.drop_column("execution_trust_digest")
            if "execution_trust_id" in columns:
                batch.drop_column("execution_trust_id")
    for table in ("execution_review_targets", "execution_trust_records"):
        if table in inspect(bind).get_table_names():
            op.drop_table(table)
