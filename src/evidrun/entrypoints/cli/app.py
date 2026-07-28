"""The CLI root: platform commands, plus one sub-app per command family.

Command names and flag surfaces are contract for anyone scripting against the
CLI, so the sub-app names below reproduce the pre-extraction invocation paths
exactly (`evidrun run inspect`, `evidrun bundle verify`, and so on).
"""

from __future__ import annotations

import json
import os
import secrets
import socket
from pathlib import Path
from typing import Annotated

import typer
import uvicorn
from rich.table import Table

from evidrun import __version__
from evidrun.entrypoints.api.app import create_app
from evidrun.entrypoints.cli.commands import (
    authority_app,
    bundle_app,
    chat_app,
    contract_app,
    data_app,
    experiment_app,
    provider_app,
    run_app,
    study_app,
)
from evidrun.entrypoints.cli.shared import components, console
from evidrun.infrastructure.providers import ProviderCredentialStore
from evidrun.runs import EvidrunService
from evidrun.shared.resources import benchmarks_root

app = typer.Typer(help="Evidrun — laboratório auditável de confiabilidade de contexto.")
app.add_typer(experiment_app, name="experiment")
app.add_typer(contract_app, name="contract")
app.add_typer(study_app, name="study")
app.add_typer(run_app, name="run")
app.add_typer(bundle_app, name="bundle")
app.add_typer(chat_app, name="chat")
app.add_typer(data_app, name="data")
app.add_typer(provider_app, name="provider")
app.add_typer(authority_app, name="authority")


@app.callback()
def root(version: Annotated[bool, typer.Option("--version")] = False) -> None:
    if version:
        console.print(__version__)
        raise typer.Exit()


@app.command("init")
def initialize(
    data_dir: Annotated[Path | None, typer.Option("--data-dir")] = None,
) -> None:
    settings, database, _ = components(data_dir)
    database.dispose()
    console.print(f"[green]Evidrun inicializado[/green] em {settings.data_dir}")


@app.command()
def doctor(data_dir: Annotated[Path | None, typer.Option("--data-dir")] = None) -> None:
    settings, database, _ = components(data_dir)
    credentials = ProviderCredentialStore()
    checks = {
        "Python package": True,
        "Data directory": settings.data_dir.exists(),
        "SQLite database": settings.database_path.exists(),
        "Artifacts directory": settings.artifacts_dir.exists(),
        "CRL-CTX-002": (
            benchmarks_root() / "experiments/crl-ctx-002-demo.yaml"
        ).exists(),
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
    if desktop_handshake:
        _serve_desktop(data_dir)
        return
    uvicorn.run(create_app(data_dir=data_dir), host=host, port=port)


def _serve_desktop(data_dir: Path | None) -> None:
    """Read the launch handshake from stdin, then announce the bound port on stdout.

    The listening socket is bound before the banner is printed so the desktop shell
    never races a port that is not accepting yet.
    """

    handshake = json.loads(input())
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
                "pid": os.getpid(),
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


@app.command("demo")
def demo(data_dir: Annotated[Path | None, typer.Option("--data-dir")] = None) -> None:
    _, database, repository = components(data_dir)
    result = EvidrunService(repository).bootstrap_demo(benchmarks_root())
    database.dispose()
    console.print_json(data=result)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
