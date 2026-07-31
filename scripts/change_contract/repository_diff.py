"""Materialize contract surfaces before and after the Git merge-base."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path, PurePosixPath

from .git import GitChange, GitSnapshot
from .openapi_diff import compare_openapi
from .python_diff import compare_migration_surface, compare_python_surface
from .schema_diff import (
    Compatibility,
    ContractChange,
    ContractDiffReport,
    ContractSurface,
    SchemaDiffError,
    compare_json_schema,
)


class RepositoryDiffError(RuntimeError):
    """A changed contract surface could not be materialized safely."""

    def __init__(self, path: str, message: str) -> None:
        self.path = path
        super().__init__(message)


def detect_repository_contract_diffs(
    snapshot: GitSnapshot,
) -> tuple[ContractDiffReport, ...]:
    """Return deterministic semantic reports for recognized changed surfaces."""

    reports: list[ContractDiffReport] = []
    for change in snapshot.changes:
        report = _detect_change(snapshot, change)
        if report is not None and report.changes:
            reports.append(report)
    return tuple(sorted(reports, key=lambda item: (item.path, item.surface.value)))


def _detect_change(
    snapshot: GitSnapshot,
    change: GitChange,
) -> ContractDiffReport | None:
    old_path = change.old_path or change.path
    old_text = _baseline_text(snapshot, old_path)
    candidate_path = snapshot.root / change.path
    new_text = _worktree_text(snapshot.root, change.path) if candidate_path.is_file() else None
    old_surface = _surface(old_path, old_text) if old_text is not None else None
    new_surface = _surface(change.path, new_text) if new_text is not None else None
    if (
        old_text is not None
        and new_text is not None
        and _declares_exports(old_path, old_text)
        != _declares_exports(change.path, new_text)
    ):
        return ContractDiffReport(
            change.path,
            ContractSurface.EXPORT,
            (
                ContractChange(
                    "explicit-exports-changed",
                    Compatibility.BREAKING,
                    "/__all__",
                    "A declaracao explicita de exports __all__ foi adicionada ou removida.",
                ),
            ),
        )
    if (
        old_text is not None
        and new_text is not None
        and _declares_exports(old_path, old_text)
        and _declares_exports(change.path, new_text)
    ):
        old_surface = new_surface = ContractSurface.EXPORT
    if old_path.startswith("alembic/") or change.path.startswith("alembic/"):
        try:
            return compare_migration_surface(
                old_text or "",
                new_text or "",
                path=change.path,
            )
        except SchemaDiffError as error:
            raise RepositoryDiffError(change.path, str(error)) from error
    if old_surface is None and new_surface is None:
        return None
    if old_surface != new_surface or old_text is None or new_text is None:
        return _file_level_report(change, old_surface, new_surface)
    assert new_surface is not None
    try:
        return _compare_text(old_text, new_text, change.path, new_surface)
    except (SchemaDiffError, json.JSONDecodeError) as error:
        raise RepositoryDiffError(change.path, str(error)) from error


def _compare_text(
    baseline: str,
    candidate: str,
    path: str,
    surface: ContractSurface,
) -> ContractDiffReport:
    if surface is ContractSurface.JSON_SCHEMA:
        return compare_json_schema(json.loads(baseline), json.loads(candidate), path=path)
    if surface is ContractSurface.OPENAPI:
        return compare_openapi(json.loads(baseline), json.loads(candidate), path=path)
    if surface in {
        ContractSurface.PERSISTED_MODEL,
        ContractSurface.EVENT,
        ContractSurface.CLI,
        ContractSurface.EXPORT,
    }:
        return compare_python_surface(baseline, candidate, path=path, surface=surface)
    raise RepositoryDiffError(path, f"superficie sem comparador: {surface.value}")


def _file_level_report(
    change: GitChange,
    old_surface: ContractSurface | None,
    new_surface: ContractSurface | None,
) -> ContractDiffReport:
    if new_surface is None:
        surface = old_surface
        kind = "surface-removed"
        compatibility = Compatibility.BREAKING
        message = "Uma superficie contratual foi removida."
    elif old_surface is None:
        surface = new_surface
        kind = "surface-added"
        compatibility = Compatibility.ADDITIVE
        message = "Uma superficie contratual foi adicionada."
    else:
        surface = new_surface
        kind = "surface-kind-changed"
        compatibility = Compatibility.BREAKING
        message = "O tipo da superficie contratual mudou."
    assert surface is not None
    return ContractDiffReport(
        change.path,
        surface,
        (ContractChange(kind, compatibility, "/", message),),
    )


def _surface(path: str, text: str | None) -> ContractSurface | None:
    pure = PurePosixPath(path)
    if path.startswith("schemas/") and pure.suffix == ".json":
        if "openapi" in pure.name.lower() or (text is not None and '"openapi"' in text[:1000]):
            return ContractSurface.OPENAPI
        return ContractSurface.JSON_SCHEMA
    if path.startswith("alembic/") and pure.suffix == ".py":
        return ContractSurface.PERSISTED_MODEL
    if pure.name == "models.py" and text is not None and "Mapped[" in text:
        return ContractSurface.PERSISTED_MODEL
    if path.startswith("src/evidrun/contracts/") and pure.name in {
        "events.py",
        "event.py",
    }:
        return ContractSurface.EVENT
    if path.startswith("src/evidrun/entrypoints/cli/") and pure.suffix == ".py":
        return ContractSurface.CLI
    if path.startswith("src/evidrun/") and (
        pure.name == "__init__.py" or (text is not None and "__all__" in text)
    ):
        return ContractSurface.EXPORT
    return None


def _declares_exports(path: str, text: str) -> bool:
    pure = PurePosixPath(path)
    return path.startswith("src/evidrun/") and pure.suffix == ".py" and "__all__" in text


def _baseline_text(snapshot: GitSnapshot, path: str) -> str | None:
    object_name = f"{snapshot.merge_base}:{path}"
    exists = subprocess.run(
        ("git", "cat-file", "-e", object_name),
        cwd=snapshot.root,
        check=False,
        capture_output=True,
    )
    if exists.returncode != 0:
        return None
    result = subprocess.run(
        ("git", "show", object_name),
        cwd=snapshot.root,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        error = result.stderr.decode("utf-8", errors="replace").strip()
        raise RepositoryDiffError(path, f"nao foi possivel ler baseline: {error}")
    try:
        return result.stdout.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise RepositoryDiffError(path, "baseline nao e UTF-8") from error


def _worktree_text(root: Path, path: str) -> str:
    try:
        return (root / path).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise RepositoryDiffError(path, f"nao foi possivel ler candidate: {error}") from error
