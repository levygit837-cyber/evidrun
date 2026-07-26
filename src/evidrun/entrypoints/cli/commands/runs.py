"""Run lifecycle, chat inspection, data retention notice, and bundle commands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from evidrun.entrypoints.cli.shared import components, console
from evidrun.evidence.bundle import EvidenceBundleService
from evidrun.infrastructure.database import Database, Repository
from evidrun.runs import EvidrunService
from evidrun.settings import Settings

run_app = typer.Typer(help="Executar e inspecionar runs.")
bundle_app = typer.Typer(help="Exportar e verificar evidence bundles.")
chat_app = typer.Typer(help="Inspecionar sessões de chat.")
data_app = typer.Typer(help="Inspecionar e eliminar dados gerenciados.")


@run_app.command("inspect")
def inspect_run(
    run_id: str,
    data_dir: Annotated[Path | None, typer.Option("--data-dir")] = None,
) -> None:
    _, database, repository = components(data_dir)
    runs = [r for r in repository.read_model.latest_dashboard()["runs"] if r["id"] == run_id]
    if not runs:
        database.dispose()
        raise typer.BadParameter("run not found")
    execution = repository.lease.get_run_execution(run_id)
    try:
        subject_envelope_digest = repository.read_model.get_subject_envelope(run_id).digest
    except KeyError:
        subject_envelope_digest = None
    console.print_json(
        data={
            **runs[0],
            "events": repository.read_model.get_run_events(run_id),
            "execution": (
                {
                    "job": execution[0].model_dump(mode="json"),
                    "attempts": [item.model_dump(mode="json") for item in execution[1]],
                }
                if execution is not None
                else None
            ),
            "subject_envelope_digest": subject_envelope_digest,
        }
    )
    database.dispose()


@run_app.command("admit")
def admit_run_spec(
    run_spec_id: str,
    data_dir: Annotated[Path | None, typer.Option("--data-dir")] = None,
) -> None:
    _, database, repository = components(data_dir)
    try:
        spec = repository.read_model.get_run_spec(run_spec_id)
        service = EvidrunService(repository)
        admission = service.admission_service.admit(spec)
        row = repository.catalog.save_admission_record(run_spec_id, admission)
        console.print_json(
            data={
                "id": row.id,
                "decision": admission.decision,
                "digest": admission.digest,
                "missing_requirements": admission.missing_requirements,
            }
        )
    finally:
        database.dispose()


@run_app.command("enqueue")
def enqueue_run(
    run_spec_id: str,
    admission_id: Annotated[str, typer.Option("--admission-id")],
    idempotency_key: Annotated[str, typer.Option("--idempotency-key")],
    data_dir: Annotated[Path | None, typer.Option("--data-dir")] = None,
) -> None:
    _, database, repository = components(data_dir)
    try:
        run_id, job = EvidrunService(repository).runtime.coordinator.enqueue(
            run_spec_id=run_spec_id,
            admission_id=admission_id,
            idempotency_key=idempotency_key,
        )
        console.print_json(
            data={
                "run_id": run_id,
                "job_id": job.job_id,
                "run_spec_id": run_spec_id,
                "admission_id": admission_id,
                "retry_of": None,
                "status": job.status,
            }
        )
    finally:
        database.dispose()


@run_app.command("retry")
def retry_run(
    run_id: str,
    admission_id: Annotated[str, typer.Option("--admission-id")],
    idempotency_key: Annotated[str, typer.Option("--idempotency-key")],
    data_dir: Annotated[Path | None, typer.Option("--data-dir")] = None,
) -> None:
    _, database, repository = components(data_dir)
    try:
        source = repository.read_model.get_run(run_id)
        if source.run_spec_id is None:
            raise typer.BadParameter("legacy Run is not eligible for retry")
        if source.admission_id == admission_id:
            raise typer.BadParameter("retry requires a new AdmissionRecord")
        new_run_id, job = EvidrunService(repository).runtime.coordinator.enqueue(
            run_spec_id=source.run_spec_id,
            admission_id=admission_id,
            idempotency_key=idempotency_key,
            retry_of=run_id,
        )
        console.print_json(
            data={
                "run_id": new_run_id,
                "job_id": job.job_id,
                "run_spec_id": source.run_spec_id,
                "admission_id": admission_id,
                "retry_of": run_id,
                "status": job.status,
            }
        )
    finally:
        database.dispose()


@bundle_app.command("export")
def export_bundle(
    comparison_id: str,
    output: Annotated[Path | None, typer.Option("--output")] = None,
    legacy_v1: Annotated[bool, typer.Option("--legacy-v1")] = False,
    data_dir: Annotated[Path | None, typer.Option("--data-dir")] = None,
) -> None:
    settings, database, repository = components(data_dir)
    target = output or settings.data_dir / "exports" / f"{comparison_id}.evidrun.zip"
    bundle_service = EvidenceBundleService(repository)
    if legacy_v1:
        bundle_service.export_comparison(comparison_id, target)
    else:
        bundle_service.export_comparison_v2(comparison_id, target)
    database.dispose()
    console.print(str(target))


@bundle_app.command("verify")
def verify_bundle(path: Path) -> None:
    # Verification reads only the bundle, so it deliberately uses a scratch
    # database. A docstring here would become Typer help text and change the
    # observable `--help` surface.
    settings = Settings.load(Path("/tmp/evidrun-bundle-verify"))
    database = Database(settings.database_path)
    result = EvidenceBundleService(Repository(database)).verify(path)
    database.dispose()
    console.print_json(data=result)
    if not result["valid"]:
        raise typer.Exit(1)


@bundle_app.command("export-run")
def export_run_bundle(
    run_id: str,
    output: Annotated[Path | None, typer.Option("--output")] = None,
    data_dir: Annotated[Path | None, typer.Option("--data-dir")] = None,
) -> None:
    settings, database, repository = components(data_dir)
    try:
        target = output or settings.data_dir / "exports" / f"{run_id}.evidrun.zip"
        EvidenceBundleService(repository).export_run_v3(run_id, target)
        console.print(str(target))
    finally:
        database.dispose()


@chat_app.command("list")
def list_chats(data_dir: Annotated[Path | None, typer.Option("--data-dir")] = None) -> None:
    _, database, repository = components(data_dir)
    console.print_json(data=repository.read_model.latest_dashboard()["chats"])
    database.dispose()


@data_app.command("purge")
def purge_notice() -> None:
    console.print(
        "A exclusão de artifacts exige um artifact_id explícito pela API de retenção; "
        "nenhum dado foi removido."
    )
