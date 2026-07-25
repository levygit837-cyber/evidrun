from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from evidrun.entrypoints.api.app import create_app
from evidrun.entrypoints.cli.app import app as cli_app
from evidrun.runs import build_runtime_kernel
from tests.integration.test_runtime_queue import _runtime_fixture


def test_run_api_enqueues_idempotently_and_exposes_execution_state(
    tmp_path: Path,
) -> None:
    fixture = _runtime_fixture(tmp_path)
    kernel = build_runtime_kernel(fixture.repository, fixture.settings.artifacts_dir)
    second_admission = kernel.coordinator.admission_service.admit(
        fixture.repository.read_model.get_run_spec(fixture.spec_id)
    )
    second_admission_row = fixture.repository.catalog.save_admission_record(
        fixture.spec_id, second_admission
    )
    fixture.database.dispose()

    app = create_app(data_dir=tmp_path)
    with TestClient(app) as client:
        missing_key = client.post(
            f"/api/v1/run-specs/{fixture.spec_id}/runs",
            json={"admission_id": fixture.admission_id},
        )
        assert missing_key.status_code == 422
        first = client.post(
            f"/api/v1/run-specs/{fixture.spec_id}/runs",
            headers={"Idempotency-Key": "api-enqueue"},
            json={"admission_id": fixture.admission_id},
        )
        assert first.status_code == 202
        assert first.json()["status"] == "queued"
        repeated = client.post(
            f"/api/v1/run-specs/{fixture.spec_id}/runs",
            headers={"Idempotency-Key": "api-enqueue"},
            json={"admission_id": fixture.admission_id},
        )
        assert repeated.status_code == 202
        assert repeated.json() == first.json()
        conflict = client.post(
            f"/api/v1/run-specs/{fixture.spec_id}/runs",
            headers={"Idempotency-Key": "api-enqueue"},
            json={"admission_id": second_admission_row.id},
        )
        assert conflict.status_code == 409

        detail = client.get(f"/api/v1/runs/{first.json()['run_id']}")
        assert detail.status_code == 200
        assert detail.json()["execution"]["job"]["job_id"] == first.json()["job_id"]
        assert detail.json()["execution"]["attempts"] == []
        assert detail.json()["subject_envelope_digest"] is None
        premature_bundle = client.post(
            f"/api/v1/runs/{first.json()['run_id']}/evidence-bundles"
        )
        assert premature_bundle.status_code == 422


def test_run_cli_enqueue_inspect_export_and_verify(tmp_path: Path) -> None:
    fixture = _runtime_fixture(tmp_path)
    fixture.database.dispose()
    runner = CliRunner()
    enqueued = runner.invoke(
        cli_app,
        [
            "run",
            "enqueue",
            fixture.spec_id,
            "--admission-id",
            fixture.admission_id,
            "--idempotency-key",
            "cli-enqueue",
            "--data-dir",
            str(tmp_path),
        ],
    )
    assert enqueued.exit_code == 0, enqueued.output
    response = json.loads(enqueued.stdout)
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "evidrun.entrypoints.worker.app",
            "--data-dir",
            str(tmp_path),
            "--once",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert completed.returncode == 0, completed.stderr
    inspected = runner.invoke(
        cli_app,
        ["run", "inspect", response["run_id"], "--data-dir", str(tmp_path)],
    )
    assert inspected.exit_code == 0, inspected.output
    inspection = json.loads(inspected.stdout)
    assert inspection["status"] == "completed"
    assert inspection["execution"]["attempts"]
    assert inspection["subject_envelope_digest"]

    target = tmp_path / "cli-run.evidrun.zip"
    exported = runner.invoke(
        cli_app,
        [
            "bundle",
            "export-run",
            response["run_id"],
            "--output",
            str(target),
            "--data-dir",
            str(tmp_path),
        ],
    )
    assert exported.exit_code == 0, exported.output
    verified = runner.invoke(cli_app, ["bundle", "verify", str(target)])
    assert verified.exit_code == 0, verified.output
    assert json.loads(verified.stdout)["valid"] is True
