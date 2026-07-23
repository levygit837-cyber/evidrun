from __future__ import annotations

import sqlite3
from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, inspect

from alembic import command
from evidrun.infrastructure.database import Database

ROOT = Path(__file__).resolve().parents[2]


def test_alembic_contract_foundation_bootstraps_an_empty_database(tmp_path: Path) -> None:
    path = tmp_path / "empty.db"
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite+pysqlite:///{path}")
    command.upgrade(config, "head")

    engine = create_engine(f"sqlite+pysqlite:///{path}")
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert {
        "contract_revisions",
        "contract_decisions",
        "run_specs",
        "admission_records",
        "checkpoint_records",
        "evaluation_records",
    }.issubset(tables)
    run_columns = {item["name"] for item in inspector.get_columns("runs")}
    assert {"run_spec_id", "admission_id"}.issubset(run_columns)
    engine.dispose()


def test_create_all_adds_contract_links_to_a_legacy_runs_table(tmp_path: Path) -> None:
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE runs (
                id VARCHAR PRIMARY KEY,
                experiment_revision_id VARCHAR NOT NULL,
                variant_id VARCHAR NOT NULL,
                repetition INTEGER NOT NULL DEFAULT 1,
                status VARCHAR NOT NULL,
                runner VARCHAR NOT NULL,
                objective TEXT NOT NULL,
                output TEXT,
                context_hash VARCHAR(64),
                retry_of VARCHAR,
                created_at DATETIME NOT NULL,
                completed_at DATETIME
            )
            """
        )
        connection.execute(
            """
            INSERT INTO runs (
                id, experiment_revision_id, variant_id, repetition, status, runner,
                objective, created_at
            ) VALUES (
                'run_legacy', 'expr_legacy', 'baseline', 1, 'completed',
                'legacy-runner', 'Preserve this legacy Run', '2026-07-22T00:00:00'
            )
            """
        )
    database = Database(path)
    database.create_all()
    columns = {item["name"] for item in inspect(database.raw_engine).get_columns("runs")}
    assert {"run_spec_id", "admission_id"}.issubset(columns)
    with database.raw_engine.connect() as connection:
        preserved = connection.exec_driver_sql(
            "SELECT objective FROM runs WHERE id = 'run_legacy'"
        ).scalar_one()
    assert preserved == "Preserve this legacy Run"
    contract_columns = {
        item["name"]
        for item in inspect(database.raw_engine).get_columns("contract_revisions")
    }
    assert "status" in contract_columns
    database.dispose()
