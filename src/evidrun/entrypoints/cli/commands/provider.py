"""Provider diagnostics and human-authority commands."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

import typer

from evidrun.authority.policy import AuthorityMode
from evidrun.authority.subject import RevisionDecisionSubject
from evidrun.contracts.triage import CLI_EXIT_BY_CODE, TriageRejected
from evidrun.entrypoints.cli.shared import authority_service, components, console
from evidrun.infrastructure.database.decide_errors import decide_revision_not_found
from evidrun.infrastructure.providers import (
    OpenAIResponsesProvider,
    ProviderCredentialStore,
    ProviderRequestError,
    extract_output_text,
)
from evidrun.settings import Settings

provider_app = typer.Typer(help="Configurar e diagnosticar providers de modelos.")
authority_app = typer.Typer(help="Enrollar credenciais e confirmar autoridade humana.")


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


@authority_app.command("enroll")
def authority_enroll(
    principal_id: Annotated[str, typer.Option("--principal-id")],
    display_name: Annotated[str, typer.Option("--display-name")],
    relying_party_id: Annotated[str, typer.Option("--relying-party-id")] = "evidrun.local",
    origin: Annotated[str, typer.Option("--origin")] = "https://evidrun.local",
    data_dir: Annotated[Path | None, typer.Option("--data-dir")] = None,
) -> None:
    settings, database, _ = components(data_dir)
    try:
        service, _ = authority_service(database, settings)
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
    settings, database, _ = components(data_dir)
    try:
        _, authority_repository = authority_service(database, settings)
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
    settings, database, _ = components(data_dir)
    try:
        _, authority_repository = authority_service(database, settings)
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
    settings, database, repository = components(data_dir)
    try:
        service, _ = authority_service(database, settings)
        try:
            revision = repository.read_model.get_contract_revision(revision_id)
        except KeyError as exc:
            raise decide_revision_not_found() from exc
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
        row = repository.registry.decide_contract_revision(subject.build_decision(attestation))
        console.print_json(
            data={
                "id": row.id,
                "decision": row.decision,
                "attestation_id": attestation.attestation_id,
            }
        )
    except TriageRejected as exc:
        console.print_json(data=exc.error.model_dump(mode="json"))
        raise typer.Exit(CLI_EXIT_BY_CODE[exc.error.code]) from exc
    except (ValueError, PermissionError, KeyError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    finally:
        database.dispose()
