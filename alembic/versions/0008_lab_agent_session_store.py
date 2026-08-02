"""Add typed Lab Agent session, message ordering and tool traces.

Revision ID: 0008_lab_agent_session_store
Revises: 0007_execution_trust_foundation
Create Date: 2026-08-02
"""

from __future__ import annotations

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import Connection, RowMapping, inspect

from evidrun.infrastructure.database.lab_errors import LabSessionMigrationError

revision: str = "0008_lab_agent_session_store"
down_revision: str | None = "0007_execution_trust_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_VALID_FOCUS_KINDS = frozenset({"study", "run", "comparison"})
_VALID_ROLES = frozenset({"human", "agent", "system_note"})


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    if "chat_sessions" not in tables or "chat_messages" not in tables:
        return
    _add_nullable_columns(bind)
    _migrate_sessions(bind)
    _migrate_messages(bind)
    _install_constraints(bind)
    _create_tool_traces(bind)


def _add_nullable_columns(bind: Connection) -> None:
    session_columns = {item["name"] for item in inspect(bind).get_columns("chat_sessions")}
    with op.batch_alter_table("chat_sessions") as batch:
        if "project_id" not in session_columns:
            batch.add_column(sa.Column("project_id", sa.String(), nullable=True))
        if "focus_kind" not in session_columns:
            batch.add_column(sa.Column("focus_kind", sa.String(), nullable=True))
        if "focus_id" not in session_columns:
            batch.add_column(sa.Column("focus_id", sa.String(), nullable=True))
    message_columns = {item["name"] for item in inspect(bind).get_columns("chat_messages")}
    if "sequence" not in message_columns:
        op.add_column("chat_messages", sa.Column("sequence", sa.Integer(), nullable=True))


def _migrate_sessions(bind: Connection) -> None:
    columns = {item["name"] for item in inspect(bind).get_columns("chat_sessions")}
    legacy = {"scope_type", "scope_id"} <= columns
    selected = "id, workspace_id, project_id, focus_kind, focus_id"
    if legacy:
        selected += ", scope_type, scope_id"
    rows = bind.execute(sa.text(f"SELECT {selected} FROM chat_sessions ORDER BY id")).mappings()
    for row in rows:
        values = _typed_scope(bind, row, legacy=legacy)
        bind.execute(
            sa.text(
                "UPDATE chat_sessions SET project_id=:project_id, "
                "focus_kind=:focus_kind, focus_id=:focus_id WHERE id=:id"
            ),
            {"id": row["id"], **values},
        )


def _typed_scope(bind: Connection, row: RowMapping, *, legacy: bool) -> dict[str, str | None]:
    row_id = str(row["id"])
    workspace_id = str(row["workspace_id"])
    if not _exists(bind, "workspaces", id=workspace_id):
        raise LabSessionMigrationError(f"chat_sessions references unknown Workspace; id={row_id}")
    typed_values = (row["project_id"], row["focus_kind"], row["focus_id"])
    if not legacy or any(value is not None for value in typed_values):
        return _validate_existing_typed_scope(bind, row)
    scope_type = row["scope_type"]
    scope_id = row["scope_id"]
    if scope_type is None and scope_id is None:
        return {"project_id": None, "focus_kind": None, "focus_id": None}
    if scope_type == "project" and scope_id is not None:
        _require_project(bind, str(scope_id), workspace_id, row_id)
        return {"project_id": str(scope_id), "focus_kind": None, "focus_id": None}
    if scope_type in _VALID_FOCUS_KINDS and scope_id is not None:
        project_id = _project_for_focus(bind, str(scope_type), str(scope_id), row_id)
        _require_project(bind, project_id, workspace_id, row_id)
        return {
            "project_id": project_id,
            "focus_kind": str(scope_type),
            "focus_id": str(scope_id),
        }
    raise LabSessionMigrationError(f"chat_sessions contains ambiguous legacy scope; id={row_id}")


