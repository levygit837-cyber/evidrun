from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from evidrun.contracts import EvaluationRecord, GoalRevision, GoalSpec
from evidrun.contracts.authoring import GoalOutcome
from evidrun.entrypoints.api.app import create_app
from evidrun.evidence.bundle import EvidenceBundleService

ROOT = Path(__file__).resolve().parents[2]


def test_contract_lifecycle_compile_admit_and_bundle_v2(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, benchmark_root=ROOT / "benchmarks")
    with TestClient(app) as client:
        bootstrap = client.post("/api/v1/demo/bootstrap")
        assert bootstrap.status_code == 200

        revisions = client.get("/api/v1/contracts/revisions").json()
        study_row = next(item for item in revisions if item["contract_type"] == "study")
        compiled = client.post(f"/api/v1/studies/{study_row['id']}/compile")
        assert compiled.status_code == 200
        assert len(compiled.json()) == 2

        run_spec_id = compiled.json()[0]["id"]
        admission = client.post(f"/api/v1/run-specs/{run_spec_id}/admit")
        assert admission.status_code == 200
        assert admission.json()["decision"] == "admitted"
        assert client.get(f"/api/v1/run-specs/{run_spec_id}").status_code == 200
        assert client.get(f"/api/v1/admissions/{admission.json()['id']}").status_code == 200

        dashboard = client.get("/api/v1/dashboard").json()
        assert all(run["contract_mode"] == "study_v1" for run in dashboard["runs"])
        run_id = dashboard["runs"][0]["id"]
        run_detail = client.get(f"/api/v1/runs/{run_id}").json()
        assert run_detail["record"]["run_id"] == run_id
        assert run_detail["record"]["run_spec_digest"]
        assert run_detail["record"]["admission_digest"]
        evaluations = client.get(f"/api/v1/runs/{run_id}/evaluations").json()
        assert len(evaluations) == 1
        assert evaluations[0]["boundary"]["event_hash"]
        assert client.get(f"/api/v1/runs/{run_id}/checkpoints").json() == []

        comparison_id = bootstrap.json()["comparison_id"]
        exported = client.post(f"/api/v1/evidence-bundles/{comparison_id}")
        assert exported.status_code == 200
        verification = EvidenceBundleService(app.state.repository).verify(
            Path(exported.json()["path"])
        )
        assert verification["valid"] is True
        assert verification["records"]

        source_bundle = Path(exported.json()["path"])
        tampered_bundle = tmp_path / "tampered-boundary.evidrun.zip"
        with zipfile.ZipFile(source_bundle) as archive:
            files = {name: archive.read(name) for name in archive.namelist()}
        evaluation_name = next(
            name for name in files if name.startswith("evaluations/")
        )
        evaluations = json.loads(files[evaluation_name])
        evaluations[0]["boundary"]["event_hash"] = "0" * 64
        record_document = {
            key: value for key, value in evaluations[0].items() if key != "digest"
        }
        evaluations[0]["digest"] = EvaluationRecord.model_validate(
            record_document
        ).digest
        files[evaluation_name] = (
            json.dumps(evaluations, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        ).encode()
        checksums = json.loads(files["checksums.json"])
        checksums["files"][evaluation_name] = hashlib.sha256(
            files[evaluation_name]
        ).hexdigest()
        files["checksums.json"] = (
            json.dumps(checksums, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        ).encode()
        with zipfile.ZipFile(
            tampered_bundle, "w", compression=zipfile.ZIP_DEFLATED
        ) as archive:
            for name, content in files.items():
                archive.writestr(name, content)
        tampered_verification = EvidenceBundleService(app.state.repository).verify(
            tampered_bundle
        )
        assert tampered_verification["valid"] is False
        assert tampered_verification["records"][evaluation_name] is False


def test_contract_validation_registration_and_human_decision(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, benchmark_root=ROOT / "benchmarks")
    with TestClient(app) as client:
        client.post("/api/v1/demo/bootstrap")
        project_id = client.get("/api/v1/projects").json()[0]["id"]
        goal = GoalRevision(
            logical_id="api-contract-goal",
            revision=1,
            project_id=project_id,
            title="API contract Goal",
            payload=GoalSpec(
                mode="goal_state",
                instruction="Produce an auditable response.",
                outcomes=(
                    GoalOutcome(id="response", description="One response is produced."),
                ),
            ),
        )
        payload = {"document": goal.semantic_document()}
        validation = client.post("/api/v1/contracts/validate", json=payload)
        assert validation.status_code == 200
        assert validation.json()["digest"] == goal.digest

        registration = client.post("/api/v1/contracts/revisions", json=payload)
        assert registration.status_code == 200
        assert registration.json()["status"] == "draft"
        revision_id = registration.json()["id"]
        decision = client.post(
            f"/api/v1/contracts/revisions/{revision_id}/decisions",
            json={
                "decision": "accepted",
                "actor_id": "integration-test-human",
                "rationale": "Explicitly accepted during the integration test.",
            },
        )
        assert decision.status_code == 200
        assert decision.json()["decision"] == "accepted"
        listed = client.get("/api/v1/contracts/revisions").json()
        stored = next(item for item in listed if item["id"] == revision_id)
        assert stored["status"] == "accepted"

        changed = goal.model_copy(update={"title": "Mutated content"})
        conflict = client.post(
            "/api/v1/contracts/revisions",
            json={"document": changed.semantic_document()},
        )
        assert conflict.status_code == 422
