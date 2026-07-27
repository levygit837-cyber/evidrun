"""Idempotent Workspace/Project name-key upgrades for Alembic and local startup."""

from __future__ import annotations

from collections import defaultdict

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Connection, inspect

from evidrun.contracts.scope import normalize_scope_name

WORKSPACE_NAME_CONSTRAINT = "uq_workspace_name_key"
PROJECT_NAME_CONSTRAINT = "uq_project_workspace_name_key"


class ScopeSchemaMigrationError(RuntimeError):
    """Legacy scope names cannot be migrated without an operator decision."""


def ensure_workspace_name_schema(connection: Connection) -> None:
    _ensure_name_column(
        connection,
        table="workspaces",
        constraint_name=WORKSPACE_NAME_CONSTRAINT,
        constraint_columns=("name_key",),
        parent_column=None,
    )


def ensure_project_name_schema(connection: Connection) -> None:
    _ensure_name_column(
        connection,
        table="projects",
        constraint_name=PROJECT_NAME_CONSTRAINT,
        constraint_columns=("workspace_id", "name_key"),
        parent_column="workspace_id",
    )


def _ensure_name_column(
    connection: Connection,
    *,
    table: str,
    constraint_name: str,
    constraint_columns: tuple[str, ...],
    parent_column: str | None,
) -> None:
    operations = Operations(MigrationContext.configure(connection))
    columns = {item["name"]: item for item in inspect(connection).get_columns(table)}
    if "name_key" not in columns:
        operations.add_column(table, sa.Column("name_key", sa.String(), nullable=True))

    selected = "id, name" if parent_column is None else f"id, {parent_column}, name"
    rows = list(connection.execute(sa.text(f"SELECT {selected} FROM {table}")).mappings())
    normalized_rows: list[tuple[str, str, str | None]] = []
    identities: defaultdict[tuple[str | None, str], list[str]] = defaultdict(list)
    for row in rows:
        row_id = str(row["id"])
        parent_id = None if parent_column is None else str(row[parent_column])
        try:
            normalized = normalize_scope_name(str(row["name"]))
        except ValueError as exc:
            raise ScopeSchemaMigrationError(
                f"{table} contains a name that normalizes to empty; id={row_id}"
            ) from exc
        normalized_rows.append((row_id, normalized.name_key, parent_id))
        identities[(parent_id, normalized.name_key)].append(row_id)

    collisions = [ids for ids in identities.values() if len(ids) > 1]
    if collisions:
        rendered = "; ".join(",".join(sorted(ids)) for ids in collisions)
        raise ScopeSchemaMigrationError(
            f"{table} contains canonical name collisions; conflicting_ids={rendered}"
        )

    update = sa.text(f"UPDATE {table} SET name_key = :name_key WHERE id = :id")
    for row_id, name_key, _parent_id in normalized_rows:
        connection.execute(update, {"id": row_id, "name_key": name_key})

    inspector = inspect(connection)
    column = next(item for item in inspector.get_columns(table) if item["name"] == "name_key")
    constraint_names = {
        item["name"] for item in inspector.get_unique_constraints(table) if item["name"]
    }
    if column.get("nullable") is False and constraint_name in constraint_names:
        return
    with operations.batch_alter_table(table) as batch:
        if column.get("nullable") is not False:
            batch.alter_column("name_key", existing_type=sa.String(), nullable=False)
        if constraint_name not in constraint_names:
            batch.create_unique_constraint(constraint_name, list(constraint_columns))
