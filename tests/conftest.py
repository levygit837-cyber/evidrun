from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from evidrun.infrastructure.database import Database, Repository


@pytest.fixture
def repository(tmp_path: Path) -> Iterator[Repository]:
    database = Database(tmp_path / "evidrun.db")
    database.create_all()
    yield Repository(database)
    database.dispose()

