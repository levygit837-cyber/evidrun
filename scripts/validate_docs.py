from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import date
from pathlib import Path

from doc_artifacts import write_artifacts
from doc_validation import Diagnostic, ValidationResult, validate_repository

DEFAULT_ROOT = Path(__file__).resolve().parents[1]


def render(result: object, *, output_format: str) -> None:
    diagnostics = result.diagnostics
    if output_format == "json":
        print(
            json.dumps(
                {
                    "diagnostics": [asdict(item) for item in diagnostics],
                    "documents": len(result.entries),
                },
                indent=2,
            )
        )
        return
    for item in diagnostics:
        print(
            f"{item.severity.upper()} {item.code}: {item.document} {item.message}",
            file=sys.stderr if item.severity == "error" else sys.stdout,
        )


def validate_docs(
    root: Path,
    *,
    output_format: str = "text",
    today: date | None = None,
) -> int:
    result = validate_repository(root, today=today)
    if result.has_errors:
        render(result, output_format=output_format)
        return 1
    try:
        write_artifacts(root, result.entries, result.claim_results)
    except (OSError, RuntimeError) as exc:
        failure = ValidationResult(
            (
                Diagnostic(
                    "error",
                    "artifact-generation",
                    "docs/_generated",
                    str(exc),
                ),
            ),
            result.entries,
            result.claim_results,
        )
        render(failure, output_format=output_format)
        return 1
    render(result, output_format=output_format)
    if output_format == "text":
        print(
            f"Validated {len(result.entries)} documents; generated "
            "docs/_generated/manifest.json and docs/_generated/claims.json"
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Evidrun documentation metadata")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--today", type=date.fromisoformat, default=None)
    args = parser.parse_args()
    return validate_docs(args.root.resolve(), output_format=args.format, today=args.today)


if __name__ == "__main__":
    raise SystemExit(main())
