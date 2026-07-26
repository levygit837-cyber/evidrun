from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, cast


@dataclass(frozen=True)
class Claim:
    id: str
    document: str
    statement: str
    verifier: str
    expected: object


@dataclass(frozen=True)
class ClaimResult:
    claim: Claim
    severity: str | None
    status: str
    observed: object | None
    message: str


def load_claims(root: Path) -> tuple[Claim, ...]:
    path = root / "docs/claims.toml"
    if not path.exists():
        return ()
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != "1":
        raise ValueError('docs/claims.toml requires schema_version = "1"')
    raw_claims = data.get("claims", [])
    if not isinstance(raw_claims, list):
        raise ValueError("docs/claims.toml claims must be an array")
    claims: list[Claim] = []
    required = ("id", "document", "statement", "verifier", "expected")
    for index, raw in enumerate(raw_claims, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"claim {index} must be a table")
        item = cast(dict[str, Any], raw)
        missing = [key for key in required if key not in item]
        if missing:
            raise ValueError(f"claim {index} missing: {', '.join(missing)}")
        for key in required[:-1]:
            if not isinstance(item[key], str) or not item[key].strip():
                raise ValueError(f"claim {index} field {key} must be a non-empty string")
        document = item["document"].strip()
        document_path = PurePosixPath(document)
        resolved_document = (root / document).resolve()
        if (
            document_path.is_absolute()
            or not document_path.parts
            or document_path.parts[0] != "docs"
            or any(part in {".", ".."} for part in document_path.parts)
            or document_path.as_posix() != document
            or not resolved_document.is_relative_to((root / "docs").resolve())
        ):
            raise ValueError(
                f"claim {index} document must be a canonical relative path beneath docs/"
            )
        claims.append(
            Claim(
                id=item["id"].strip(),
                document=document,
                statement=item["statement"].strip(),
                verifier=item["verifier"].strip(),
                expected=item["expected"],
            )
        )
    ids = [claim.id for claim in claims]
    if len(ids) != len(set(ids)):
        raise ValueError("docs/claims.toml has duplicate claim ids")
    return tuple(claims)


def evaluate_claims(root: Path, claims: tuple[Claim, ...]) -> tuple[ClaimResult, ...]:
    document_count = len(
        [path for path in (root / "docs").rglob("*.md") if "_generated" not in path.parts]
    )
    results: list[ClaimResult] = []
    for claim in claims:
        if not (root / claim.document).is_file():
            results.append(
                ClaimResult(
                    claim,
                    "error",
                    "failed",
                    None,
                    f"claim document does not exist: {claim.document}",
                )
            )
        elif claim.verifier in {
            "document-count",
            "import-direction-violations",
            "code-budget-violations",
        }:
            observed = _observed_value(root, claim.verifier, document_count)
            passed = claim.expected == observed
            results.append(
                ClaimResult(
                    claim,
                    None if passed else "error",
                    "verified" if passed else "failed",
                    observed,
                    f"{claim.id} expected {claim.expected}, observed {observed}",
                )
            )
        else:
            results.append(
                ClaimResult(
                    claim,
                    "not-verifiable",
                    "not-verifiable",
                    None,
                    f"{claim.id} has no verifier: {claim.verifier}",
                )
            )
    return tuple(results)


def _observed_value(root: Path, verifier: str, document_count: int) -> object:
    if verifier == "document-count":
        return document_count
    command = (
        [sys.executable, "scripts/check_import_directions.py", "--format", "json"]
        if verifier == "import-direction-violations"
        else [sys.executable, "scripts/check_code_budget.py", "--json"]
    )
    completed = subprocess.run(command, cwd=root, check=False, capture_output=True, text=True)
    report = json.loads(completed.stdout)
    return len(report["violations"])
