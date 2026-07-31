from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from evidrun.entrypoints.api.app import create_app
from evidrun.entrypoints.cli.app import app as cli_app
from evidrun.entrypoints.cli.app import main as cli_main
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


def test_api_and_cli_share_named_compile_failure_without_traceback(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    application = create_app(data_dir=data_dir)
    missing_id = "contract:missing-study@1"

    with TestClient(application) as client:
        response = client.post(f"/api/v1/studies/{missing_id}/compile")

    assert response.status_code == 404
    api_error = response.json()["detail"]
    assert api_error["code"] == "compile.revision_not_found"

    result = CliRunner().invoke(
        cli_app,
        ["study", "compile", missing_id, "--data-dir", str(data_dir)],
    )

    assert result.exit_code == 4
    assert "Traceback" not in result.output
    assert json.loads(result.stdout) == api_error
    application.state.repository.database.dispose()


@pytest.mark.parametrize(
    ("document", "expected_code"),
    (
        ({"logical_id": "no-type"}, "parse.contract_type_missing"),
        ({"contract_type": "not-a-contract"}, "parse.contract_type_unknown"),
        ({"contract_type": "goal", "unexpected": True}, "parse.field_undeclared"),
    ),
)
def test_api_and_cli_agree_on_every_parse_refusal(
    tmp_path: Path, document: dict[str, object], expected_code: str
) -> None:
    data_dir = tmp_path / "data"
    application = create_app(data_dir=data_dir)
    document_path = tmp_path / "contract.yaml"
    document_path.write_text(yaml.safe_dump(document), encoding="utf-8")

    with TestClient(application) as client:
        response = client.post("/api/v1/contracts/validate", json={"document": document})

    result = CliRunner().invoke(cli_app, ["contract", "validate", str(document_path)])

    assert response.status_code == 422
    assert "Traceback" not in result.output
    assert result.exit_code == 2
    assert json.loads(result.stdout) == response.json()["detail"]
    assert response.json()["detail"]["code"] == expected_code
    application.state.repository.database.dispose()


def test_a_non_object_document_is_refused_by_name_on_the_cli(tmp_path: Path) -> None:
    document_path = tmp_path / "contract.yaml"
    document_path.write_text(yaml.safe_dump([]), encoding="utf-8")

    result = CliRunner().invoke(cli_app, ["contract", "validate", str(document_path)])

    assert result.exit_code == 2
    assert "Traceback" not in result.output
    assert json.loads(result.stdout)["code"] == "parse.document_not_object"


def test_cli_entrypoint_hides_an_unexpected_traceback_unless_requested(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`main` is the seam that owns unexpected failures, so drive it, not the Typer app."""

    def explode(_document: object) -> None:
        raise RuntimeError("unexpected defect")

    monkeypatch.setattr(
        "evidrun.entrypoints.cli.commands.contracts.parse_revision", explode
    )
    document_path = tmp_path / "contract.yaml"
    document_path.write_text("contract_type: goal\n", encoding="utf-8")
    argv = ["evidrun", "contract", "validate", str(document_path)]

    monkeypatch.setattr("sys.argv", argv)
    with pytest.raises(SystemExit) as quiet:
        cli_main()
    assert quiet.value.code == 1

    monkeypatch.setattr("sys.argv", ["evidrun", "--traceback", *argv[1:]])
    with pytest.raises(RuntimeError, match="unexpected defect"):
        cli_main()
