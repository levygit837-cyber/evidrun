from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
import tomllib
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, cast

from import_directions_typescript import (
    TYPESCRIPT_SOURCE_SUFFIXES,
    resolve_typescript_path,
    typescript_imports,
)

SCANNED_ROOTS = ("src/evidrun", "apps/desktop/src", "apps/web/src")
CONTRACTS_FORBIDDEN_EXTERNALS = ("fastapi", "sqlalchemy", "openai", "electron", "react")
NATIVE_BINDING_PACKAGES = {"bindings", "ffi-napi", "node-gyp-build", "ref-napi"}


@dataclass(frozen=True, order=True)
class ImportEdge:
    source_path: str
    source_module: str
    destination: str
    chain: tuple[str, ...]
    imported_symbol: str | None = field(default=None, compare=False)
    bound_name: str | None = field(default=None, compare=False)


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
    for index, raw in enumerate(raw_exceptions, start=1):
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


def tracked_source_files(root: Path) -> tuple[Path, ...]:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z", "--", *SCANNED_ROOTS],
        check=True,
        capture_output=True,
    )
    relative_paths = sorted(
        path.decode("utf-8")
        for path in result.stdout.split(b"\0")
        if path
        and Path(path.decode("utf-8")).suffix in {".py", *TYPESCRIPT_SOURCE_SUFFIXES}
    )
    return tuple(root / relative for relative in relative_paths)


def python_module(path: Path, root: Path) -> str:
    relative = path.relative_to(root).with_suffix("")
    parts = relative.parts
    module_parts = parts[1:] if parts[:2] == ("src", "evidrun") else parts
    if module_parts[-1] == "__init__":
        module_parts = module_parts[:-1]
    return ".".join(module_parts)


def python_edges(path: Path, root: Path, modules: frozenset[str]) -> tuple[ImportEdge, ...]:
    source_module = python_module(path, root)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    edges: list[ImportEdge] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                edges.append(
                    ImportEdge(
                        source_path=str(path.relative_to(root)),
                        source_module=source_module,
                        destination=alias.name,
                        chain=(source_module, alias.name),
                        bound_name=alias.asname or alias.name.split(".")[0],
                    )
                )
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                package = (
                    source_module
                    if path.name == "__init__.py"
                    else source_module.rsplit(".", 1)[0]
                )
                package_parts = package.split(".")
                keep = len(package_parts) - node.level + 1
                base = ".".join(package_parts[:keep])
                destination = ".".join(part for part in (base, node.module) if part)
            else:
                destination = node.module or ""
            for alias in node.names:
                candidate = f"{destination}.{alias.name}" if destination else alias.name
                resolved = candidate if candidate in modules else destination
                if not resolved:
                    continue
                edges.append(
                    ImportEdge(
                        source_path=str(path.relative_to(root)),
                        source_module=source_module,
                        destination=resolved,
                        chain=(source_module, resolved),
                        imported_symbol=None if resolved == candidate else alias.name,
                        bound_name=alias.asname or alias.name,
                    )
                )
    return tuple(edges)


def typescript_edges(path: Path, root: Path, tracked: set[str]) -> tuple[ImportEdge, ...]:
    source_path = str(path.relative_to(root))
    destinations = typescript_imports(path.read_text(encoding="utf-8"))
    edges: list[ImportEdge] = []
    for destination in destinations:
        resolved = resolve_typescript_path(destination, path, root, tracked)
        edges.append(
            ImportEdge(
                source_path=source_path,
                source_module=source_path,
                destination=resolved,
                chain=(source_path, resolved),
            )
        )
    return tuple(edges)


def resolve_reexports(
    edge: ImportEdge,
    reexports: dict[tuple[str, str | None], tuple[str, str | None]],
) -> ImportEdge:
    destination = edge.destination
    symbol = edge.imported_symbol
    chain = list(edge.chain)
    visited: set[tuple[str, str | None]] = set()
    while True:
        key = (destination, symbol)
        preserve_symbol = False
        if key not in reexports and symbol != "*" and (destination, "*") in reexports:
            key = (destination, "*")
            preserve_symbol = True
        if key not in reexports:
            break
        if key in visited:
            break
        visited.add(key)
        destination, reexported_symbol = reexports[key]
        if not preserve_symbol:
            symbol = reexported_symbol
        chain.append(destination)
    return ImportEdge(
        source_path=edge.source_path,
        source_module=edge.source_module,
        destination=destination,
        chain=tuple(chain),
        imported_symbol=symbol,
        bound_name=edge.bound_name,
    )


def scan_edges(root: Path, files: tuple[Path, ...]) -> tuple[ImportEdge, ...]:
    modules = frozenset(python_module(path, root) for path in files if path.suffix == ".py")
    tracked = {str(path.relative_to(root)) for path in files}
    edges: list[ImportEdge] = []
    for path in files:
        if path.suffix == ".py":
            edges.extend(python_edges(path, root, modules))
        else:
            edges.extend(typescript_edges(path, root, tracked))
    reexports = {
        (edge.source_module, edge.bound_name): (edge.destination, edge.imported_symbol)
        for edge in edges
        if edge.source_path.endswith("/__init__.py") and edge.bound_name is not None
    }
    resolved_edges = [resolve_reexports(edge, reexports) for edge in edges]
    return tuple(sorted(resolved_edges))


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


def json_report(files: tuple[Path, ...], violations: tuple[Violation, ...]) -> str:
    return json.dumps(
        {
            "schema_version": "1",
            "scanned_files": len(files),
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
        files = tracked_source_files(root)
        observed = evaluate(scan_edges(root, files))
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
        print(json_report(files, violations))
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
            f"Import directions: {len(files)} files, {len(violations)} violations, "
            f"{len(exceptions)} exceptions"
        )
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
