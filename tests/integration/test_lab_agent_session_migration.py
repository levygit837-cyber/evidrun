from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from evidrun.infrastructure.database.lab_errors import LabSessionMigrationError

ROOT = Path(__file__).resolve().parents[2]
LEGACY_FIXTURE = ROOT / "tests/fixtures/lab_agent_session_store_v0007.sql"
PREVIOUS_FIXTURE = ROOT / "tests/fixtures/lab_turn_instruction_digest_v0008.sql"


def _config(path: Path) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite+pysqlite:///{path}")
    return config


def _legacy_database(path: Path, *, scope_type: str | None, scope_id: str | None) -> None:
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE workspaces (
                id VARCHAR PRIMARY KEY,
                name VARCHAR NOT NULL,
                name_key VARCHAR NOT NULL,
                created_at DATETIME NOT NULL
            );
            CREATE TABLE projects (
                id VARCHAR PRIMARY KEY,
                workspace_id VARCHAR NOT NULL REFERENCES workspaces(id),
                name VARCHAR NOT NULL,
                name_key VARCHAR NOT NULL,
                created_at DATETIME NOT NULL
            );
            CREATE TABLE chat_sessions (
                id VARCHAR PRIMARY KEY,
                workspace_id VARCHAR NOT NULL REFERENCES workspaces(id),
                scope_type VARCHAR,
                scope_id VARCHAR,
                title VARCHAR NOT NULL,
                created_at DATETIME NOT NULL
            );
            CREATE TABLE chat_messages (
                id VARCHAR PRIMARY KEY,
                session_id VARCHAR NOT NULL REFERENCES chat_sessions(id),
                role VARCHAR NOT NULL,
                content TEXT NOT NULL,
                created_at DATETIME NOT NULL
            );
            CREATE TABLE alembic_version (
                version_num VARCHAR(32) NOT NULL PRIMARY KEY
            );
            INSERT INTO alembic_version (version_num)
            VALUES ('0007_execution_trust_foundation');
            """
        )
        connection.execute(
            "INSERT INTO workspaces (id,name,name_key,created_at) VALUES (?,?,?,?)",
            ("ws_legacy", "Legado", "legado", "2026-08-02T00:00:00"),
        )
        connection.execute(
            "INSERT INTO projects (id,workspace_id,name,name_key,created_at) VALUES (?,?,?,?,?)",
            ("prj_legacy", "ws_legacy", "Projeto", "projeto", "2026-08-02T00:00:00"),
        )
        connection.execute(
            "INSERT INTO chat_sessions (id,workspace_id,scope_type,scope_id,title,created_at) "
            "VALUES (?,?,?,?,?,?)",
            (
                "chat_legacy",
                "ws_legacy",
                scope_type,
                scope_id,
                "Título cita prj_legacy mas não concede escopo",
                "2026-08-02T00:00:00",
            ),
        )
        connection.executemany(
            "INSERT INTO chat_messages (id,session_id,role,content,created_at) VALUES (?,?,?,?,?)",
            [
                (
                    "msg_b",
                    "chat_legacy",
                    "custom_role",
                    "Conteúdo cita prj_legacy e deve ser preservado",
                    "2026-08-02T01:00:00",
                ),
                ("msg_a", "chat_legacy", "human", "Primeiro", "2026-08-02T01:00:00"),
                ("msg_c", "chat_legacy", "agent", "Terceiro", "2026-08-02T02:00:00"),
            ],
        )


def test_migration_preserves_ids_content_and_stable_message_order(tmp_path: Path) -> None:
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as connection:
        connection.executescript(LEGACY_FIXTURE.read_text())

    command.upgrade(_config(path), "head")

    engine = create_engine(f"sqlite+pysqlite:///{path}")
    with engine.connect() as connection:
        assert connection.exec_driver_sql(
            "SELECT id,workspace_id,project_id,focus_kind,focus_id,title FROM chat_sessions"
        ).one() == (
            "chat_legacy",
            "ws_legacy",
            "prj_legacy",
            None,
            None,
            "Título cita prj_legacy mas não concede escopo",
        )
        assert connection.exec_driver_sql(
            "SELECT id,role,content,sequence FROM chat_messages ORDER BY sequence"
        ).all() == [
            ("msg_a", "human", "Primeiro", 1),
            (
                "msg_b",
                "system_note",
                "[legacy role: custom_role]\nConteúdo cita prj_legacy e deve ser preservado",
                2,
            ),
            ("msg_c", "agent", "Terceiro", 3),
        ]
    assert "lab_tool_traces" in inspect(engine).get_table_names()
    engine.dispose()


def test_migration_preserves_already_typed_scope(tmp_path: Path) -> None:
    path = tmp_path / "typed.db"
    _legacy_database(path, scope_type=None, scope_id=None)
    with sqlite3.connect(path) as connection:
        connection.execute("ALTER TABLE chat_sessions ADD COLUMN project_id VARCHAR")
        connection.execute("ALTER TABLE chat_sessions ADD COLUMN focus_kind VARCHAR")
        connection.execute("ALTER TABLE chat_sessions ADD COLUMN focus_id VARCHAR")
        connection.execute(
            "UPDATE chat_sessions SET project_id='prj_legacy' WHERE id='chat_legacy'"
        )

    command.upgrade(_config(path), "head")

    with sqlite3.connect(path) as connection:
        assert connection.execute(
            "SELECT project_id,focus_kind,focus_id FROM chat_sessions WHERE id='chat_legacy'"
        ).fetchone() == ("prj_legacy", None, None)


def test_migration_cria_registro_de_instrucao_sem_reescrever_sessao_anterior(
    tmp_path: Path,
) -> None:
    path = tmp_path / "v0008.db"
    with sqlite3.connect(path) as connection:
        connection.executescript(PREVIOUS_FIXTURE.read_text())

    command.upgrade(_config(path), "head")

    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT id,title FROM chat_sessions").fetchone() == (
            "chat_v0008",
            "Sessão anterior",
        )
        assert connection.execute("SELECT * FROM lab_turn_instructions").fetchall() == []
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == (
            "0009_lab_turn_instruction_digest",
        )


def test_migration_fails_closed_without_inference_from_text(tmp_path: Path) -> None:
    path = tmp_path / "ambiguous.db"
    _legacy_database(path, scope_type="unknown", scope_id="prj_missing")

    with pytest.raises(LabSessionMigrationError, match="id=chat_legacy"):
        command.upgrade(_config(path), "head")

    with sqlite3.connect(path) as connection:
        row = connection.execute(
            "SELECT scope_type,scope_id,title FROM chat_sessions WHERE id='chat_legacy'"
        ).fetchone()
        assert row == (
            "unknown",
            "prj_missing",
            "Título cita prj_legacy mas não concede escopo",
        )
