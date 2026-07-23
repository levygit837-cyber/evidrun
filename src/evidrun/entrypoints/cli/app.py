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
from evidrun.authority.authenticator import KeyringAuthenticator
from evidrun.authority.policy import AuthorityMode
from evidrun.authority.repository import AuthorityRepository
from evidrun.authority.service import HumanAuthorityService
from evidrun.authority.subject import RevisionDecisionSubject
from evidrun.authority.verifier import LocalWebAuthnVerifier
from evidrun.contracts import StudyRevision, parse_revision
from evidrun.contracts.compiler import StudyCompiler
from evidrun.entrypoints.api.app import REPOSITORY_ROOT, create_app
from evidrun.evidence.bundle import EvidenceBundleService
from evidrun.experiments import ExperimentManifest
from evidrun.infrastructure.artifacts.store import ArtifactStore
from evidrun.infrastructure.database import Database, Repository
from evidrun.infrastructure.providers import (
    OpenAIResponsesProvider,
    ProviderCredentialStore,
    ProviderRequestError,
    extract_output_text,
)
from evidrun.runs import EvidrunService
from evidrun.shared.settings import Settings

app = typer.Typer(help="Evidrun — laboratório auditável de confiabilidade de contexto.")
experiment_app = typer.Typer(help="Validar e aceitar manifests de experimento.")
contract_app = typer.Typer(help="Validar, registrar e decidir contracts revisionados.")
study_app = typer.Typer(help="Compilar Studies aceitos em RunSpecs imutáveis.")
run_app = typer.Typer(help="Executar e inspecionar runs.")
bundle_app = typer.Typer(help="Exportar e verificar evidence bundles.")
chat_app = typer.Typer(help="Inspecionar sessões de chat.")
data_app = typer.Typer(help="Inspecionar e eliminar dados gerenciados.")
provider_app = typer.Typer(help="Configurar e diagnosticar providers de modelos.")
authority_app = typer.Typer(help="Enrollar credenciais e confirmar autoridade humana.")
app.add_typer(experiment_app, name="experiment")
app.add_typer(contract_app, name="contract")
app.add_typer(study_app, name="study")
app.add_typer(run_app, name="run")
app.add_typer(bundle_app, name="bundle")
app.add_typer(chat_app, name="chat")
app.add_typer(data_app, name="data")
app.add_typer(provider_app, name="provider")
app.add_typer(authority_app, name="authority")
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
    data_dir: Annotated[Path | None, typer.Option("--data-dir")] = None,
) -> None:
    del revision_id, reason, data_dir
    console.print(
        "Verified human authority is unavailable. "
        "A trusted WebAuthn verifier must complete contract acceptance."
    )
    raise typer.Exit(code=1)


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
    execution = repository.get_run_execution(run_id)
    try:
        subject_envelope_digest = repository.get_subject_envelope(run_id).digest
    except KeyError:
        subject_envelope_digest = None
    console.print_json(
        data={
            **runs[0],
            "events": repository.get_run_events(run_id),
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


@run_app.command("enqueue")
def enqueue_run(
    run_spec_id: str,
    admission_id: Annotated[str, typer.Option("--admission-id")],
    idempotency_key: Annotated[str, typer.Option("--idempotency-key")],
    data_dir: Annotated[Path | None, typer.Option("--data-dir")] = None,
) -> None:
    _, database, repository = _components(data_dir)
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
    _, database, repository = _components(data_dir)
    try:
        source = repository.get_run(run_id)
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


@bundle_app.command("export-run")
def export_run_bundle(
    run_id: str,
    output: Annotated[Path | None, typer.Option("--output")] = None,
    data_dir: Annotated[Path | None, typer.Option("--data-dir")] = None,
) -> None:
    settings, database, repository = _components(data_dir)
    try:
        target = output or settings.data_dir / "exports" / f"{run_id}.evidrun.zip"
        EvidenceBundleService(repository).export_run_v3(run_id, target)
        console.print(str(target))
    finally:
        database.dispose()


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


def _authority_service(
    database: Database,
    settings: Settings,
) -> tuple[HumanAuthorityService, AuthorityRepository]:
    authority_repository = AuthorityRepository(database)
    artifacts = ArtifactStore(settings.artifacts_dir)
    service = HumanAuthorityService(
        repository=authority_repository,
        authenticator=KeyringAuthenticator(),
        artifacts=artifacts,
    )
    return service, authority_repository


@authority_app.command("enroll")
def authority_enroll(
    principal_id: Annotated[str, typer.Option("--principal-id")],
    display_name: Annotated[str, typer.Option("--display-name")],
    relying_party_id: Annotated[str, typer.Option("--relying-party-id")] = "evidrun.local",
    origin: Annotated[str, typer.Option("--origin")] = "https://evidrun.local",
    data_dir: Annotated[Path | None, typer.Option("--data-dir")] = None,
) -> None:
    settings, database, _ = _components(data_dir)
    try:
        service, _ = _authority_service(database, settings)
        credential = service.enroll(
            principal_id=principal_id,
            display_name=display_name,
            relying_party_id=relying_party_id,
            origin=origin,
        )
        console.print_json(
            data={
                "credential_id": credential.credential_id,
                "principal_id": credential.principal_id,
                "status": credential.status,
            }
        )
    finally:
        database.dispose()


@authority_app.command("credentials")
def authority_credentials(
    data_dir: Annotated[Path | None, typer.Option("--data-dir")] = None,
) -> None:
    settings, database, _ = _components(data_dir)
    try:
        _, authority_repository = _authority_service(database, settings)
        console.print_json(
            data=[
                {
                    "credential_id": item.credential_id,
                    "principal_id": item.principal_id,
                    "display_name": item.display_name,
                    "status": item.status,
                }
                for item in authority_repository.list_credentials()
            ]
        )
    finally:
        database.dispose()


@authority_app.command("revoke")
def authority_revoke(
    credential_id: str,
    data_dir: Annotated[Path | None, typer.Option("--data-dir")] = None,
) -> None:
    settings, database, _ = _components(data_dir)
    try:
        _, authority_repository = _authority_service(database, settings)
        credential = authority_repository.revoke_credential(credential_id)
        console.print_json(
            data={"credential_id": credential.credential_id, "status": credential.status}
        )
    finally:
        database.dispose()


@authority_app.command("accept")
def authority_accept(
    revision_id: str,
    credential_id: Annotated[str, typer.Option("--credential-id")],
    reason: Annotated[str, typer.Option("--reason")],
    data_dir: Annotated[Path | None, typer.Option("--data-dir")] = None,
) -> None:
    """Confirm a verified-human acceptance of a contract revision (offline authenticator)."""
    settings, database, repository = _components(data_dir)
    try:
        service, authority_repository = _authority_service(database, settings)
        repository.human_attestation_verifier = LocalWebAuthnVerifier(
            authority_repository, ArtifactStore(settings.artifacts_dir)
        )
        revision = repository.get_contract_revision(revision_id)
        subject = RevisionDecisionSubject(
            revision_ref=revision.ref,
            decision="accepted",
            rationale=reason,
        )
        attestation = service.confirm_with_local_authenticator(
            mode=AuthorityMode.PRIVILEGED,
            subject=subject,
            credential_id=credential_id,
            project_id=revision.project_id,
        )
        row = repository.decide_contract_revision(subject.build_decision(attestation))
        console.print_json(
            data={
                "id": row.id,
                "decision": row.decision,
                "attestation_id": attestation.attestation_id,
            }
        )
    except (ValueError, PermissionError, KeyError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    finally:
        database.dispose()


def main() -> None:
    app()


if __name__ == "__main__":
    main()
