"""Admission rejection causes stay identical at every operator-facing surface."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from evidrun.contracts.admission import admission_rejection_error
from evidrun.entrypoints.api.app import create_app
from evidrun.entrypoints.cli.app import app as cli_app
from evidrun.infrastructure.artifacts.store import ArtifactStore, MemoryKeyProvider
from evidrun.infrastructure.database import Database, Repository
from tests.integration.test_runtime_queue import _runtime_fixture
from tests.support.admission_cases import build_admission_cases, build_catalogs
from tests.support.admission_specs import oracle_profile


def test_api_and_cli_require_system_derived_execution_trust(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data"
    database = Database(data_dir / "evidrun.db")
    database.create_all()
    repository = Repository(database)
    store = ArtifactStore(data_dir / "artifacts", MemoryKeyProvider())
    cases = {case.name: case for case in build_admission_cases(store)}
    catalogs = build_catalogs(store, profile=oracle_profile())
    case = cases["subject_input_media_type_json"]
    expected_record = catalogs[case.catalog].admission_service().admit(case.spec)
    assert admission_rejection_error(expected_record).code
    spec_row = repository.catalog.save_run_spec(case.spec)
    database.dispose()

    app = create_app(data_dir=data_dir)
    with TestClient(app) as client:
        api_response = client.post(f"/api/v1/run-specs/{spec_row.id}/admit")
        assert api_response.status_code == 422
        unknown = client.post(
            f"/api/v1/run-specs/{spec_row.id}/admit",
            json={"execution_trust_id": "trust_unknown"},
        )
        assert unknown.status_code == 404

    cli_response = CliRunner().invoke(
        cli_app,
        ["run", "admit", spec_row.id, "--data-dir", str(data_dir)],
    )
    assert cli_response.exit_code == 2, cli_response.output


def test_missing_provider_profile_cannot_bypass_execution_trust(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    app = create_app(data_dir=data_dir)
    store = app.state.runtime_kernel.artifact_store
    cases = {case.name: case for case in build_admission_cases(store)}
    case = cases["provider_profile_unavailable"]
    spec_row = app.state.repository.catalog.save_run_spec(case.spec)

    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/run-specs/{spec_row.id}/admit",
            json={"execution_trust_id": "trust_missing-provider-bypass"},
        )
        assert response.status_code == 404


def test_admitted_api_and_cli_responses_keep_their_success_contract(tmp_path: Path) -> None:
    fixture = _runtime_fixture(tmp_path)
    fixture.database.dispose()
    app = create_app(data_dir=tmp_path)

    with TestClient(app) as client:
        api_response = client.post(
            f"/api/v1/run-specs/{fixture.spec_id}/admit",
            json={"execution_trust_id": fixture.execution_trust_id},
        )
        assert api_response.status_code == 200
        assert api_response.json()["decision"] == "admitted"
        assert "error" not in api_response.json()

    cli_response = CliRunner().invoke(
        cli_app,
        [
            "run",
            "admit",
            fixture.spec_id,
            "--execution-trust-id",
            fixture.execution_trust_id,
            "--data-dir",
            str(tmp_path),
        ],
    )
    assert cli_response.exit_code == 0, cli_response.output
    assert json.loads(cli_response.stdout)["decision"] == "admitted"
    assert "error" not in json.loads(cli_response.stdout)
