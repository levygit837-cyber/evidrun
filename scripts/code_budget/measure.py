"""Measure the three budget metrics per tracked file.

Only files git tracks are measured. An unstaged new file is invisible to the gate,
which is exactly why a violation can appear only after `git add`.
"""

from __future__ import annotations

import ast
import subprocess
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from code_budget.policy import Metric, Policy

FunctionDef = ast.FunctionDef | ast.AsyncFunctionDef
NESTING = ast.If | ast.Try | ast.With | ast.For | ast.While


@dataclass(frozen=True, slots=True)
class Measurement:
    """Métricas de um arquivo. Chave ausente = métrica não aplicável ao arquivo."""

    path: str
    metrics: Mapping[Metric, int] = field(default_factory=dict[Metric, int])
    details: Mapping[Metric, str] = field(default_factory=dict[Metric, str])
    syntax_error: str | None = None


def tracked_files(root: Path) -> list[str]:
    """Arquivos versionados, na ordem do git, sem walk do filesystem."""

    completed = subprocess.run(
        ("git", "ls-files", "-z"), cwd=root, check=True, capture_output=True
    )
    return [entry for entry in completed.stdout.decode("utf-8").split("\0") if entry]


def measure_file(root: Path, relative: str) -> Measurement:
    """Mede um arquivo. Métricas de função e classe existem só para Python."""

    text = (root / relative).read_text(encoding="utf-8")
    metrics: dict[Metric, int] = {"file_lines": len(text.splitlines())}
    if not relative.endswith(".py"):
        return Measurement(path=relative, metrics=metrics, details={})
    try:
        tree = ast.parse(text, filename=relative)
    except SyntaxError as exc:
        return Measurement(path=relative, metrics=metrics, details={}, syntax_error=str(exc))
    details: dict[Metric, str] = {}
    scans: tuple[tuple[Metric, tuple[str | None, int]], ...] = (
        ("function_lines", _longest_function(tree)),
        ("public_methods", _largest_class(tree)),
    )
    for metric, (name, value) in scans:
        metrics[metric] = value
        if name is not None:
            details[metric] = name
    return Measurement(path=relative, metrics=metrics, details=details)


def measure_all(root: Path, policy: Policy, files: Iterable[str]) -> list[Measurement]:
    """Mede só os arquivos que caem em algum grupo com orçamento."""

    measurements: list[Measurement] = []
    for relative in files:
        group = policy.group_for(relative)
        if group is None or group.exempt or not (root / relative).is_file():
            continue
        measurements.append(measure_file(root, relative))
    return measurements


def _longest_function(tree: ast.Module) -> tuple[str | None, int]:
    winner: str | None = None
    longest = 0
    for node, scope in _walk_scopes(tree.body, ()):
        if isinstance(node, FunctionDef):
            span = (node.end_lineno or node.lineno) - node.lineno + 1
            if span > longest:
                longest, winner = span, ".".join((*scope, node.name))
    return winner, longest


def _largest_class(tree: ast.Module) -> tuple[str | None, int]:
    winner: str | None = None
    largest = 0
    for node, scope in _walk_scopes(tree.body, ()):
        if not isinstance(node, ast.ClassDef):
            continue
        public = sum(
            1
            for child in node.body
            if isinstance(child, FunctionDef) and not child.name.startswith("_")
        )
        if public > largest:
            largest, winner = public, ".".join((*scope, node.name))
    return winner, largest


def _walk_scopes(
    body: Sequence[ast.stmt], scope: tuple[str, ...]
) -> Iterable[tuple[ast.stmt, tuple[str, ...]]]:
    """Percorre defs de função e classe mantendo o nome qualificado do escopo."""

    for node in body:
        if isinstance(node, FunctionDef | ast.ClassDef):
            yield node, scope
            yield from _walk_scopes(node.body, (*scope, node.name))
        elif isinstance(node, NESTING):
            yield from _walk_scopes(node.body, scope)
