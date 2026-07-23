from __future__ import annotations

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from evidrun.contracts import GoalRevision, GoalSpec
from evidrun.contracts.authoring import GoalOutcome
from evidrun.entrypoints.cli.app import app
from evidrun.infrastructure.database import Database, Repository


def test_contract_cli_validates_registers_and_accepts_the_same_normalized_model(
    tmp_path: Path,
) -> None:
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

    acceptance = runner.invoke(
        app,
        [
            "contract",
            "accept",
            registered["id"],
            "--reason",
            "Explicitly accepted by the CLI integration test.",
            "--actor-id",
            "cli-test-human",
            "--data-dir",
            str(data_dir),
        ],
    )
    assert acceptance.exit_code == 0, acceptance.output
    assert json.loads(acceptance.stdout)["decision"] == "accepted"

    verify_database = Database(data_dir / "evidrun.db")
    verify_database.create_all()
    revisions = Repository(verify_database).list_contract_revisions()
    verify_database.dispose()
    stored = next(item for item in revisions if item["logical_id"] == goal.logical_id)
    assert stored["status"] == "accepted"
