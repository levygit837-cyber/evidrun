from __future__ import annotations

import sqlite3
from pathlib import Path

from sqlalchemy import Engine, create_engine, event, inspect
from sqlalchemy.orm import Session, sessionmaker

from evidrun.infrastructure.database.models import Base


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

    def session(self) -> Session:
        return self.session_factory()

    def dispose(self) -> None:
        self.engine.dispose()

    @property
    def raw_engine(self) -> Engine:
        return self.engine
