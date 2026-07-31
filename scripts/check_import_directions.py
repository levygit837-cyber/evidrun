from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tomllib
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, cast

from import_graph import ImportEdge, WorktreeSource, build_graph

CONTRACTS_FORBIDDEN_EXTERNALS = ("fastapi", "sqlalchemy", "openai", "electron", "react")
NATIVE_BINDING_PACKAGES = {"bindings", "ffi-napi", "node-gyp-build", "ref-napi"}


@dataclass(frozen=True, order=True)
class Violation:
    source: str
    destination: str
    rule: str
    chain: tuple[str, ...]


@dataclass(frozen=True)
class ImportException:
    source: str
    destination: str
    rule: str
    reason: str
    owner: str
    expires: date

    def matches(self, violation: Violation) -> bool:
        return (
            self.source,
            self.destination,
            self.rule,
        ) == (violation.source, violation.destination, violation.rule)


def load_exceptions(root: Path) -> tuple[ImportException, ...]:
    config_path = root / "import-directions.toml"
    if not config_path.exists():
        return ()
    data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    if data.get("schema_version") != "1":
        raise ValueError("import-directions.toml requires schema_version = \"1\"")
    raw_exceptions = data.get("exceptions", [])
    if not isinstance(raw_exceptions, list):
        raise ValueError("import-directions.toml exceptions must be an array")
    exceptions: list[ImportException] = []
    required = {"source", "destination", "rule", "reason", "owner", "expires"}
    for index, raw in enumerate(cast(list[object], raw_exceptions), start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"exception {index} must be a table")
        document = cast(dict[str, Any], raw)
        missing = sorted(key for key in required if key not in document)
        if missing:
            raise ValueError(f"exception {index} missing: {', '.join(missing)}")
        normalized: dict[str, str] = {}
        for key in ("source", "destination", "rule", "reason", "owner"):
            value = document[key]
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"exception {index} field {key} must be a non-empty string"
                )
            normalized[key] = value.strip()
        raw_expiry = document["expires"]
        if isinstance(raw_expiry, datetime):
            raise ValueError(
                f"exception {index} expires must be a TOML date or ISO date string"
            )
        if isinstance(raw_expiry, date):
            expiry = raw_expiry
        elif isinstance(raw_expiry, str):
            expiry = date.fromisoformat(raw_expiry.strip())
        else:
            raise ValueError(
                f"exception {index} expires must be a TOML date or ISO date string"
            )
        if expiry < datetime.now(UTC).date():
            raise ValueError(f"exception {index} expired on {expiry.isoformat()}")
        exceptions.append(
            ImportException(
                source=normalized["source"],
                destination=normalized["destination"],
                rule=normalized["rule"],
                reason=normalized["reason"],
                owner=normalized["owner"],
                expires=expiry,
            )
        )
    keys = [(item.source, item.destination, item.rule) for item in exceptions]
    if len(keys) != len(set(keys)):
        raise ValueError("import-directions.toml has duplicate exceptions")
    return tuple(exceptions)


def is_namespace(value: str, namespace: str) -> bool:
    return value == namespace or value.startswith(f"{namespace}.")


def evaluate(edges: tuple[ImportEdge, ...]) -> tuple[Violation, ...]:
    violations: list[Violation] = []
    for edge in edges:
        rule: str | None = None
        if edge.source_path.startswith("src/evidrun/contracts/"):
            if edge.destination.split(".", 1)[0] in CONTRACTS_FORBIDDEN_EXTERNALS:
                rule = "PY-CONTRACTS-EXTERNALS"
            elif any(
                is_namespace(edge.destination, namespace)
                for namespace in ("evidrun.infrastructure", "evidrun.runs")
            ):
                rule = "PY-CONTRACTS-LAYERS"
        elif (
            edge.source_path.startswith("src/evidrun/shared/")
            and is_namespace(edge.destination, "evidrun")
            and not is_namespace(edge.destination, "evidrun.shared")
        ):
            rule = "PY-SHARED-UPWARD"
        elif edge.source_path.startswith("src/evidrun/infrastructure/") and is_namespace(
            edge.destination, "evidrun.runs"
        ):
            rule = "PY-INFRASTRUCTURE-RUNS"
        elif edge.source_path.startswith("apps/web/src/") and (
            edge.destination in {"electron", *NATIVE_BINDING_PACKAGES}
            or edge.destination.startswith("node:")
            or edge.destination.endswith(".node")
            or edge.destination.startswith("apps/desktop/src/main/")
            or edge.destination.startswith("apps/desktop/src/preload/")
        ):
            rule = "TS-RENDERER-NATIVE"
        elif edge.source_path.startswith("apps/desktop/src/main/") and edge.destination.startswith(
            ("apps/web/src/", "src/evidrun/", "evidrun.", "@evidrun/")
        ):
            rule = "TS-MAIN-DOMAIN"
        if rule is not None:
            violations.append(
                Violation(
                    source=edge.source_path,
                    destination=edge.destination,
                    rule=rule,
                    chain=edge.chain,
                )
            )
    return tuple(sorted(violations))


def json_report(scanned_files: int, violations: tuple[Violation, ...]) -> str:
    return json.dumps(
        {
            "schema_version": "1",
            "scanned_files": scanned_files,
            "violations": [
                {**asdict(violation), "chain": list(violation.chain)}
                for violation in violations
            ],
        },
        ensure_ascii=False,
        indent=2,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Check deterministic import directions")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        exceptions = load_exceptions(root)
        graph = build_graph(root, WorktreeSource(root))
        observed = evaluate(graph.edges)
    except (OSError, subprocess.CalledProcessError, tomllib.TOMLDecodeError, ValueError) as exc:
        print(f"CONFIG ERROR: {exc}", file=sys.stderr)
        return 2
    matched_exceptions = tuple(
        exception
        for exception in exceptions
        if any(exception.matches(violation) for violation in observed)
    )
    if len(matched_exceptions) != len(exceptions):
        print("CONFIG ERROR: import-directions.toml has a stale exception", file=sys.stderr)
        return 2
    violations = tuple(
        violation
        for violation in observed
        if not any(exception.matches(violation) for exception in exceptions)
    )
    if args.format == "json":
        print(json_report(len(graph.paths), violations))
    else:
        for exception in matched_exceptions:
            print(
                f"EXCEPTION {exception.rule}: {exception.source} -> {exception.destination} "
                f"owner={exception.owner} expires={exception.expires.isoformat()} "
                f"reason={exception.reason}"
            )
        for violation in violations:
            print(
                f"ERROR {violation.rule}: {violation.source} -> {violation.destination} "
                f"({' -> '.join(violation.chain)})",
                file=sys.stderr,
            )
        print(
            f"Import directions: {len(graph.paths)} files, {len(violations)} violations, "
            f"{len(exceptions)} exceptions"
        )
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
