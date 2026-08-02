"""Run lifecycle, chat inspection, data retention notice, and bundle commands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, NoReturn

import typer

from evidrun.contracts.admission import admission_rejection_error
from evidrun.contracts.scope import CLI_EXIT_BY_CODE as SCOPE_CLI_EXIT_BY_CODE
from evidrun.contracts.triage import CLI_EXIT_BY_CODE, TriageRejected
from evidrun.entrypoints.cli.shared import components, console
from evidrun.evidence.bundle import EvidenceBundleService
from evidrun.evidence.verify.failures import BundleVerificationRefused
from evidrun.infrastructure.database import Database, Repository
from evidrun.infrastructure.database.ledger.transitions import RETRYABLE_RUN_STATUSES
from evidrun.infrastructure.database.queue.enqueue_errors import (
    enqueue_retry_admission_reused,
    enqueue_retry_legacy_run,
    enqueue_retry_source_succeeded,
)
from evidrun.infrastructure.database.scope_errors import ScopeStorageUnavailable
from evidrun.runs import EvidrunService
from evidrun.settings import Settings

run_app = typer.Typer(help="Executar e inspecionar runs.")
bundle_app = typer.Typer(help="Exportar e verificar evidence bundles.")
chat_app = typer.Typer(help="Inspecionar sessões de chat.")
data_app = typer.Typer(help="Inspecionar e eliminar dados gerenciados.")


def _exit_triage(rejection: TriageRejected) -> typer.Exit:
    """Print the named refusal as JSON and exit by its contract table."""

    console.print_json(data=rejection.error.model_dump(mode="json"))
    return typer.Exit(CLI_EXIT_BY_CODE[rejection.error.code])


def _exit_scope_error(exc: ScopeStorageUnavailable) -> NoReturn:
    console.print_json(data=exc.error.model_dump(mode="json"))
    raise typer.Exit(SCOPE_CLI_EXIT_BY_CODE[exc.error.code]) from exc


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
    execution_trust_id: Annotated[str, typer.Option("--execution-trust-id")],
    data_dir: Annotated[Path | None, typer.Option("--data-dir")] = None,
) -> None:
    _, database, repository = components(data_dir)
    try:
        spec = repository.read_model.get_run_spec(run_spec_id)
        trust = repository.execution_trust.get_record(execution_trust_id)
        service = EvidrunService(repository)
        admission = service.admission_service.admit(spec, trust)
        row = repository.catalog.save_admission_record(run_spec_id, admission)
        response: dict[str, Any] = {
            "id": row.id,
            "decision": admission.decision,
            "digest": admission.digest,
            "missing_requirements": admission.missing_requirements,
            "execution_trust": trust.ref.model_dump(mode="json"),
        }
        exit_code: int | None = None
        if admission.decision == "rejected":
            error = admission_rejection_error(admission)
            response["error"] = error.model_dump(mode="json")
            exit_code = int(CLI_EXIT_BY_CODE[error.code])
        console.print_json(data=response)
        if exit_code is not None:
            raise typer.Exit(exit_code)
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
        try:
            run_id, job = EvidrunService(repository).runtime.coordinator.enqueue(
                run_spec_id=run_spec_id,
                admission_id=admission_id,
                idempotency_key=idempotency_key,
            )
        except TriageRejected as exc:
            raise _exit_triage(exc) from exc
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
        try:
            source = repository.read_model.get_run(run_id)
            if source.run_spec_id is None:
                raise enqueue_retry_legacy_run()
            if source.status not in RETRYABLE_RUN_STATUSES:
                raise enqueue_retry_source_succeeded()
            if source.admission_id == admission_id:
                raise enqueue_retry_admission_reused()
            new_run_id, job = EvidrunService(repository).runtime.coordinator.enqueue(
                run_spec_id=source.run_spec_id,
                admission_id=admission_id,
                idempotency_key=idempotency_key,
                retry_of=run_id,
            )
        except TriageRejected as exc:
            raise _exit_triage(exc) from exc
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
    try:
        result = EvidenceBundleService(Repository(database)).verify(path)
    except BundleVerificationRefused as exc:
        # A bundle that cannot be verified at all is still an invalid bundle, not an
        # unexpected defect: print the named refusal in the same shape and keep exit 1.
        console.print_json(data=exc.document())
        raise typer.Exit(1) from exc
    finally:
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
        EvidenceBundleService(repository).export_run(run_id, target)
        console.print(str(target))
    finally:
        database.dispose()


@chat_app.command("list")
def list_chats(
    workspace_id: Annotated[str, typer.Option("--workspace-id")],
    data_dir: Annotated[Path | None, typer.Option("--data-dir")] = None,
) -> None:
    _, database, repository = components(data_dir)
    try:
        try:
            documents = repository.read_model.list_chat_sessions(workspace_id)
        except ScopeStorageUnavailable as exc:
            _exit_scope_error(exc)
        console.print_json(data=documents)
    finally:
        database.dispose()


@data_app.command("purge")
def purge_notice() -> None:
    console.print(
        "A exclusão de artifacts exige um artifact_id explícito pela API de retenção; "
        "nenhum dado foi removido."
    )
