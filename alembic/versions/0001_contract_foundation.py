"""Add immutable Study/Run contract storage.

Revision ID: 0001_contract_foundation
Revises:
Create Date: 2026-07-22
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

from evidrun.infrastructure.database.models import Base

revision: str = "0001_contract_foundation"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the complete local baseline, then add columns missing from legacy Runs."""
    bind = op.get_bind()
    Base.metadata.create_all(bind)
    columns = {item["name"] for item in inspect(bind).get_columns("runs")}
    if "run_spec_id" not in columns:
        op.add_column("runs", sa.Column("run_spec_id", sa.String(), nullable=True))
    if "admission_id" not in columns:
        op.add_column("runs", sa.Column("admission_id", sa.String(), nullable=True))
    contract_columns = {
        item["name"] for item in inspect(bind).get_columns("contract_revisions")
    }
    if "status" not in contract_columns:
        op.add_column(
            "contract_revisions",
            sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        )


def downgrade() -> None:
    """Remove only the contract foundation; legacy Evidrun tables remain intact."""
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    with op.batch_alter_table("runs") as batch:
        columns = {item["name"] for item in inspect(bind).get_columns("runs")}
        if "admission_id" in columns:
            batch.drop_column("admission_id")
        if "run_spec_id" in columns:
            batch.drop_column("run_spec_id")
    for table in (
        "evaluation_records",
        "checkpoint_records",
        "admission_records",
        "run_specs",
        "contract_decisions",
        "contract_revisions",
    ):
        if table in tables:
            op.drop_table(table)
