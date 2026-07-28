from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from evidrun.infrastructure.database import Database
from evidrun.infrastructure.database.scope_schema import ScopeSchemaMigrationError

ROOT = Path(__file__).resolve().parents[2]


def _config(path: Path) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite+pysqlite:///{path}")
    return config


def _legacy_database(
    path: Path,
    *,
    workspaces: Sequence[tuple[str, str]],
    projects: Sequence[tuple[str, str, str]],
) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE workspaces (
                id VARCHAR PRIMARY KEY,
                name VARCHAR NOT NULL,
                created_at DATETIME NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE projects (
                id VARCHAR PRIMARY KEY,
                workspace_id VARCHAR NOT NULL REFERENCES workspaces(id),
                name VARCHAR NOT NULL,
                created_at DATETIME NOT NULL
            )
            """
        )
        connection.executemany(
            "INSERT INTO workspaces (id, name, created_at) VALUES (?, ?, ?)",
            [(item_id, name, "2026-07-27T00:00:00") for item_id, name in workspaces],
        )
        connection.executemany(
            "INSERT INTO projects (id, workspace_id, name, created_at) VALUES (?, ?, ?, ?)",
            [
                (item_id, workspace_id, name, "2026-07-27T00:00:00")
                for item_id, workspace_id, name in projects
            ],
        )
        connection.execute(
            "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
        )
        connection.execute(
            "INSERT INTO alembic_version (version_num) VALUES ('0004_runtime_kernel')"
        )


def test_scope_migrations_preserve_legacy_ids_names_and_install_constraints(
    tmp_path: Path,
) -> None:
    path = tmp_path / "legacy.db"
    _legacy_database(
        path,
        workspaces=(("ws_a", "  \uff2cab\tA "), ("ws_b", "Lab B")),
        projects=(
            ("prj_a", "ws_a", " Cafe\u0301 "),
            ("prj_b", "ws_b", "CAFÉ"),
        ),
    )

    command.upgrade(_config(path), "head")

    engine = create_engine(f"sqlite+pysqlite:///{path}")
    inspector = inspect(engine)
    workspace_column = next(
        item for item in inspector.get_columns("workspaces") if item["name"] == "name_key"
    )
    project_column = next(
        item for item in inspector.get_columns("projects") if item["name"] == "name_key"
    )
    assert workspace_column["nullable"] is False
    assert project_column["nullable"] is False
    assert {item["name"] for item in inspector.get_unique_constraints("workspaces")} >= {
        "uq_workspace_name_key"
    }
    assert {item["name"] for item in inspector.get_unique_constraints("projects")} >= {
        "uq_project_workspace_name_key"
    }
    with engine.connect() as connection:
        assert connection.exec_driver_sql(
            "SELECT id, name, name_key FROM workspaces ORDER BY id"
        ).all() == [
            ("ws_a", "  \uff2cab\tA ", "lab a"),
            ("ws_b", "Lab B", "lab b"),
        ]
        assert connection.exec_driver_sql(
            "SELECT id, workspace_id, name, name_key FROM projects ORDER BY id"
        ).all() == [
            ("prj_a", "ws_a", " Cafe\u0301 ", "café"),
            ("prj_b", "ws_b", "CAFÉ", "café"),
        ]
    engine.dispose()


@pytest.mark.parametrize(
    ("workspaces", "projects", "message"),
    [
        (
            (("ws_a", "Research Lab"), ("ws_b", " research\tLAB ")),
            (),
            "workspaces contains canonical name collisions",
        ),
        (
            (("ws_a", "Workspace"),),
            (("prj_a", "ws_a", "Project"), ("prj_b", "ws_a", "\uff50roject")),
            "projects contains canonical name collisions",
        ),
        (
            (("ws_a", " \t "),),
            (),
            "workspaces contains a name that normalizes to empty",
        ),
    ],
)
def test_scope_migrations_fail_closed_on_legacy_ambiguity(
    tmp_path: Path,
    workspaces: Sequence[tuple[str, str]],
    projects: Sequence[tuple[str, str, str]],
    message: str,
) -> None:
    path = tmp_path / "collision.db"
    _legacy_database(path, workspaces=workspaces, projects=projects)

    with pytest.raises(ScopeSchemaMigrationError, match=message):
        command.upgrade(_config(path), "head")

    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT id, name FROM workspaces ORDER BY id").fetchall() == list(
            workspaces
        )
        assert connection.execute(
            "SELECT id, workspace_id, name FROM projects ORDER BY id"
        ).fetchall() == list(projects)
        workspace_constraints = {
            row[1] for row in connection.execute("PRAGMA index_list('workspaces')")
        }
        project_constraints = {
            row[1] for row in connection.execute("PRAGMA index_list('projects')")
        }
    if message.startswith("workspaces"):
        assert "uq_workspace_name_key" not in workspace_constraints
    else:
        assert "uq_project_workspace_name_key" not in project_constraints


def test_scope_migration_allows_project_homonyms_across_workspaces_and_downgrades(
    tmp_path: Path,
) -> None:
    path = tmp_path / "homonyms.db"
    _legacy_database(
        path,
        workspaces=(("ws_a", "Workspace A"), ("ws_b", "Workspace B")),
        projects=(
            ("prj_a", "ws_a", "Shared name"),
            ("prj_b", "ws_b", " shared\tNAME "),
        ),
    )
    config = _config(path)

    command.upgrade(config, "head")
    command.downgrade(config, "0004_runtime_kernel")

    engine = create_engine(f"sqlite+pysqlite:///{path}")
    inspector = inspect(engine)
    assert "name_key" not in {item["name"] for item in inspector.get_columns("workspaces")}
    assert "name_key" not in {item["name"] for item in inspector.get_columns("projects")}
    with engine.connect() as connection:
        assert connection.exec_driver_sql(
            "SELECT id, name FROM workspaces ORDER BY id"
        ).all() == [("ws_a", "Workspace A"), ("ws_b", "Workspace B")]
        assert connection.exec_driver_sql(
            "SELECT id, workspace_id, name FROM projects ORDER BY id"
        ).all() == [
            ("prj_a", "ws_a", "Shared name"),
            ("prj_b", "ws_b", " shared\tNAME "),
        ]
    engine.dispose()


def test_database_create_all_upgrades_legacy_scopes_and_fails_closed_on_collision(
    tmp_path: Path,
) -> None:
    compatible = tmp_path / "create-all-compatible.db"
    _legacy_database(
        compatible,
        workspaces=(("ws_a", " Legacy Workspace "),),
        projects=(("prj_a", "ws_a", " Legacy Project "),),
    )
    database = Database(compatible)
    database.create_all()
    with database.raw_engine.connect() as connection:
        assert connection.exec_driver_sql(
            "SELECT name_key FROM workspaces WHERE id = 'ws_a'"
        ).scalar_one() == "legacy workspace"
        assert connection.exec_driver_sql(
            "SELECT name_key FROM projects WHERE id = 'prj_a'"
        ).scalar_one() == "legacy project"
    database.dispose()

    ambiguous = tmp_path / "create-all-ambiguous.db"
    _legacy_database(
        ambiguous,
        workspaces=(("ws_a", "Duplicate"), ("ws_b", " duplicate ")),
        projects=(),
    )
    database = Database(ambiguous)
    with pytest.raises(ScopeSchemaMigrationError, match="canonical name collisions"):
        database.create_all()
    database.dispose()
