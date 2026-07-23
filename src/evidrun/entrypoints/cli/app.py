from __future__ import annotations

import asyncio
import json
import secrets
import socket
from pathlib import Path
from typing import Annotated, Literal

import typer
import uvicorn
import yaml
from rich.console import Console
from rich.table import Table

from evidrun import __version__
from evidrun.contracts import RevisionDecisionRecord, StudyRevision, parse_revision
from evidrun.contracts.compiler import StudyCompiler
from evidrun.entrypoints.api.app import REPOSITORY_ROOT, create_app
from evidrun.evidence.bundle import EvidenceBundleService
from evidrun.experiments import ExperimentManifest
from evidrun.infrastructure.database import Database, Repository
from evidrun.infrastructure.providers import (
    OpenAIResponsesProvider,
    ProviderCredentialStore,
    ProviderRequestError,
    extract_output_text,
)
from evidrun.runs import EvidrunService
from evidrun.shared.settings import Settings
from evidrun.shared.types import utc_now

app = typer.Typer(help="Evidrun — laboratório auditável de confiabilidade de contexto.")
experiment_app = typer.Typer(help="Validar e aceitar manifests de experimento.")
contract_app = typer.Typer(help="Validar, registrar e decidir contracts revisionados.")
study_app = typer.Typer(help="Compilar Studies aceitos em RunSpecs imutáveis.")
run_app = typer.Typer(help="Executar e inspecionar runs.")
bundle_app = typer.Typer(help="Exportar e verificar evidence bundles.")
chat_app = typer.Typer(help="Inspecionar sessões de chat.")
data_app = typer.Typer(help="Inspecionar e eliminar dados gerenciados.")
provider_app = typer.Typer(help="Configurar e diagnosticar providers de modelos.")
app.add_typer(experiment_app, name="experiment")
app.add_typer(contract_app, name="contract")
app.add_typer(study_app, name="study")
app.add_typer(run_app, name="run")
app.add_typer(bundle_app, name="bundle")
app.add_typer(chat_app, name="chat")
app.add_typer(data_app, name="data")
app.add_typer(provider_app, name="provider")
console = Console()


def _components(data_dir: Path | None = None) -> tuple[Settings, Database, Repository]:
    settings = Settings.load(data_dir)
    settings.ensure_directories()
    database = Database(settings.database_path)
    database.create_all()
    return settings, database, Repository(database)


@app.callback()
def root(version: Annotated[bool, typer.Option("--version")] = False) -> None:
    if version:
        console.print(__version__)
        raise typer.Exit()


@app.command("init")
def initialize(
    data_dir: Annotated[Path | None, typer.Option("--data-dir")] = None,
) -> None:
    settings, database, _ = _components(data_dir)
    database.dispose()
    console.print(f"[green]Evidrun inicializado[/green] em {settings.data_dir}")


@app.command()
def doctor(data_dir: Annotated[Path | None, typer.Option("--data-dir")] = None) -> None:
    settings, database, _ = _components(data_dir)
    credentials = ProviderCredentialStore()
    checks = {
        "Python package": True,
        "Data directory": settings.data_dir.exists(),
        "SQLite database": settings.database_path.exists(),
        "Artifacts directory": settings.artifacts_dir.exists(),
        "CRL-CTX-002": (REPOSITORY_ROOT / "benchmarks/experiments/crl-ctx-002-demo.yaml").exists(),
        "Demo runs offline": True,
        "Default model is deepseek-v4-flash": (
            settings.default_provider.model == "deepseek-v4-flash"
        ),
        "Provider reasoning is max": settings.default_provider.reasoning_effort == "max",
        "Provider credential available": bool(credentials.get(settings.default_provider)),
    }
    database.dispose()
    table = Table(title="Evidrun doctor")
    table.add_column("Check")
    table.add_column("Resultado")
    for name, passed in checks.items():
        table.add_row(name, "OK" if passed else "FALHOU")
    console.print(table)
    if not all(checks.values()):
        raise typer.Exit(1)


@app.command()
def serve(
    host: Annotated[str, typer.Option()] = "127.0.0.1",
    port: Annotated[int, typer.Option()] = 8765,
    data_dir: Annotated[Path | None, typer.Option("--data-dir")] = None,
    desktop_handshake: Annotated[bool, typer.Option("--desktop-handshake")] = False,
) -> None:
    launch_token: str | None = None
    if desktop_handshake:
        line = input()
        handshake = json.loads(line)
        launch_token = str(handshake["token"])
        if data_dir is None and handshake.get("data_dir"):
            data_dir = Path(handshake["data_dir"])
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        listener.listen(2048)
        actual_port = listener.getsockname()[1]
        print(
            json.dumps(
                {
                    "protocol": "evidrun-desktop-v1",
                    "port": actual_port,
                    "backend_instance_id": secrets.token_hex(12),
                    "schema_version": "1",
                    "pid": __import__("os").getpid(),
                    "health_nonce": secrets.token_hex(16),
                }
            ),
            flush=True,
        )
        server = uvicorn.Server(
            uvicorn.Config(
                create_app(data_dir=data_dir, launch_token=launch_token),
                host="127.0.0.1",
                port=actual_port,
                log_level="warning",
            )
        )
        server.run(sockets=[listener])
        return
    uvicorn.run(create_app(data_dir=data_dir), host=host, port=port)


@app.command("demo")
def demo(data_dir: Annotated[Path | None, typer.Option("--data-dir")] = None) -> None:
    _, database, repository = _components(data_dir)
    result = EvidrunService(repository).bootstrap_demo(REPOSITORY_ROOT / "benchmarks")
    database.dispose()
    console.print_json(data=result)


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
    status: Annotated[Literal["draft", "proposed"], typer.Option("--status")] = "draft",
    data_dir: Annotated[Path | None, typer.Option("--data-dir")] = None,
) -> None:
    _, database, repository = _components(data_dir)
    try:
        revision = parse_revision(yaml.safe_load(path.read_text()))
        row = repository.save_contract_revision(revision, status=status)
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


