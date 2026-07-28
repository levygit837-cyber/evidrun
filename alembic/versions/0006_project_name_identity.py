"""Add canonical Project name identity within each Workspace.

Revision ID: 0006_project_name_identity
Revises: 0005_workspace_name_identity
Create Date: 2026-07-27
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sqlalchemy import inspect

from evidrun.infrastructure.database.scope_schema import (
    PROJECT_NAME_CONSTRAINT,
    ensure_project_name_schema,
)

revision: str = "0006_project_name_identity"
down_revision: str | None = "0005_workspace_name_identity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    ensure_project_name_schema(op.get_bind())


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {item["name"] for item in inspector.get_columns("projects")}
    constraints = {item["name"] for item in inspector.get_unique_constraints("projects")}
    if "name_key" not in columns:
        return
    with op.batch_alter_table("projects") as batch:
        if PROJECT_NAME_CONSTRAINT in constraints:
            batch.drop_constraint(PROJECT_NAME_CONSTRAINT, type_="unique")
        batch.drop_column("name_key")
