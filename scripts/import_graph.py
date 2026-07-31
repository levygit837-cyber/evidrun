"""Normalized import graph over versioned sources.

This module owns edge construction only. Direction policy lives in
`check_import_directions.py` and the warning-only metrics live in
`dependency_report/`, so both read the same graph instead of building a second one.

A `SourceTree` decouples edge construction from the working tree: the same scan
runs against the checkout or against an arbitrary revision, which is what lets a
report name the edges a branch adds without checking that revision out.
"""

from __future__ import annotations

import ast
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Protocol

from import_directions_typescript import (
    TYPESCRIPT_SOURCE_SUFFIXES,
    resolve_typescript_path,
    typescript_imports,
)

SCANNED_ROOTS = ("src/evidrun", "apps/desktop/src", "apps/web/src")
SOURCE_SUFFIXES = frozenset({".py", *TYPESCRIPT_SOURCE_SUFFIXES})


@dataclass(frozen=True, order=True)
class ImportEdge:
    source_path: str
    source_module: str
    destination: str
    chain: tuple[str, ...]
    imported_symbol: str | None = field(default=None, compare=False)
    bound_name: str | None = field(default=None, compare=False)


class SourceTree(Protocol):
    """A read-only set of versioned source files."""

    def paths(self) -> tuple[str, ...]:
        """Repository-relative POSIX paths, sorted, restricted to scanned roots."""
        ...

    def read(self, path: str) -> str:
        """Text of one path returned by `paths`."""
        ...


@dataclass(frozen=True)
class WorktreeSource:
    """Files tracked by the index, read from disk."""

    root: Path

    def paths(self) -> tuple[str, ...]:
        output = _git_bytes(self.root, "ls-files", "-z", "--", *SCANNED_ROOTS)
        return _scanned_paths(
            entry.decode("utf-8") for entry in output.split(b"\0") if entry
        )

    def read(self, path: str) -> str:
        return (self.root / path).read_text(encoding="utf-8")


@dataclass(frozen=True)
class RevisionSource:
    """Files recorded in a commit, read through `git show` without a checkout."""

    root: Path
    revision: str

    def paths(self) -> tuple[str, ...]:
        output = _git_bytes(
            self.root, "ls-tree", "-r", "-z", "--name-only", self.revision, "--", *SCANNED_ROOTS
        )
        return _scanned_paths(
            entry.decode("utf-8") for entry in output.split(b"\0") if entry
        )

    def read(self, path: str) -> str:
        blob = _git_bytes(self.root, "show", f"{self.revision}:{path}")
        return blob.decode("utf-8", errors="replace")


def _scanned_paths(entries: Iterable[str]) -> tuple[str, ...]:
    return tuple(
        sorted(path for path in entries if PurePosixPath(path).suffix in SOURCE_SUFFIXES)
    )


def _git_bytes(root: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
    )
    return result.stdout


def python_module(path: str) -> str:
    parts = PurePosixPath(path).with_suffix("").parts
    module_parts = parts[1:] if parts[:2] == ("src", "evidrun") else parts
    if module_parts[-1] == "__init__":
        module_parts = module_parts[:-1]
    return ".".join(module_parts)


def python_edges(path: str, text: str, modules: frozenset[str]) -> tuple[ImportEdge, ...]:
    source_module = python_module(path)
    tree = ast.parse(text, filename=path)
    edges: list[ImportEdge] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                edges.append(
                    ImportEdge(
                        source_path=path,
                        source_module=source_module,
                        destination=alias.name,
                        chain=(source_module, alias.name),
                        bound_name=alias.asname or alias.name.split(".")[0],
                    )
                )
        elif isinstance(node, ast.ImportFrom):
            destination = _import_from_destination(node, path, source_module)
            for alias in node.names:
                candidate = f"{destination}.{alias.name}" if destination else alias.name
                resolved = candidate if candidate in modules else destination
                if not resolved:
                    continue
                edges.append(
                    ImportEdge(
                        source_path=path,
                        source_module=source_module,
                        destination=resolved,
                        chain=(source_module, resolved),
                        imported_symbol=None if resolved == candidate else alias.name,
                        bound_name=alias.asname or alias.name,
                    )
                )
    return tuple(edges)


def _import_from_destination(node: ast.ImportFrom, path: str, source_module: str) -> str:
    if not node.level:
        return node.module or ""
    package = (
        source_module
        if PurePosixPath(path).name == "__init__.py"
        else source_module.rsplit(".", 1)[0]
    )
    package_parts = package.split(".")
    keep = len(package_parts) - node.level + 1
    base = ".".join(package_parts[:keep])
    return ".".join(part for part in (base, node.module) if part)


def typescript_edges(
    path: str, text: str, root: Path, tracked: set[str]
) -> tuple[ImportEdge, ...]:
    edges: list[ImportEdge] = []
    for destination in typescript_imports(text):
        resolved = resolve_typescript_path(destination, root / path, root, tracked)
        edges.append(
            ImportEdge(
                source_path=path,
                source_module=path,
                destination=resolved,
                chain=(path, resolved),
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


@dataclass(frozen=True)
class ImportGraph:
    """Every edge resolved from one source tree, plus the nodes it was built from."""

    paths: tuple[str, ...]
    edges: tuple[ImportEdge, ...]
    python_modules: frozenset[str]

    def internal_destinations(self) -> frozenset[str]:
        """Destinations that name a node of this graph rather than an external package."""
        return frozenset(self.python_modules) | frozenset(self.paths)


def build_graph(root: Path, source: SourceTree) -> ImportGraph:
    paths = source.paths()
    modules = frozenset(python_module(path) for path in paths if path.endswith(".py"))
    tracked = set(paths)
    edges: list[ImportEdge] = []
    for path in paths:
        text = source.read(path)
        if path.endswith(".py"):
            edges.extend(python_edges(path, text, modules))
        else:
            edges.extend(typescript_edges(path, text, root, tracked))
    reexports: dict[tuple[str, str | None], tuple[str, str | None]] = {
        (edge.source_module, edge.bound_name): (edge.destination, edge.imported_symbol)
        for edge in edges
        if edge.source_path.endswith("/__init__.py") and edge.bound_name is not None
    }
    resolved = tuple(sorted(resolve_reexports(edge, reexports) for edge in edges))
    return ImportGraph(paths=paths, edges=resolved, python_modules=modules)
