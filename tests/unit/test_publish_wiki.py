from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.publish_wiki import validate_source_commit


def write_meta(source: Path, commit_hash: str) -> None:
    source.mkdir()
    (source / ".wiki-meta.json").write_text(
        json.dumps({"commitHash": commit_hash}),
        encoding="utf-8",
    )


def test_source_commit_validation_accepts_exact_snapshot(tmp_path: Path) -> None:
    source = tmp_path / "source"
    write_meta(source, "abc123")

    validate_source_commit(source, "abc123", allow_stale_source=False)


def test_source_commit_validation_rejects_stale_snapshot(tmp_path: Path) -> None:
    source = tmp_path / "source"
    write_meta(source, "old123")

    with pytest.raises(SystemExit, match="wiki snapshot is stale"):
        validate_source_commit(source, "new456", allow_stale_source=False)


def test_source_commit_validation_allows_explicit_historical_publish(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "source"
    write_meta(source, "old123")

    validate_source_commit(source, "new456", allow_stale_source=True)

    assert "WARNING: wiki snapshot is stale" in capsys.readouterr().out


def test_checked_in_wiki_metadata_matches_markdown_pages() -> None:
    source = Path(__file__).parents[2] / "droid-wiki"
    metadata = json.loads((source / ".wiki-meta.json").read_text(encoding="utf-8"))
    pages = {path.relative_to(source).as_posix() for path in source.rglob("*.md")}

    assert metadata["pageCount"] == len(pages)
    assert set(metadata["pageOrder"]) == pages
