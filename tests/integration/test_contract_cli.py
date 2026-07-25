from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from evidrun.authority.verifier import LocalWebAuthnVerifier
from evidrun.contracts import GoalRevision, GoalSpec
from evidrun.contracts.authoring import GoalOutcome
from evidrun.contracts.authority import UnavailableHumanAttestationVerifier
from evidrun.entrypoints.cli.app import _components, app
from evidrun.infrastructure.database import Database, Repository


def test_contract_cli_validates_registers_and_fails_closed_without_human_verifier(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("EVIDRUN_AUTHORITY", raising=False)
    data_dir = tmp_path / "data"
    database = Database(data_dir / "evidrun.db")
    database.create_all()
    repository = Repository(database)
    workspace = repository.create_workspace("CLI workspace")
    project = repository.create_project(workspace.id, "CLI project")
    database.dispose()

    goal = GoalRevision(
        logical_id="cli-goal",
        revision=1,
        project_id=project.id,
        title="CLI Goal",
        payload=GoalSpec(
            mode="goal_state",
            instruction="Produce one auditable response.",
            outcomes=(
                GoalOutcome(id="response", description="An auditable response exists."),
            ),
        ),
    )
    document_path = tmp_path / "goal.yaml"
    document_path.write_text(
        yaml.safe_dump(goal.semantic_document(), sort_keys=False), encoding="utf-8"
    )
    runner = CliRunner()

    validation = runner.invoke(app, ["contract", "validate", str(document_path)])
    assert validation.exit_code == 0, validation.output
    assert json.loads(validation.stdout)["digest"] == goal.digest

    registration = runner.invoke(
        app,
        [
            "contract",
            "register",
            str(document_path),
            "--status",
            "proposed",
            "--data-dir",
            str(data_dir),
        ],
    )
    assert registration.exit_code == 0, registration.output
    registered = json.loads(registration.stdout)
    assert registered["digest"] == goal.digest
    assert registered["status"] == "proposed"

    # Acceptance requires verified human authority. Without EVIDRUN_AUTHORITY the CLI
    # installs no trusted verifier, so the ceremony must fail closed and persist nothing.
    settings, cli_database, cli_repository = _components(data_dir)
    try:
        assert settings.authority_enabled is False
        assert isinstance(
            cli_repository.human_attestation_verifier, UnavailableHumanAttestationVerifier
        )
    finally:
        cli_database.dispose()

    acceptance = runner.invoke(
        app,
        [
            "authority",
            "accept",
            registered["id"],
            "--credential-id",
            "hcred-absent",
            "--reason",
            "Explicitly accepted by the CLI integration test.",
            "--data-dir",
            str(data_dir),
        ],
    )
    assert acceptance.exit_code == 1

    verify_database = Database(data_dir / "evidrun.db")
    verify_database.create_all()
    revisions = Repository(verify_database).list_contract_revisions()
    verify_database.dispose()
    stored = next(item for item in revisions if item["logical_id"] == goal.logical_id)
    assert stored["status"] == "proposed"


def test_authority_enabled_cli_installs_a_trusted_verifier(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With authority enabled every CLI command must read decisions through a real verifier.

    A CLI that persists a verified-human acceptance but rebuilds its Repository without a
    verifier writes evidence it can never resolve again: `study compile` would fail closed
    on data the same CLI just accepted.
    """

    monkeypatch.setenv("EVIDRUN_AUTHORITY", "1")
    data_dir = tmp_path / "data"
    settings, database, repository = _components(data_dir)
    try:
        assert settings.authority_enabled is True
        assert isinstance(repository.human_attestation_verifier, LocalWebAuthnVerifier)
    finally:
        database.dispose()
