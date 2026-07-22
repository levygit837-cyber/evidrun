from __future__ import annotations

import sqlite3
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
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
        Base.metadata.create_all(self.engine)

    def session(self) -> Session:
        return self.session_factory()

    def dispose(self) -> None:
        self.engine.dispose()

    @property
    def raw_engine(self) -> Engine:
        return self.engine
