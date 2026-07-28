"""Add canonical Workspace name identity.

Revision ID: 0005_workspace_name_identity
Revises: 0004_runtime_kernel
Create Date: 2026-07-27
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sqlalchemy import inspect

from evidrun.infrastructure.database.scope_schema import (
    WORKSPACE_NAME_CONSTRAINT,
    ensure_workspace_name_schema,
)

revision: str = "0005_workspace_name_identity"
down_revision: str | None = "0004_runtime_kernel"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    ensure_workspace_name_schema(op.get_bind())


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {item["name"] for item in inspector.get_columns("workspaces")}
    constraints = {
        item["name"] for item in inspector.get_unique_constraints("workspaces")
    }
    if "name_key" not in columns:
        return
    with op.batch_alter_table("workspaces") as batch:
        if WORKSPACE_NAME_CONSTRAINT in constraints:
            batch.drop_constraint(WORKSPACE_NAME_CONSTRAINT, type_="unique")
        batch.drop_column("name_key")
