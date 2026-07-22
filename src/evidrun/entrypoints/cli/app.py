from __future__ import annotations

import json
import secrets
import socket
from pathlib import Path
from typing import Annotated

import typer
import uvicorn
import yaml
from rich.console import Console
from rich.table import Table

from evidrun import __version__
from evidrun.entrypoints.api.app import REPOSITORY_ROOT, create_app
from evidrun.evidence.bundle import EvidenceBundleService
from evidrun.experiments import ExperimentManifest
from evidrun.infrastructure.database import Database, Repository
from evidrun.runs import EvidrunService
from evidrun.shared.settings import Settings

app = typer.Typer(help="Evidrun — laboratório auditável de confiabilidade de contexto.")
experiment_app = typer.Typer(help="Validar e aceitar manifests de experimento.")
run_app = typer.Typer(help="Executar e inspecionar runs.")
bundle_app = typer.Typer(help="Exportar e verificar evidence bundles.")
chat_app = typer.Typer(help="Inspecionar sessões de chat.")
data_app = typer.Typer(help="Inspecionar e eliminar dados gerenciados.")
app.add_typer(experiment_app, name="experiment")
app.add_typer(run_app, name="run")
app.add_typer(bundle_app, name="bundle")
app.add_typer(chat_app, name="chat")
app.add_typer(data_app, name="data")
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
    checks = {
        "Python package": True,
        "Data directory": settings.data_dir.exists(),
        "SQLite database": settings.database_path.exists(),
        "Artifacts directory": settings.artifacts_dir.exists(),
        "CRL-CTX-002": (REPOSITORY_ROOT / "benchmarks/experiments/crl-ctx-002-demo.yaml").exists(),
        "Demo runs offline": True,
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


@bundle_app.command("export")
def export_bundle(
    comparison_id: str,
    output: Annotated[Path | None, typer.Option("--output")] = None,
    data_dir: Annotated[Path | None, typer.Option("--data-dir")] = None,
) -> None:
    settings, database, repository = _components(data_dir)
    target = output or settings.data_dir / "exports" / f"{comparison_id}.evidrun.zip"
    EvidenceBundleService(repository).export_comparison(comparison_id, target)
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


def main() -> None:
    app()


if __name__ == "__main__":
    main()
