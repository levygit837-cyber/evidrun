from __future__ import annotations

import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

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
        "run_execution_jobs",
        "run_execution_attempts",
        "subject_envelopes",
        "execution_trust_records",
        "execution_review_targets",
    }.issubset(tables)
    run_columns = {item["name"] for item in inspector.get_columns("runs")}
    assert {
        "run_spec_id",
        "admission_id",
        "execution_trust_id",
        "execution_trust_digest",
    }.issubset(run_columns)
    experiment_column = next(
        item for item in inspector.get_columns("runs") if item["name"] == "experiment_revision_id"
    )
    assert experiment_column["nullable"] is True
    event_columns = {item["name"] for item in inspector.get_columns("run_events")}
    assert "operation_key" in event_columns
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
        item["name"] for item in inspect(database.raw_engine).get_columns("contract_revisions")
    }
    assert "status" in contract_columns
    experiment_column = next(
        item
        for item in inspect(database.raw_engine).get_columns("runs")
        if item["name"] == "experiment_revision_id"
    )
    assert experiment_column["nullable"] is True
    tables = set(inspect(database.raw_engine).get_table_names())
    assert {
        "run_execution_jobs",
        "run_execution_attempts",
        "subject_envelopes",
    }.issubset(tables)
    database.dispose()


def test_alembic_runtime_kernel_preserves_a_legacy_run(tmp_path: Path) -> None:
    path = tmp_path / "legacy-alembic.db"
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
                'run_alembic_legacy', 'expr_legacy', 'baseline', 1, 'completed',
                'legacy-runner', 'Preserve through Alembic', '2026-07-22T00:00:00'
            )
            """
        )
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite+pysqlite:///{path}")
    command.upgrade(config, "head")

    engine = create_engine(f"sqlite+pysqlite:///{path}")
    with engine.connect() as connection:
        assert (
            connection.exec_driver_sql(
                "SELECT objective FROM runs WHERE id = 'run_alembic_legacy'"
            ).scalar_one()
            == "Preserve through Alembic"
        )
    experiment_column = next(
        item
        for item in inspect(engine).get_columns("runs")
        if item["name"] == "experiment_revision_id"
    )
    assert experiment_column["nullable"] is True
    engine.dispose()


def test_runtime_kernel_migration_creates_its_own_tables_from_0001(
    tmp_path: Path,
) -> None:
    path = tmp_path / "runtime-kernel-from-0001.db"
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite+pysqlite:///{path}")
    command.upgrade(config, "0001_contract_foundation")

    engine = create_engine(f"sqlite+pysqlite:///{path}")
    with engine.begin() as connection:
        connection.exec_driver_sql("DROP TABLE run_execution_attempts")
        connection.exec_driver_sql("DROP TABLE run_execution_jobs")
        connection.exec_driver_sql("DROP TABLE subject_envelopes")
    engine.dispose()

    command.upgrade(config, "head")
    migrated_engine = create_engine(f"sqlite+pysqlite:///{path}")
    tables = set(inspect(migrated_engine).get_table_names())
    assert {
        "run_execution_jobs",
        "run_execution_attempts",
        "subject_envelopes",
    }.issubset(tables)
    attempt_uniques = {
        constraint["name"]
        for constraint in inspect(migrated_engine).get_unique_constraints("run_execution_attempts")
    }
    assert {
        "uq_run_attempt_generation",
        "uq_run_attempt_ordinal",
    }.issubset(attempt_uniques)
    migrated_engine.dispose()


def test_runtime_kernel_upgrades_database_already_stamped_at_human_authority(
    tmp_path: Path,
) -> None:
    path = tmp_path / "pre-runtime-authority.db"
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite+pysqlite:///{path}")
    command.upgrade(config, "0003_human_authority")

    engine = create_engine(f"sqlite+pysqlite:///{path}")
    with engine.begin() as connection:
        # Revision 0001 used the then-current SQLAlchemy metadata during bootstrap.
        # Remove future tables to reproduce a real database created before the
        # Runtime Kernel existed while retaining its 0003 Alembic stamp.
        connection.exec_driver_sql("DROP TABLE IF EXISTS run_execution_attempts")
        connection.exec_driver_sql("DROP TABLE IF EXISTS run_execution_jobs")
        connection.exec_driver_sql("DROP TABLE IF EXISTS subject_envelopes")
    engine.dispose()

    command.upgrade(config, "head")

    migrated_engine = create_engine(f"sqlite+pysqlite:///{path}")
    inspector = inspect(migrated_engine)
    assert {
        "human_credentials",
        "human_challenges",
        "run_execution_jobs",
        "run_execution_attempts",
        "subject_envelopes",
    }.issubset(inspector.get_table_names())
    with migrated_engine.connect() as connection:
        assert (
            connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one()
            == "0009_lab_turn_instruction_digest"
        )
    migrated_engine.dispose()
