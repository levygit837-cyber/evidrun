from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from evidrun.contracts.triage import TriageErrorCode, TriageRejected
from evidrun.entrypoints.api.app import create_app
from evidrun.entrypoints.cli.app import app as cli_app
from evidrun.infrastructure.database.models import RunRow
from evidrun.runs import build_runtime_kernel
from evidrun.shared.types import new_id, utc_now
from tests.integration.test_runtime_queue import _runtime_fixture


def test_run_api_enqueues_idempotently_and_exposes_execution_state(
    tmp_path: Path,
) -> None:
    fixture = _runtime_fixture(tmp_path)
    kernel = build_runtime_kernel(fixture.repository, fixture.settings.artifacts_dir)
    second_admission = kernel.coordinator.admission_service.admit(
        fixture.repository.read_model.get_run_spec(fixture.spec_id),
        fixture.repository.execution_trust.get_record(fixture.execution_trust_id),
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

    # A bundle that cannot be verified at all used to reach the generic handler and print
    # "Falha inesperada" with no JSON, so a caller could not classify it. It is an invalid
    # bundle, not a defect: same shape, same exit code, named cause.
    unverifiable = tmp_path / "cli-run-no-checksums.evidrun.zip"
    with zipfile.ZipFile(target) as archive:
        members = {
            name: archive.read(name)
            for name in archive.namelist()
            if name != "checksums.json"
        }
    with zipfile.ZipFile(unverifiable, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in members.items():
            archive.writestr(name, content)
    refused = runner.invoke(cli_app, ["bundle", "verify", str(unverifiable)])
    assert refused.exit_code == 1, refused.output
    assert "Falha inesperada" not in refused.output
    assert "Traceback" not in refused.output
    refusal = json.loads(refused.stdout)
    assert refusal["valid"] is False
    assert [item["code"] for item in refusal["failures"]] == ["bundle.checksums_absent"]
    assert refusal["failures"][0]["category"] == "integrity"


def test_api_and_cli_agree_on_enqueue_refusals_by_stable_code(tmp_path: Path) -> None:
    """Every enqueue refusal names itself; no border classifies by message text."""

    fixture = _runtime_fixture(tmp_path)
    kernel = build_runtime_kernel(fixture.repository, fixture.settings.artifacts_dir)
    second_admission = kernel.coordinator.admission_service.admit(
        fixture.repository.read_model.get_run_spec(fixture.spec_id),
        fixture.repository.execution_trust.get_record(fixture.execution_trust_id),
    )
    second_admission_row = fixture.repository.catalog.save_admission_record(
        fixture.spec_id, second_admission
    )
    fixture.database.dispose()
    runner = CliRunner()

    application = create_app(data_dir=tmp_path)
    with TestClient(application) as client:
        accepted = client.post(
            f"/api/v1/run-specs/{fixture.spec_id}/runs",
            headers={"Idempotency-Key": "parity-enqueue"},
            json={"admission_id": fixture.admission_id},
        )
        assert accepted.status_code == 202

        # A reused key with a different request is a conflict by code, not by phrase.
        conflict = client.post(
            f"/api/v1/run-specs/{fixture.spec_id}/runs",
            headers={"Idempotency-Key": "parity-enqueue"},
            json={"admission_id": second_admission_row.id},
        )
        assert conflict.status_code == 409
        assert conflict.json()["detail"]["code"] == "enqueue.idempotency_conflict"

        missing_spec = client.post(
            "/api/v1/run-specs/run-spec-absent/runs",
            headers={"Idempotency-Key": "parity-missing-spec"},
            json={"admission_id": fixture.admission_id},
        )
        assert missing_spec.status_code == 404
        assert missing_spec.json()["detail"]["code"] == "enqueue.run_spec_not_found"

        missing_admission = client.post(
            f"/api/v1/run-specs/{fixture.spec_id}/runs",
            headers={"Idempotency-Key": "parity-missing-admission"},
            json={"admission_id": "adm-absent"},
        )
        assert missing_admission.status_code == 404
        assert missing_admission.json()["detail"]["code"] == "enqueue.admission_not_found"

        empty_key = client.post(
            f"/api/v1/run-specs/{fixture.spec_id}/runs",
            headers={"Idempotency-Key": "   "},
            json={"admission_id": fixture.admission_id},
        )
        assert empty_key.status_code == 422
        assert empty_key.json()["detail"]["code"] == "enqueue.idempotency_key_empty"

        # The Run above is queued, never terminal, so a retry cannot start from it.
        succeeded = client.post(
            f"/api/v1/runs/{accepted.json()['run_id']}/retries",
            headers={"Idempotency-Key": "parity-retry-queued"},
            json={"admission_id": second_admission_row.id},
        )
        assert succeeded.status_code == 409
        assert succeeded.json()["detail"]["code"] == "enqueue.retry_source_succeeded"

    cli_conflict = runner.invoke(
        cli_app,
        [
            "run",
            "enqueue",
            fixture.spec_id,
            "--admission-id",
            second_admission_row.id,
            "--idempotency-key",
            "parity-enqueue",
            "--data-dir",
            str(tmp_path),
        ],
    )
    assert cli_conflict.exit_code == 5
    assert "Traceback" not in cli_conflict.output
    assert json.loads(cli_conflict.stdout)["code"] == "enqueue.idempotency_conflict"

    cli_missing_spec = runner.invoke(
        cli_app,
        [
            "run",
            "enqueue",
            "run-spec-absent",
            "--admission-id",
            fixture.admission_id,
            "--idempotency-key",
            "parity-cli-missing-spec",
            "--data-dir",
            str(tmp_path),
        ],
    )
    assert cli_missing_spec.exit_code == 4
    assert json.loads(cli_missing_spec.stdout)["code"] == "enqueue.run_spec_not_found"

    cli_empty_key = runner.invoke(
        cli_app,
        [
            "run",
            "enqueue",
            fixture.spec_id,
            "--admission-id",
            fixture.admission_id,
            "--idempotency-key",
            "   ",
            "--data-dir",
            str(tmp_path),
        ],
    )
    assert cli_empty_key.exit_code == 2
    assert json.loads(cli_empty_key.stdout)["code"] == "enqueue.idempotency_key_empty"
    application.state.repository.database.dispose()


def test_api_and_cli_name_the_remaining_retry_refusals(tmp_path: Path) -> None:
    """A legacy Run and a stale retry admission each refuse by their own code."""

    fixture = _runtime_fixture(tmp_path)
    legacy_run_id = new_id("run")
    with fixture.repository.unit_of_work.session() as session:
        session.add(
            RunRow(
                id=legacy_run_id,
                experiment_revision_id=None,
                variant_id="default",
                repetition=1,
                status="failed",
                runner="fixture",
                objective="a Run that predates the Runtime Kernel",
                created_at=utc_now(),
                completed_at=utc_now(),
            )
        )
        session.commit()
    fixture.database.dispose()
    runner = CliRunner()

    application = create_app(data_dir=tmp_path)
    with TestClient(application) as client:
        legacy = client.post(
            f"/api/v1/runs/{legacy_run_id}/retries",
            headers={"Idempotency-Key": "parity-retry-legacy"},
            json={"admission_id": fixture.admission_id},
        )
        assert legacy.status_code == 409
        assert legacy.json()["detail"]["code"] == "enqueue.retry_legacy_run"

    cli_legacy = runner.invoke(
        cli_app,
        [
            "run",
            "retry",
            legacy_run_id,
            "--admission-id",
            fixture.admission_id,
            "--idempotency-key",
            "parity-cli-retry-legacy",
            "--data-dir",
            str(tmp_path),
        ],
    )
    assert cli_legacy.exit_code == 5
    assert "Traceback" not in cli_legacy.output
    assert json.loads(cli_legacy.stdout)["code"] == "enqueue.retry_legacy_run"
    application.state.repository.database.dispose()


def test_a_retry_admission_older_than_the_source_terminal_is_refused(tmp_path: Path) -> None:
    """The admission must be created after the source Run reached its terminal state."""

    fixture = _runtime_fixture(tmp_path)
    kernel = build_runtime_kernel(fixture.repository, fixture.settings.artifacts_dir)
    run_id, job = kernel.coordinator.enqueue(
        run_spec_id=fixture.spec_id,
        admission_id=fixture.admission_id,
        idempotency_key="stale-admission-source",
    )
    stale_admission = kernel.coordinator.admission_service.admit(
        fixture.repository.read_model.get_run_spec(fixture.spec_id),
        fixture.repository.execution_trust.get_record(fixture.execution_trust_id),
    )
    stale_row = fixture.repository.catalog.save_admission_record(
        fixture.spec_id, stale_admission
    )
    # Terminate the source strictly after the admission above, so the only rule the
    # retry can break is admission-not-newer.
    with fixture.repository.unit_of_work.session() as session:
        run = session.get(RunRow, run_id)
        assert run is not None
        run.status = "failed"
        run.completed_at = utc_now() + timedelta(minutes=5)
        session.commit()

    with pytest.raises(TriageRejected) as stale:
        kernel.coordinator.enqueue(
            run_spec_id=fixture.spec_id,
            admission_id=stale_row.id,
            idempotency_key="stale-admission-retry-parity",
            retry_of=run_id,
        )

    assert (
        stale.value.error.code == TriageErrorCode.ENQUEUE_RETRY_ADMISSION_NOT_NEWER
    )
    assert job.status == "queued"
    fixture.database.dispose()
