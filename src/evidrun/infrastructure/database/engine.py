from __future__ import annotations

import sqlite3
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Engine, String, create_engine, event, inspect
from sqlalchemy.orm import Session, sessionmaker

from evidrun.infrastructure.database.models import Base
from evidrun.infrastructure.database.scope_schema import (
    ensure_project_name_schema,
    ensure_workspace_name_schema,
)


class Database:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = path
        self.engine = create_engine(f"sqlite+pysqlite:///{path}", future=True)
        event.listen(self.engine, "connect", self._configure_sqlite)
        self.session_factory = sessionmaker(self.engine, expire_on_commit=False, class_=Session)

    @staticmethod
    def _configure_sqlite(dbapi_connection: sqlite3.Connection, _: object) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA synchronous=FULL")
        cursor.close()

    def create_all(self) -> None:
        import importlib

        importlib.import_module("evidrun.authority.models")  # register authority tables

        Base.metadata.create_all(self.engine)
        self._ensure_additive_run_contract_columns()
        self._ensure_additive_contract_revision_status()
        self._ensure_runtime_kernel_schema()
        self._ensure_scope_name_schema()

    def _ensure_additive_run_contract_columns(self) -> None:
        """Keep pre-contract local databases readable before Alembic is invoked explicitly."""
        columns = {item["name"] for item in inspect(self.engine).get_columns("runs")}
        additions = {
            "run_spec_id": "VARCHAR REFERENCES run_specs(id)",
            "admission_id": "VARCHAR REFERENCES admission_records(id)",
        }
        with self.engine.begin() as connection:
            for name, declaration in additions.items():
                if name not in columns:
                    connection.exec_driver_sql(
                        f"ALTER TABLE runs ADD COLUMN {name} {declaration}"
                    )

    def _ensure_additive_contract_revision_status(self) -> None:
        columns = {
            item["name"] for item in inspect(self.engine).get_columns("contract_revisions")
        }
        if "status" not in columns:
            with self.engine.begin() as connection:
                connection.exec_driver_sql(
                    "ALTER TABLE contract_revisions "
                    "ADD COLUMN status VARCHAR NOT NULL DEFAULT 'draft'"
                )

    def _ensure_runtime_kernel_schema(self) -> None:
        inspector = inspect(self.engine)
        event_columns = {
            item["name"] for item in inspector.get_columns("run_events")
        }
        with self.engine.begin() as connection:
            if "operation_key" not in event_columns:
                connection.exec_driver_sql(
                    "ALTER TABLE run_events ADD COLUMN operation_key VARCHAR"
                )
            connection.exec_driver_sql(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_run_event_operation "
                "ON run_events (run_id, operation_key)"
            )
            connection.exec_driver_sql(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_context_snapshot_run "
                "ON context_snapshots (run_id)"
            )
            connection.exec_driver_sql(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_evaluation_stage_source "
                "ON evaluation_records (run_id, stage_id, source_type)"
            )
            connection.exec_driver_sql(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_grade_run_grader "
                "ON grades (run_id, grader_id)"
            )
        run_columns = {
            item["name"]: item for item in inspect(self.engine).get_columns("runs")
        }
        if run_columns["experiment_revision_id"].get("nullable") is False:
            with self.engine.begin() as connection:
                context = MigrationContext.configure(connection)
                operations = Operations(context)
                with operations.batch_alter_table("runs") as batch:
                    batch.alter_column(
                        "experiment_revision_id",
                        existing_type=String(),
                        nullable=True,
                    )

    def _ensure_scope_name_schema(self) -> None:
        """Upgrade legacy local scope rows before repositories use their name keys."""

        with self.engine.connect() as connection:
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
            connection.commit()
            try:
                with connection.begin():
                    ensure_workspace_name_schema(connection)
                    ensure_project_name_schema(connection)
            finally:
                if connection.in_transaction():
                    connection.rollback()
                connection.exec_driver_sql("PRAGMA foreign_keys=ON")
                connection.commit()

    def session(self) -> Session:
        return self.session_factory()

    def dispose(self) -> None:
        self.engine.dispose()

    @property
    def raw_engine(self) -> Engine:
        return self.engine
