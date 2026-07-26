"""Experiment, contract, and study commands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
import yaml

from evidrun.contracts import StudyRevision, parse_revision
from evidrun.contracts.compiler import StudyCompiler
from evidrun.contracts.triage import CLI_EXIT_BY_CODE
from evidrun.entrypoints.cli.shared import components, console
from evidrun.experiments import ExperimentManifest
from evidrun.infrastructure.database.register_errors import RegisterRejected

experiment_app = typer.Typer(help="Validar e aceitar manifests de experimento.")
contract_app = typer.Typer(help="Validar, registrar e decidir contracts revisionados.")
study_app = typer.Typer(help="Compilar Studies aceitos em RunSpecs imutáveis.")


@experiment_app.command("validate")
def validate_experiment(path: Path) -> None:
    manifest = ExperimentManifest.model_validate(yaml.safe_load(path.read_text()))
    console.print_json(
        data={"valid": True, "digest": manifest.digest, "validity": manifest.validity}
    )


@contract_app.command("validate")
def validate_contract(path: Path) -> None:
    revision = parse_revision(yaml.safe_load(path.read_text()))
    console.print_json(
        data={
            "valid": True,
            "digest": revision.digest,
            "normalized": revision.semantic_document(),
        }
    )


@contract_app.command("register")
def register_contract(
    path: Path,
    status: Annotated[str, typer.Option("--status")] = "draft",
    data_dir: Annotated[Path | None, typer.Option("--data-dir")] = None,
) -> None:
    _, database, repository = components(data_dir)
    try:
        revision = parse_revision(yaml.safe_load(path.read_text()))
        try:
            row = repository.registry.save_contract_revision(revision, status=status)
        except RegisterRejected as exc:
            console.print_json(data=exc.error.model_dump(mode="json"))
            raise typer.Exit(CLI_EXIT_BY_CODE[exc.error.code]) from exc
        console.print_json(
            data={
                "id": row.id,
                "contract_type": row.contract_type,
                "logical_id": row.logical_id,
                "revision": row.revision,
                "digest": row.digest,
                "status": row.status,
            }
        )
    finally:
        database.dispose()


@study_app.command("compile")
def compile_study(
    revision_id: str,
    data_dir: Annotated[Path | None, typer.Option("--data-dir")] = None,
) -> None:
    _, database, repository = components(data_dir)
    try:
        revision = repository.read_model.get_contract_revision(revision_id)
        if not isinstance(revision, StudyRevision):
            raise typer.BadParameter("contract revision is not a StudyRevision")
        registry = repository.registry.contract_registry(revision.project_id)
        specs = StudyCompiler(registry).compile(revision)
        rows = [repository.catalog.save_run_spec(spec) for spec in specs]
        console.print_json(
            data=[
                {
                    "id": row.id,
                    "digest": row.digest,
                    "variant_id": row.variant_id,
                    "scenario_id": row.scenario_logical_id,
                    "repetition_index": row.repetition_index,
                }
                for row in rows
            ]
        )
    finally:
        database.dispose()