def _validate_existing_typed_scope(bind: Connection, row: RowMapping) -> dict[str, str | None]:
    row_id = str(row["id"])
    workspace_id = str(row["workspace_id"])
    project_id = None if row["project_id"] is None else str(row["project_id"])
    focus_kind = None if row["focus_kind"] is None else str(row["focus_kind"])
    focus_id = None if row["focus_id"] is None else str(row["focus_id"])
    if (focus_kind is None) != (focus_id is None):
        raise LabSessionMigrationError(f"chat_sessions contains incomplete focus; id={row_id}")
    if focus_kind is not None and (focus_kind not in _VALID_FOCUS_KINDS or project_id is None):
        raise LabSessionMigrationError(f"chat_sessions contains invalid focus; id={row_id}")
    if project_id is not None:
        _require_project(bind, project_id, workspace_id, row_id)
    if focus_kind is not None:
        actual = _project_for_focus(bind, focus_kind, focus_id or "", row_id)
        if actual != project_id:
            raise LabSessionMigrationError(
                f"chat_sessions focus belongs to another Project; id={row_id}"
            )
    return {"project_id": project_id, "focus_kind": focus_kind, "focus_id": focus_id}


def _require_project(bind: Connection, project_id: str, workspace_id: str, row_id: str) -> None:
    project = (
        bind.execute(sa.text("SELECT workspace_id FROM projects WHERE id=:id"), {"id": project_id})
        .mappings()
        .first()
    )
    if project is None or str(project["workspace_id"]) != workspace_id:
        raise LabSessionMigrationError(
            f"chat_sessions scope does not resolve inside its Workspace; id={row_id}"
        )


def _project_for_focus(bind: Connection, kind: str, focus_id: str, row_id: str) -> str:
    if kind == "study":
        row = (
            bind.execute(
                sa.text(
                    "SELECT project_id FROM contract_revisions "
                    "WHERE id=:id AND contract_type='study'"
                ),
                {"id": focus_id},
            )
            .mappings()
            .first()
        )
    elif kind == "comparison":
        row = (
            bind.execute(
                sa.text(
                    "SELECT er.project_id FROM comparisons c "
                    "JOIN experiment_revisions er ON er.id=c.experiment_revision_id "
                    "WHERE c.id=:id"
                ),
                {"id": focus_id},
            )
            .mappings()
            .first()
        )
    else:
        row = _project_for_run(bind, focus_id, row_id)
    if row is None:
        raise LabSessionMigrationError(
            f"chat_sessions focus does not resolve to an entity; id={row_id}"
        )
    if isinstance(row, str):
        return row
    return str(row["project_id"])


def _project_for_run(bind: Connection, focus_id: str, row_id: str) -> str | None:
    run = (
        bind.execute(
            sa.text("SELECT experiment_revision_id, run_spec_id FROM runs WHERE id=:id"),
            {"id": focus_id},
        )
        .mappings()
        .first()
    )
    if run is None:
        return None
    candidates: set[str] = set()
    if run["experiment_revision_id"] is not None:
        experiment = (
            bind.execute(
                sa.text("SELECT project_id FROM experiment_revisions WHERE id=:id"),
                {"id": run["experiment_revision_id"]},
            )
            .mappings()
            .first()
        )
        if experiment is not None:
            candidates.add(str(experiment["project_id"]))
    if run["run_spec_id"] is not None:
        spec = (
            bind.execute(
                sa.text("SELECT spec_json FROM run_specs WHERE id=:id"),
                {"id": run["run_spec_id"]},
            )
            .mappings()
            .first()
        )
        if spec is not None:
            candidates.add(_project_from_spec(bind, str(spec["spec_json"]), row_id))
    if len(candidates) != 1:
        raise LabSessionMigrationError(
            f"chat_sessions Run focus has ambiguous Project lineage; id={row_id}"
        )
    return candidates.pop()


def _project_from_spec(bind: Connection, spec_json: str, row_id: str) -> str:
    try:
        reference = json.loads(spec_json)["study_ref"]
        params = {
            "logical_id": str(reference["logical_id"]),
            "revision": int(reference["revision"]),
        }
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise LabSessionMigrationError(
            f"chat_sessions RunSpec has invalid Study ref; id={row_id}"
        ) from exc
    study = (
        bind.execute(
            sa.text(
                "SELECT project_id FROM contract_revisions WHERE contract_type='study' "
                "AND logical_id=:logical_id AND revision=:revision"
            ),
            params,
        )
        .mappings()
        .first()
    )
    if study is None:
        raise LabSessionMigrationError(f"chat_sessions RunSpec Study does not resolve; id={row_id}")
    return str(study["project_id"])