@contract_app.command("accept")
def accept_contract(
    revision_id: str,
    reason: Annotated[str, typer.Option("--reason")],
    actor_id: Annotated[str, typer.Option("--actor-id")] = "local-human",
    data_dir: Annotated[Path | None, typer.Option("--data-dir")] = None,
) -> None:
    _, database, repository = _components(data_dir)
    try:
        revision = repository.get_contract_revision(revision_id)
        decision = RevisionDecisionRecord(
            revision_ref=revision.ref,
            decision="accepted",
            actor_id=actor_id,
            rationale=reason,
            decided_at_utc=utc_now(),
        )
        row = repository.decide_contract_revision(decision)
        console.print_json(
            data={
                "id": row.id,
                "decision": row.decision,
                "decision_digest": row.decision_digest,
            }
        )
    finally:
        database.dispose()


@study_app.command("compile")
def compile_study(
    revision_id: str,
    data_dir: Annotated[Path | None, typer.Option("--data-dir")] = None,
) -> None:
    _, database, repository = _components(data_dir)
    try:
        revision = repository.get_contract_revision(revision_id)
        if not isinstance(revision, StudyRevision):
            raise typer.BadParameter("contract revision is not a StudyRevision")
        registry = repository.contract_registry(revision.project_id)
        specs = StudyCompiler(registry).compile(revision)
        rows = [repository.save_run_spec(spec) for spec in specs]
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


@run_app.command("inspect")
def inspect_run(
    run_id: str,
    data_dir: Annotated[Path | None, typer.Option("--data-dir")] = None,
) -> None:
    _, database, repository = _components(data_dir)
    runs = [item for item in repository.latest_dashboard()["runs"] if item["id"] == run_id]
    if not runs:
        database.dispose()
        raise typer.BadParameter("run not found")
    console.print_json(data={**runs[0], "events": repository.get_run_events(run_id)})
    database.dispose()


@run_app.command("admit")
def admit_run_spec(
    run_spec_id: str,
    data_dir: Annotated[Path | None, typer.Option("--data-dir")] = None,
) -> None:
    _, database, repository = _components(data_dir)
    try:
        spec = repository.get_run_spec(run_spec_id)
        service = EvidrunService(repository)
        admission = service.admission_service.admit(spec)
        row = repository.save_admission_record(run_spec_id, admission)
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


@bundle_app.command("export")
def export_bundle(
    comparison_id: str,
    output: Annotated[Path | None, typer.Option("--output")] = None,
    legacy_v1: Annotated[bool, typer.Option("--legacy-v1")] = False,
    data_dir: Annotated[Path | None, typer.Option("--data-dir")] = None,
) -> None:
    settings, database, repository = _components(data_dir)
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
    settings = Settings.load(Path("/tmp/evidrun-bundle-verify"))
    database = Database(settings.database_path)
    result = EvidenceBundleService(Repository(database)).verify(path)
    database.dispose()
    console.print_json(data=result)
    if not result["valid"]:
        raise typer.Exit(1)


@chat_app.command("list")
def list_chats(data_dir: Annotated[Path | None, typer.Option("--data-dir")] = None) -> None:
    _, database, repository = _components(data_dir)
    console.print_json(data=repository.latest_dashboard()["chats"])
    database.dispose()


@data_app.command("purge")
def purge_notice() -> None:
    console.print(
        "A exclusão de artifacts exige um artifact_id explícito pela API de retenção; "
        "nenhum dado foi removido."
    )


@provider_app.command("status")
def provider_status() -> None:
    profile = Settings.load().default_provider
    credentials = ProviderCredentialStore()
    console.print_json(
        data={
            **profile.public_dict(),
            "default": True,
            "credential_available": bool(credentials.get(profile)),
            "credential_source": credentials.source(profile),
        }
    )


@provider_app.command("set-key")
def provider_set_key() -> None:
    profile = Settings.load().default_provider
    api_key = typer.prompt(
        f"API key para {profile.display_name}", hide_input=True, confirmation_prompt=True
    )
    ProviderCredentialStore().set(profile, api_key)
    console.print(f"[green]Credencial salva no Keychain[/green] para {profile.id}")


@provider_app.command("doctor")
def provider_doctor() -> None:
    profile = Settings.load().default_provider
    provider = OpenAIResponsesProvider(profile, ProviderCredentialStore())
    try:
        result = asyncio.run(provider.check())
    except (ProviderRequestError, RuntimeError) as exc:
        console.print(f"[red]Provider indisponível:[/red] {exc}")
        raise typer.Exit(1) from exc
    console.print_json(data=result)
    if not result["model_available"]:
        raise typer.Exit(1)


@provider_app.command("smoke")
def provider_smoke() -> None:
    profile = Settings.load().default_provider
    provider = OpenAIResponsesProvider(profile, ProviderCredentialStore())
    try:
        response = asyncio.run(
            provider.invoke(
                {
                    "input": "Reply with exactly: EVIDRUN_PROVIDER_OK",
                    "max_output_tokens": 64,
                }
            )
        )
    except (ProviderRequestError, RuntimeError) as exc:
        console.print(f"[red]Smoke falhou:[/red] {exc}")
        raise typer.Exit(1) from exc
    console.print_json(
        data={
            "provider": profile.id,
            "model": profile.model,
            "reasoning_effort": profile.reasoning_effort,
            "status": response.get("status"),
            "output": extract_output_text(response),
        }
    )


def main() -> None:
    app()


if __name__ == "__main__":
    main()
