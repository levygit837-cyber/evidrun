"""Add verifiable human authority tables (ADR 0015).

Revision ID: 0003_human_authority
Revises: 0001_contract_foundation
Create Date: 2026-07-23

NOTE (rebase): the Run Kernel worktree introduces 0002. When rebasing onto it,
repoint ``down_revision`` to that head so history stays linear (or add a merge
revision if two heads exist). These tables are independent of Run Kernel tables.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0003_human_authority"
down_revision: str | None = "0001_contract_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    if "human_credentials" not in tables:
        op.create_table(
            "human_credentials",
            sa.Column("credential_id", sa.String(), primary_key=True),
            sa.Column("principal_id", sa.String(), nullable=False, index=True),
            sa.Column("display_name", sa.String(), nullable=False),
            sa.Column("public_key_pem", sa.Text(), nullable=False),
            sa.Column("relying_party_id", sa.String(), nullable=False),
            sa.Column("origin", sa.String(), nullable=False),
            sa.Column("sign_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(), nullable=False, server_default="active"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
        )
    if "human_challenges" not in tables:
        op.create_table(
            "human_challenges",
            sa.Column("challenge_id", sa.String(), primary_key=True),
            sa.Column("challenge_digest", sa.String(length=64), nullable=False, index=True),
            sa.Column("principal_id", sa.String(), nullable=False, index=True),
            sa.Column("credential_id", sa.String(), nullable=False, index=True),
            sa.Column("action", sa.String(), nullable=False),
            sa.Column("intent_json", sa.Text(), nullable=False),
            sa.Column("issued_at", sa.DateTime(), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("consumed_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    for table in ("human_challenges", "human_credentials"):
        if table in tables:
            op.drop_table(table)
