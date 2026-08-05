"""Persist instruction digests by Lab Agent turn.

Revision ID: 0009_lab_turn_instruction_digest
Revises: 0008_lab_agent_session_store
Create Date: 2026-08-05
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0009_lab_turn_instruction_digest"
down_revision: str | None = "0008_lab_agent_session_store"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if "chat_sessions" not in inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "lab_turn_instructions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("turn_sequence", sa.Integer(), nullable=False),
        sa.Column("instruction_digest", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.id"]),
    )
    op.create_index("ix_lab_turn_instructions_session_id", "lab_turn_instructions", ["session_id"])


def downgrade() -> None:
    if "lab_turn_instructions" not in inspect(op.get_bind()).get_table_names():
        return
    op.drop_index("ix_lab_turn_instructions_session_id", table_name="lab_turn_instructions")
    op.drop_table("lab_turn_instructions")
