from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from evidrun.entrypoints.api.app import create_app
from evidrun.entrypoints.cli.app import app as cli_app
from evidrun.infrastructure.artifacts.store import ArtifactStore
from evidrun.infrastructure.database import Database, Repository
from evidrun.settings import Settings
from evidrun.shared.types import Classification
from tests.support.runtime_study import build_runtime_study


def test_api_and_cli_share_one_draft_execution_preparation(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    settings = Settings.load(data_dir)
    settings.ensure_directories()
    database = Database(settings.database_path)
    database.create_all()
    repository = Repository(database)
    workspace = repository.catalog.create_workspace("Preparation surface workspace")
    project = repository.catalog.create_project(workspace.id, "Preparation surface project")
    source = ArtifactStore(settings.artifacts_dir).put_ref(
        b"ROOT_CAUSE=SEARCH_INDEX_LAG\n",
        project_id=project.id,
        media_type="text/plain",
        classification=Classification.INTERNAL,
    )
    revisions, study = build_runtime_study(project_id=project.id, source=source)
    study_id = ""
    for revision in revisions:
        row = repository.registry.save_contract_revision(revision, status="draft")
        if revision == study:
            study_id = row.id
    database.dispose()

    app = create_app(data_dir=data_dir)
    with TestClient(app) as client:
        api_prepared = client.post(f"/api/v1/studies/{study_id}/compile")
        assert api_prepared.status_code == 200
        api_document = api_prepared.json()
        prepared = api_document["run_specs"][0]
        trust_id = prepared["execution_trust"]["trust_id"]
        caller_claim = client.post(
            f"/api/v1/run-specs/{prepared['id']}/admit",
            json={
                "execution_trust_id": trust_id,
                "kind": "verified_revision_set",
            },
        )
        assert caller_claim.status_code == 422
        api_admission = client.post(
            f"/api/v1/run-specs/{prepared['id']}/admit",
            json={"execution_trust_id": trust_id},
        )
        assert api_admission.status_code == 200, api_admission.text
        assert api_admission.json()["execution_trust"] == {
            "trust_id": trust_id,
            "digest": prepared["execution_trust"]["digest"],
        }

    runner = CliRunner()
    cli_prepared = runner.invoke(
        cli_app,
        ["study", "compile", study_id, "--data-dir", str(data_dir)],
    )
    assert cli_prepared.exit_code == 0, cli_prepared.output
    assert json.loads(cli_prepared.stdout) == api_document
    cli_admission = runner.invoke(
        cli_app,
        [
            "run",
            "admit",
            prepared["id"],
            "--execution-trust-id",
            trust_id,
            "--data-dir",
            str(data_dir),
        ],
    )
    assert cli_admission.exit_code == 0, cli_admission.output
    cli_document = json.loads(cli_admission.stdout)
    assert cli_document["decision"] == api_admission.json()["decision"]
    assert cli_document["execution_trust"] == api_admission.json()["execution_trust"]
    app.state.repository.database.dispose()
