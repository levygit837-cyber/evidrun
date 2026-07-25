from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import text
from sqlalchemy.orm import Session

from evidrun.infrastructure.database.engine import Database

__all__ = ["LeaseFence", "LeaseLost", "UnitOfWork"]

LeaseFence = tuple[str, str, str, int]


class LeaseLost(RuntimeError):
    """The caller no longer owns the active fenced execution lease."""


class UnitOfWork:
    """The session seam every persistence aggregate shares.

    Aggregates never reach for `Database`. They open a transaction here, and an
    operation whose atomicity spans aggregates passes the live `Session` to its
    collaborators instead of opening a second one. That is the whole point of the
    module: a nested session would split one transaction into two and break the
    lease fencing that `queue` depends on.
    """

    def __init__(self, database: Database) -> None:
        self.database = database

    @contextmanager
    def session(self) -> Generator[Session]:
        """Deferred transaction: SQLite takes its lock on first write."""
        with self.database.session() as session:
            yield session

    @contextmanager
    def immediate(self) -> Generator[Session]:
        """Eager write transaction, for read-then-write races over the same rows."""
        with self.database.session() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            yield session
