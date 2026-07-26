from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from doc_claims import ClaimResult


def write_artifacts(
    root: Path,
    entries: tuple[dict[str, Any], ...],
    claim_results: tuple[ClaimResult, ...],
) -> None:
    completed = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root, check=False, capture_output=True
    )
    if completed.returncode != 0:
        raise RuntimeError(f"git ls-files failed with exit code {completed.returncode}")
    tracked = completed.stdout.decode("utf-8").split("\0")
    repository_tree = sorted({"/".join(Path(path).parts[:2]) for path in tracked if path})
    generated = root / "docs/_generated"
    generated.mkdir(parents=True, exist_ok=True)
    (generated / "manifest.json").write_text(
        json.dumps({"schema_version": "1", "documents": entries}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    claims = [
        {
            "id": item.claim.id,
            "document": item.claim.document,
            "statement": item.claim.statement,
            "verifier": item.claim.verifier,
            "expected": item.claim.expected,
            "observed": item.observed,
            "status": item.status,
        }
        for item in claim_results
    ]
    (generated / "claims.json").write_text(
        json.dumps(
            {
                "schema_version": "1",
                "document_count": len(entries),
                "repository_tree": repository_tree,
                "claims": claims,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
