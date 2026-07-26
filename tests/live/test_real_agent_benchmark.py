from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
import zipfile
from pathlib import Path

import pytest

from evidrun.contracts import ArtifactRef
from evidrun.contracts.compiler import StudyCompiler
from evidrun.evidence.bundle import EvidenceBundleService
from evidrun.infrastructure.artifacts.store import ArtifactStore
from evidrun.infrastructure.database import Database, Repository
from evidrun.providers import ProviderProfile
from evidrun.runs import build_runtime_kernel
from evidrun.settings import Settings
from evidrun.shared.types import Classification
from tests.support.human_attestation import (
    TestHumanAttestationVerifier,
    accepted_decision,
)
from tests.support.live_read_study import (
    build_live_read_study,
    fresh_incident_memo,
)

pytestmark = pytest.mark.skipif(
    os.environ.get("EVIDRUN_RUN_LIVE_AGENT") != "1",
    reason="real-provider benchmark is opt-in",
)


def test_real_model_completes_fresh_tool_grounded_study(tmp_path: Path) -> None:
    configured_dir = os.environ.get("EVIDRUN_LIVE_DATA_DIR")
    data_dir = Path(configured_dir) if configured_dir else tmp_path / "live-data"
    settings = Settings.load(data_dir)
    settings.ensure_directories()
    profile = ProviderProfile.load_default()
    nonce = uuid.uuid4().hex[:12].upper()
    expected = f"THERMAL_RELAY_LIVE_{nonce}"

    database = Database(settings.database_path)
    database.create_all()
    repository = Repository(database, TestHumanAttestationVerifier())
    workspace = repository.catalog.create_workspace(f"Live benchmark {nonce}")
    project = repository.catalog.create_project(workspace.id, f"Fresh retrieval {nonce}")
    artifact_store = ArtifactStore(settings.artifacts_dir)
    source = artifact_store.put_ref(
        fresh_incident_memo(expected).encode("utf-8"),
        project_id=project.id,
        media_type="text/plain",
        classification=Classification.INTERNAL,
    )
    revisions, study = build_live_read_study(
        project_id=project.id,
        source=source,
        expected=expected,
        profile=profile,
    )
    for revision in revisions:
        repository.registry.save_contract_revision(revision, status="proposed")
        repository.registry.decide_contract_revision(accepted_decision(revision))
    spec = StudyCompiler(repository.registry.contract_registry(project.id)).compile(study)[0]
    spec_row = repository.catalog.save_run_spec(spec)
    kernel = build_runtime_kernel(repository, settings.artifacts_dir)
    admission = kernel.coordinator.admission_service.admit(spec)
    assert admission.decision == "admitted", admission.model_dump(mode="json")
    admission_row = repository.catalog.save_admission_record(spec_row.id, admission)
    run_id, job = kernel.coordinator.enqueue(
        run_spec_id=spec_row.id,
        admission_id=admission_row.id,
        idempotency_key=f"live-agent-{nonce}",
    )
    database.dispose()

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "evidrun.entrypoints.worker.app",
            "--data-dir",
            str(data_dir),
            "--worker-id",
            f"live-subprocess-{nonce}",
            "--once",
            "--lease-seconds",
            "60",
            "--heartbeat-seconds",
            "10",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert completed.returncode == 0, {
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }

    reopened_database = Database(settings.database_path)
    reopened_database.create_all()
    reopened = Repository(reopened_database)
    run = reopened.read_model.get_run(run_id)
    events = reopened.read_model.get_run_events(run_id)
    assert run.status == "completed", events
    event_types = [event["type"] for event in events]
    assert event_types[:6] == [
        "run.queued",
        "run.preparing",
        "context.composed",
        "capability.offered",
        "run.running",
        "subject.invoked",
    ]
    assert event_types[-4:] == [
        "subject.responded",
        "run.evaluating",
        "evaluation.completed",
        "run.completed",
    ]
    tool_event_types = event_types[6:-4]
    assert len(tool_event_types) in {2, 4}
    assert tool_event_types == ["tool.called", "tool.completed"] * (
        len(tool_event_types) // 2
    )
    assert reopened.read_model.get_evaluation_records(run_id)[0].gate_status == "passed"
    execution = reopened.lease.get_run_execution(run_id)
    assert execution is not None
    assert execution[0].job_id == job.job_id
    assert execution[0].status == "completed"
    assert execution[1][0].worker_id == f"live-subprocess-{nonce}"

    response = next(event for event in events if event["type"] == "subject.responded")
    output_ref = ArtifactRef.model_validate(response["payload"]["output_ref"])
    result_document = json.loads(
        ArtifactStore(settings.artifacts_dir).get_verified(
            output_ref,
            project_id=project.id,
        )
    )
    output_document = json.loads(result_document["output"])
    assert output_document["answer"] == expected
    assert {"input_id": "incident-memo", "line": 36} in output_document["evidence"]

    bundle_path = data_dir / f"{run_id}.evidence-v3.zip"
    service = EvidenceBundleService(reopened)
    service.export_run_v3(run_id, bundle_path)
    verification = service.verify(bundle_path)
    assert verification["valid"] is True, verification
    with zipfile.ZipFile(bundle_path) as archive:
        envelope = json.loads(archive.read(f"subject-envelopes/{run_id}.json"))
        bundle = json.loads(archive.read("bundle.json"))
    assert bundle["schema_version"] == "3"
    invocation = next(event for event in events if event["type"] == "subject.invoked")
    assert envelope["digest"] == invocation["payload"]["subject_envelope_digest"]
    assert expected not in json.dumps(envelope, sort_keys=True)

    result_path = data_dir / "live-result.json"
    result_path.write_text(
        json.dumps(
            {
                "data_dir": str(data_dir),
                "run_id": run_id,
                "job_id": job.job_id,
                "run_spec_id": spec_row.id,
                "admission_id": admission_row.id,
                "expected": expected,
                "model": profile.model,
                "reasoning_effort": profile.reasoning_effort,
                "event_types": event_types,
                "evaluation_gate": "passed",
                "bundle_path": str(bundle_path),
                "bundle_valid": True,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    reopened_database.dispose()
