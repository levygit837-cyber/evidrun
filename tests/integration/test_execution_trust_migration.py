from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

ROOT = Path(__file__).resolve().parents[2]


def _config(path: Path) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite+pysqlite:///{path}")
    return config


def test_execution_trust_migration_preserves_a_legacy_database(tmp_path: Path) -> None:
    path = tmp_path / "legacy-trust.db"
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE projects (id VARCHAR PRIMARY KEY);
            CREATE TABLE run_specs (
                id VARCHAR PRIMARY KEY,
                digest VARCHAR(64) NOT NULL UNIQUE
            );
            CREATE TABLE admission_records (
                id VARCHAR PRIMARY KEY,
                run_spec_id VARCHAR NOT NULL,
                decision VARCHAR NOT NULL,
                record_json TEXT NOT NULL,
                digest VARCHAR(64) NOT NULL,
                created_at DATETIME NOT NULL
            );
            CREATE TABLE runs (
                id VARCHAR PRIMARY KEY,
                objective TEXT NOT NULL
            );
            INSERT INTO runs (id, objective) VALUES ('run_legacy', 'preserve me');
            """
        )
    config = _config(path)
    command.stamp(config, "0006_project_name_identity")
    command.upgrade(config, "head")

    engine = create_engine(f"sqlite+pysqlite:///{path}")
    inspector = inspect(engine)
    assert {
        "execution_trust_records",
        "execution_review_targets",
    }.issubset(inspector.get_table_names())
    for table in ("admission_records", "runs"):
        columns = {item["name"] for item in inspector.get_columns(table)}
        assert {"execution_trust_id", "execution_trust_digest"}.issubset(columns)
    with engine.connect() as connection:
        assert (
            connection.exec_driver_sql(
                "SELECT objective FROM runs WHERE id = 'run_legacy'"
            ).scalar_one()
            == "preserve me"
        )
        assert (
            connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one()
            == "0008_lab_agent_session_store"
        )
    engine.dispose()


def test_execution_trust_empty_downgrade_removes_only_its_schema(tmp_path: Path) -> None:
    path = tmp_path / "trust-downgrade.db"
    config = _config(path)
    command.upgrade(config, "head")
    command.downgrade(config, "0006_project_name_identity")

    engine = create_engine(f"sqlite+pysqlite:///{path}")
    inspector = inspect(engine)
    assert "execution_trust_records" not in inspector.get_table_names()
    assert "execution_review_targets" not in inspector.get_table_names()
    for table in ("admission_records", "runs"):
        columns = {item["name"] for item in inspector.get_columns(table)}
        assert "execution_trust_id" not in columns
        assert "execution_trust_digest" not in columns
    assert {"run_specs", "contract_revisions"}.issubset(inspector.get_table_names())
    engine.dispose()


def test_execution_trust_downgrade_refuses_to_discard_current_records(
    tmp_path: Path,
) -> None:
    path = tmp_path / "trust-data.db"
    config = _config(path)
    command.upgrade(config, "head")
    engine = create_engine(f"sqlite+pysqlite:///{path}")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO workspaces (id, name, name_key, created_at) "
            "VALUES ('ws_current', 'Current', 'current', '2026-07-28T00:00:00')"
        )
        connection.exec_driver_sql(
            "INSERT INTO projects (id, workspace_id, name, name_key, created_at) "
            "VALUES ('prj_current', 'ws_current', 'Current', 'current', "
            "'2026-07-28T00:00:00')"
        )
        connection.exec_driver_sql(
            "INSERT INTO execution_trust_records ("
            "id, kind, project_id, study_logical_id, revision_set_digest, "
            "run_spec_digest, record_json, digest, semantic_digest, created_at"
            ") VALUES ("
            "'trust_current', 'unverified_revision_set', 'prj_current', 'study', "
            f"'{('a' * 64)}', '{('b' * 64)}', '{{}}', '{('c' * 64)}', "
            f"'{('d' * 64)}', '2026-07-28T00:00:00')"
        )
    engine.dispose()

    with pytest.raises(RuntimeError, match="canonical trust data exists"):
        command.downgrade(config, "0006_project_name_identity")
