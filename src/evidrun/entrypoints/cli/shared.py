"""What every command family needs: one console and one way to open the runtime.

`components()` is the CLI's composition root. It resolves settings, opens the
database, and wires the human-attestation verifier only when authority is
enabled, so a command never reconstructs a `Repository` without its verifier.
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

from evidrun.authority.authenticator import KeyringAuthenticator
from evidrun.authority.repository import AuthorityRepository
from evidrun.authority.service import HumanAuthorityService
from evidrun.authority.verifier import LocalWebAuthnVerifier
from evidrun.infrastructure.artifacts.store import ArtifactStore
from evidrun.infrastructure.database import Database, Repository
from evidrun.settings import Settings

console = Console()


def components(data_dir: Path | None = None) -> tuple[Settings, Database, Repository]:
    """Open the managed runtime, keeping the verifier attached to the Repository."""

    settings = Settings.load(data_dir)
    settings.ensure_directories()
    database = Database(settings.database_path)
    database.create_all()
    verifier: LocalWebAuthnVerifier | None = None
    if settings.authority_enabled:
        verifier = LocalWebAuthnVerifier(
            AuthorityRepository(database), ArtifactStore(settings.artifacts_dir)
        )
    return settings, database, Repository(database, human_attestation_verifier=verifier)


def authority_service(
    database: Database, settings: Settings
) -> tuple[HumanAuthorityService, AuthorityRepository]:
    authority_repository = AuthorityRepository(database)
    artifacts = ArtifactStore(settings.artifacts_dir)
    service = HumanAuthorityService(
        repository=authority_repository,
        authenticator=KeyringAuthenticator(),
        artifacts=artifacts,
    )
    return service, authority_repository
