from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "scripts" / "validate_docs.py"


def write_document(
    root: Path,
    *,
    relative: str = "fixture.md",
    body: str = "# Fixture\n",
    **overrides: object,
) -> None:
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
    path = docs / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\n{yaml.safe_dump(metadata, sort_keys=False)}---\n\n{body}",
        encoding="utf-8",
    )


def run_validator(
    root: Path,
    *,
    output_format: str = "text",
    today: str | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    if not (root / ".git").exists():
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    command = [
        sys.executable,
        str(VALIDATOR),
        "--root",
        str(root),
        "--format",
        output_format,
    ]
    if today is not None:
        command.extend(("--today", today))
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def write_claims(root: Path, claims: list[dict[str, object]]) -> None:
    lines = ['schema_version = "1"', ""]
    for claim in claims:
        lines.append("[[claims]]")
        for key, value in claim.items():
            lines.append(f"{key} = {json.dumps(value)}")
        lines.append("")
    path = root / "docs/claims.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


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


def test_json_reports_a_broken_relative_link_as_a_typed_error(tmp_path: Path) -> None:
    write_document(tmp_path, body="# Fixture\n\n[Missing](missing.md)\n")

    result = run_validator(tmp_path, output_format="json")

    assert result.returncode == 1
    assert json.loads(result.stdout)["diagnostics"] == [
        {
            "severity": "error",
            "code": "broken-link",
            "document": "docs/fixture.md",
            "message": "relative link does not resolve: missing.md",
        }
    ]


def test_json_reports_a_broken_reference_style_link(tmp_path: Path) -> None:
    write_document(tmp_path, body="# Fixture\n\n[Missing][guide]\n\n[guide]: missing.md\n")

    result = run_validator(tmp_path, output_format="json")

    assert result.returncode == 1
    assert json.loads(result.stdout)["diagnostics"][0]["code"] == "broken-link"


def test_json_rejects_asymmetric_supersession_between_existing_documents(
    tmp_path: Path,
) -> None:
    write_document(
        tmp_path,
        relative="old.md",
        id="old-doc",
        status="superseded",
        superseded_by="docs/new.md",
    )
    write_document(
        tmp_path,
        relative="new.md",
        id="new-doc",
        supersedes=[],
    )

    result = run_validator(tmp_path, output_format="json")

    assert result.returncode == 1
    assert json.loads(result.stdout)["diagnostics"] == [
        {
            "severity": "error",
            "code": "supersession-mismatch",
            "document": "docs/old.md",
            "message": "docs/new.md does not supersede docs/old.md",
        }
    ]


def test_existing_document_with_a_false_typed_claim_fails_its_verifier(
    tmp_path: Path,
) -> None:
    write_document(tmp_path)
    write_claims(
        tmp_path,
        [
            {
                "id": "wrong-document-count",
                "document": "docs/fixture.md",
                "statement": "The repository contains two documents.",
                "verifier": "document-count",
                "expected": 2,
            }
        ],
    )

    result = run_validator(tmp_path, output_format="json")

    assert result.returncode == 1
    assert json.loads(result.stdout)["diagnostics"] == [
        {
            "severity": "error",
            "code": "claim-failed",
            "document": "docs/fixture.md",
            "message": "wrong-document-count expected 2, observed 1",
        }
    ]


def test_claim_without_a_known_verifier_is_explicitly_not_verifiable(
    tmp_path: Path,
) -> None:
    write_document(tmp_path)
    write_claims(
        tmp_path,
        [
            {
                "id": "semantic-judgment",
                "document": "docs/fixture.md",
                "statement": "The prose is semantically approved.",
                "verifier": "human-semantic-approval",
                "expected": True,
            }
        ],
    )

    result = run_validator(tmp_path, output_format="json")

    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["diagnostics"] == [
        {
            "severity": "not-verifiable",
            "code": "claim-not-verifiable",
            "document": "docs/fixture.md",
            "message": "semantic-judgment has no verifier: human-semantic-approval",
        }
    ]


@pytest.mark.parametrize("document", ["../outside.md", "/etc/hosts", "docs/../outside.md"])
def test_claim_document_must_be_a_canonical_path_beneath_docs(
    tmp_path: Path, document: str
) -> None:
    write_document(tmp_path)
    write_claims(
        tmp_path,
        [
            {
                "id": "escaped-document",
                "document": document,
                "statement": "An external file exists.",
                "verifier": "document-count",
                "expected": 1,
            }
        ],
    )

    result = run_validator(tmp_path, output_format="json")

    assert result.returncode == 1
    assert json.loads(result.stdout)["diagnostics"][0]["code"] == "claim-registry"


def test_json_rejects_created_at_after_updated_at(tmp_path: Path) -> None:
    write_document(
        tmp_path,
        created_at="2026-07-27",
        updated_at="2026-07-26",
    )

    result = run_validator(tmp_path, output_format="json")

    assert result.returncode == 1
    assert json.loads(result.stdout)["diagnostics"][0] == {
        "severity": "error",
        "code": "invalid-date-order",
        "document": "docs/fixture.md",
        "message": "created_at must not be after updated_at",
    }


def test_overdue_review_is_warning_only_before_the_explicit_ratchet(tmp_path: Path) -> None:
    write_document(tmp_path, review_due="2026-07-25")

    result = run_validator(tmp_path, output_format="json", today="2026-07-26")

    assert result.returncode == 0
    assert json.loads(result.stdout)["diagnostics"] == [
        {
            "severity": "warning",
            "code": "review-overdue",
            "document": "docs/fixture.md",
            "message": "review_due 2026-07-25 is before 2026-07-26",
        }
    ]


def test_default_validation_does_not_read_the_wall_clock(tmp_path: Path) -> None:
    write_document(tmp_path, review_due="2000-01-01")

    result = run_validator(tmp_path, output_format="json")

    assert result.returncode == 0
    assert json.loads(result.stdout)["diagnostics"] == []


def test_default_validation_uses_the_checkout_date_for_review_warnings(tmp_path: Path) -> None:
    write_document(tmp_path, review_due="2026-07-25")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "docs/fixture.md"], cwd=tmp_path, check=True)
    commit_env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Evidrun Tests",
        "GIT_AUTHOR_EMAIL": "tests@evidrun.invalid",
        "GIT_COMMITTER_NAME": "Evidrun Tests",
        "GIT_COMMITTER_EMAIL": "tests@evidrun.invalid",
        "GIT_AUTHOR_DATE": "2026-07-26T12:00:00Z",
        "GIT_COMMITTER_DATE": "2026-07-26T12:00:00Z",
    }
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=tmp_path, check=True, env=commit_env)

    result = run_validator(tmp_path, output_format="json")

    assert result.returncode == 0
    diagnostic = json.loads(result.stdout)["diagnostics"][0]
    assert diagnostic["code"] == "review-overdue"
    assert "before 2026-07-26" in diagnostic["message"]