def _migrate_messages(bind: Connection) -> None:
    sessions = bind.execute(sa.text("SELECT id FROM chat_sessions ORDER BY id")).scalars()
    for session_id in sessions:
        rows = bind.execute(
            sa.text(
                "SELECT id, role, content FROM chat_messages WHERE session_id=:session_id "
                "ORDER BY created_at, id"
            ),
            {"session_id": session_id},
        ).mappings()
        for sequence, row in enumerate(rows, start=1):
            role = str(row["role"])
            content = str(row["content"])
            if role not in _VALID_ROLES:
                content = f"[legacy role: {role}]\n{content}"
                role = "system_note"
            bind.execute(
                sa.text(
                    "UPDATE chat_messages SET role=:role, content=:content, sequence=:sequence "
                    "WHERE id=:id"
                ),
                {"id": row["id"], "role": role, "content": content, "sequence": sequence},
            )


def _install_constraints(bind: Connection) -> None:
    message_constraints = {
        item["name"] for item in inspect(bind).get_unique_constraints("chat_messages")
    }
    with op.batch_alter_table("chat_messages") as batch:
        batch.alter_column("sequence", existing_type=sa.Integer(), nullable=False)
        if "uq_chat_message_sequence" not in message_constraints:
            batch.create_unique_constraint("uq_chat_message_sequence", ["session_id", "sequence"])
    session_foreign_keys = inspect(bind).get_foreign_keys("chat_sessions")
    has_project_foreign_key = any(
        item.get("constrained_columns") == ["project_id"]
        and item.get("referred_table") == "projects"
        and item.get("referred_columns") == ["id"]
        for item in session_foreign_keys
    )
    session_indexes = {item["name"] for item in inspect(bind).get_indexes("chat_sessions")}
    with op.batch_alter_table("chat_sessions") as batch:
        if not has_project_foreign_key:
            batch.create_foreign_key(
                "fk_chat_sessions_project_id_projects", "projects", ["project_id"], ["id"]
            )
        if "ix_chat_sessions_workspace_id" not in session_indexes:
            batch.create_index("ix_chat_sessions_workspace_id", ["workspace_id"], unique=False)
        if "ix_chat_sessions_project_id" not in session_indexes:
            batch.create_index("ix_chat_sessions_project_id", ["project_id"], unique=False)


def _create_tool_traces(bind: Connection) -> None:
    if "lab_tool_traces" in inspect(bind).get_table_names():
        return
    op.create_table(
        "lab_tool_traces",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("turn_sequence", sa.Integer(), nullable=False),
        sa.Column("tool_name", sa.String(), nullable=False),
        sa.Column("arguments_digest", sa.String(64), nullable=False),
        sa.Column("requested_refs_json", sa.Text(), nullable=False),
        sa.Column("returned_refs_json", sa.Text(), nullable=False),
        sa.Column("outcome", sa.String(), nullable=False),
        sa.Column("refusal_code", sa.String(), nullable=True),
        sa.Column("scope_snapshot_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.id"]),
    )
    op.create_index("ix_lab_tool_traces_session_id", "lab_tool_traces", ["session_id"])


def _exists(bind: Connection, table: str, **where: object) -> bool:
    clause = " AND ".join(f"{key}=:{key}" for key in where)
    return bind.execute(sa.text(f"SELECT 1 FROM {table} WHERE {clause}"), where).first() is not None


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    if "lab_tool_traces" in tables:
        op.drop_index("ix_lab_tool_traces_session_id", table_name="lab_tool_traces")
        op.drop_table("lab_tool_traces")
    if "chat_messages" in tables and "sequence" in {
        item["name"] for item in inspect(bind).get_columns("chat_messages")
    }:
        with op.batch_alter_table("chat_messages") as batch:
            batch.drop_constraint("uq_chat_message_sequence", type_="unique")
            batch.drop_column("sequence")
    if "chat_sessions" in tables:
        columns = {item["name"] for item in inspect(bind).get_columns("chat_sessions")}
        indexes = {item["name"] for item in inspect(bind).get_indexes("chat_sessions")}
        if "ix_chat_sessions_project_id" in indexes:
            op.drop_index("ix_chat_sessions_project_id", table_name="chat_sessions")
        if "ix_chat_sessions_workspace_id" in indexes:
            op.drop_index("ix_chat_sessions_workspace_id", table_name="chat_sessions")
        with op.batch_alter_table("chat_sessions") as batch:
            for name in ("focus_id", "focus_kind", "project_id"):
                if name in columns:
                    batch.drop_column(name)
