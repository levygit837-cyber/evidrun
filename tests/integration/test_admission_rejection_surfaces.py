"""Admission rejection causes stay identical at every operator-facing surface."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from evidrun.contracts.admission import admission_rejection_error
from evidrun.entrypoints.api.app import create_app
from evidrun.entrypoints.cli.app import app as cli_app
from evidrun.infrastructure.artifacts.store import ArtifactStore, MemoryKeyProvider
from evidrun.infrastructure.database import Database, Repository
from evidrun.runs import EvidrunService
from tests.support.admission_cases import build_admission_cases, build_catalogs
from tests.support.admission_specs import oracle_profile


def test_api_cli_and_service_share_the_persistible_admission_rejection(
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
    expected = admission_rejection_error(expected_record).model_dump(mode="json")
    spec_row = repository.catalog.save_run_spec(case.spec)
    database.dispose()

    app = create_app(data_dir=data_dir)
    with TestClient(app) as client:
        api_response = client.post(f"/api/v1/run-specs/{spec_row.id}/admit")
        assert api_response.status_code == 200
        assert api_response.json()["error"] == expected
        api_admission_id = api_response.json()["id"]
        persisted = client.get(f"/api/v1/admissions/{api_admission_id}")
        assert persisted.status_code == 200
        assert persisted.json()["decision"] == "rejected"

    cli_response = CliRunner().invoke(
        cli_app,
        ["run", "admit", spec_row.id, "--data-dir", str(data_dir)],
    )
    assert cli_response.exit_code == 0, cli_response.output
    assert json.loads(cli_response.stdout)["error"] == expected

    service_database = Database(data_dir / "evidrun.db")
    service_database.create_all()
    service = EvidrunService(Repository(service_database))
    with pytest.raises(ValueError) as rejected:
        asyncio.run(service._execute_spec("oracle-experiment", case.spec, ""))
    assert str(rejected.value) == expected["message"]
    service_database.dispose()


def test_missing_provider_profile_is_persisted_as_a_rejection(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    app = create_app(data_dir=data_dir)
    store = app.state.runtime_kernel.artifact_store
    cases = {case.name: case for case in build_admission_cases(store)}
    case = cases["provider_profile_unavailable"]
    spec_row = app.state.repository.catalog.save_run_spec(case.spec)

    with TestClient(app) as client:
        response = client.post(f"/api/v1/run-specs/{spec_row.id}/admit")
        assert response.status_code == 200
        payload = response.json()
        assert payload["decision"] == "rejected"
        assert "ghost-profile" in payload["error"]["message"]
        persisted = client.get(f"/api/v1/admissions/{payload['id']}")
        assert persisted.status_code == 200
        assert persisted.json()["decision"] == "rejected"
