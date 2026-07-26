from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "scripts" / "validate_docs.py"


def write_document(root: Path, **overrides: object) -> None:
    metadata: dict[str, object] = {
        "id": "fixture-doc",
        "type": "contract",
        "title": "Fixture document",
        "status": "accepted",
        "authority": "normative",
        "volatility": "timeless",
        "owner": "tests",
        "created_at": "2026-07-26",
        "updated_at": "2026-07-26",
        "applies_to": "tests",
        "sources": [],
        "supersedes": [],
        "superseded_by": None,
        "implementation_refs": [],
        "verification_refs": [],
    }
    metadata.update(overrides)
    docs = root / "docs"
    docs.mkdir(parents=True)
    (docs / "fixture.md").write_text(
        f"---\n{yaml.safe_dump(metadata, sort_keys=False)}---\n\n# Fixture\n",
        encoding="utf-8",
    )


def run_validator(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "--root", str(root)],
        check=False,
        capture_output=True,
        text=True,
    )


def test_cli_accepts_a_timeless_normative_document_and_exports_volatility(
    tmp_path: Path,
) -> None:
    write_document(tmp_path)

    result = run_validator(tmp_path)

    assert result.returncode == 0, result.stderr
    manifest = json.loads((tmp_path / "docs/_generated/manifest.json").read_text())
    assert manifest["documents"][0]["volatility"] == "timeless"


@pytest.mark.parametrize(
    ("overrides", "expected_error"),
    [
        (
            {"authority": "planning", "volatility": "timeless"},
            "planning authority requires snapshot volatility",
        ),
        (
            {"authority": "normative", "volatility": "snapshot"},
            "normative authority cannot use snapshot volatility",
        ),
        (
            {
                "status": "implemented",
                "authority": "incubation",
                "volatility": "snapshot",
                "implementation_refs": ["docs/fixture.md"],
            },
            "incubation authority cannot claim implemented status",
        ),
        (
            {"authority": "normative", "volatility": "generated"},
            "normative authority cannot use generated volatility",
        ),
    ],
)
def test_cli_rejects_impossible_authority_status_volatility_combinations(
    tmp_path: Path,
    overrides: dict[str, object],
    expected_error: str,
) -> None:
    write_document(tmp_path, **overrides)

    result = run_validator(tmp_path)

    assert result.returncode == 1
    assert expected_error in result.stderr


def test_cli_accepts_an_implemented_timeless_contract(tmp_path: Path) -> None:
    write_document(
        tmp_path,
        status="implemented",
        implementation_refs=["docs/fixture.md"],
    )

    result = run_validator(tmp_path)

    assert result.returncode == 0, result.stderr