def test_artifact_generation_fails_closed_when_git_inventory_fails(tmp_path: Path) -> None:
    write_document(tmp_path)
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_git = fake_bin / "git"
    fake_git.write_text("#!/bin/sh\nexit 42\n", encoding="utf-8")
    fake_git.chmod(0o755)
    run_env = {**os.environ, "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}"}

    result = run_validator(tmp_path, output_format="json", env=run_env)

    assert result.returncode == 1
    diagnostic = json.loads(result.stdout)["diagnostics"][0]
    assert diagnostic["code"] == "artifact-generation"
    assert "git ls-files failed" in diagnostic["message"]
    assert not (tmp_path / "docs/_generated/claims.json").exists()


def test_existing_python_reference_with_missing_symbol_fails(tmp_path: Path) -> None:
    source = tmp_path / "src/example.py"
    source.parent.mkdir(parents=True)
    source.write_text("def actual_symbol() -> None:\n    pass\n", encoding="utf-8")
    write_document(
        tmp_path,
        status="implemented",
        implementation_refs=["src/example.py#missing_symbol"],
    )

    result = run_validator(tmp_path, output_format="json")

    assert result.returncode == 1
    assert json.loads(result.stdout)["diagnostics"][0] == {
        "severity": "error",
        "code": "missing-reference-symbol",
        "document": "docs/fixture.md",
        "message": "reference symbol does not resolve: src/example.py#missing_symbol",
    }


def test_python_reference_does_not_resolve_a_function_local_name(tmp_path: Path) -> None:
    source = tmp_path / "src/example.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "def public_function() -> None:\n    temporary = 1\n",
        encoding="utf-8",
    )
    write_document(
        tmp_path,
        status="implemented",
        implementation_refs=["src/example.py#temporary"],
    )

    result = run_validator(tmp_path, output_format="json")

    assert result.returncode == 1
    assert json.loads(result.stdout)["diagnostics"][0]["code"] == "missing-reference-symbol"


def test_missing_frontmatter_source_fails_even_when_other_refs_exist(tmp_path: Path) -> None:
    write_document(tmp_path, sources=["docs/missing-source.md"])

    result = run_validator(tmp_path, output_format="json")

    assert result.returncode == 1
    assert json.loads(result.stdout)["diagnostics"][0] == {
        "severity": "error",
        "code": "missing-source",
        "document": "docs/fixture.md",
        "message": "source does not resolve: docs/missing-source.md",
    }
