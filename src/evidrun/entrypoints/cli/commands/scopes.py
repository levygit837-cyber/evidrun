"""Workspace and Project commands over the shared catalog contracts."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, NoReturn

import typer

from evidrun.contracts.scope import CLI_EXIT_BY_CODE
from evidrun.entrypoints.cli.shared import components, console
from evidrun.infrastructure.database.read_model import projections
from evidrun.infrastructure.database.scope_errors import (
    ScopeRejected,
    ScopeStorageUnavailable,
)

workspace_app = typer.Typer(help="Criar e listar Workspaces.")
project_app = typer.Typer(help="Criar e listar Projects.")


def _exit_scope_error(exc: ScopeRejected | ScopeStorageUnavailable) -> NoReturn:
    console.print_json(data=exc.error.model_dump(mode="json"))
    raise typer.Exit(CLI_EXIT_BY_CODE[exc.error.code]) from exc


@workspace_app.command("create")
def create_workspace(
    name: str,
    data_dir: Annotated[Path | None, typer.Option("--data-dir")] = None,
) -> None:
    _, database, repository = components(data_dir)
    try:
        try:
            row = repository.catalog.create_workspace(name)
        except (ScopeRejected, ScopeStorageUnavailable) as exc:
            _exit_scope_error(exc)
        console.print_json(data=projections.workspace_document(row))
    finally:
        database.dispose()


@workspace_app.command("list")
def list_workspaces(
    data_dir: Annotated[Path | None, typer.Option("--data-dir")] = None,
) -> None:
    _, database, repository = components(data_dir)
    try:
        try:
            documents = repository.read_model.list_workspaces()
        except (ScopeRejected, ScopeStorageUnavailable) as exc:
            _exit_scope_error(exc)
        console.print_json(data=documents)
    finally:
        database.dispose()


@project_app.command("create")
def create_project(
    workspace_id: str,
    name: str,
    data_dir: Annotated[Path | None, typer.Option("--data-dir")] = None,
) -> None:
    _, database, repository = components(data_dir)
    try:
        try:
            row = repository.catalog.create_project(workspace_id, name)
        except (ScopeRejected, ScopeStorageUnavailable) as exc:
            _exit_scope_error(exc)
        console.print_json(data=projections.project_document(row))
    finally:
        database.dispose()


@project_app.command("list")
def list_projects(
    workspace_id: Annotated[str | None, typer.Option("--workspace-id")] = None,
    data_dir: Annotated[Path | None, typer.Option("--data-dir")] = None,
) -> None:
    _, database, repository = components(data_dir)
    try:
        try:
            documents = repository.read_model.list_projects(workspace_id)
        except (ScopeRejected, ScopeStorageUnavailable) as exc:
            _exit_scope_error(exc)
        console.print_json(data=documents)
    finally:
        database.dispose()
