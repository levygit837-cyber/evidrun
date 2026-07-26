from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from evidrun.contracts import ArtifactManifest, EvaluationRecord, GoalRevision, GoalSpec
from evidrun.contracts.authoring.goal import GoalOutcome
from evidrun.entrypoints.api.app import create_app
from evidrun.evidence.bundle import EvidenceBundleService
from evidrun.shared.types import canonical_json, sha256_json

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
        with zipfile.ZipFile(source_bundle) as archive:
            bundle_profile = json.loads(archive.read("bundle.json"))
            artifact_manifest = json.loads(archive.read("artifact-manifest.json"))
            member_names = set(archive.namelist())
        assert bundle_profile["profile"] == "audit"
        assert bundle_profile["artifact_content"] == "references_only"
        assert bundle_profile["portable"] is False
        assert bundle_profile["replayable"] is False
        assert artifact_manifest["entries"]
        assert {item["role"] for item in artifact_manifest["entries"]} == {
            "scenario_input"
        }
        assert all(item["content_included"] is False for item in artifact_manifest["entries"])
        assert all("omission_reason" in item for item in artifact_manifest["entries"])
        assert all(
            "locator" not in item["artifact_ref"]
            for item in artifact_manifest["entries"]
        )
        assert not any(name.startswith("artifact-content/") for name in member_names)

        with zipfile.ZipFile(source_bundle) as archive:
            unanchored_files = {name: archive.read(name) for name in archive.namelist()}
        unanchored_manifest = json.loads(unanchored_files["artifact-manifest.json"])
        extra_entry = dict(unanchored_manifest["entries"][0])
        extra_entry["role"] = "report_attachment"
        extra_entry["source_label"] = "unanchored-file-access-telemetry"
        extra_entry["artifact_ref"] = {
            **extra_entry["artifact_ref"],
            "artifact_id": "unanchored-file",
            "digest": "f" * 64,
        }
        unanchored_manifest["entries"].append(extra_entry)
        manifest_document = {
            key: value for key, value in unanchored_manifest.items() if key != "digest"
        }
        unanchored_manifest["digest"] = ArtifactManifest.model_validate(
            manifest_document
        ).digest
        unanchored_files["artifact-manifest.json"] = (
            json.dumps(
                unanchored_manifest,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            + "\n"
        ).encode()
        unanchored_checksums = json.loads(unanchored_files["checksums.json"])
        unanchored_checksums["files"]["artifact-manifest.json"] = hashlib.sha256(
            unanchored_files["artifact-manifest.json"]
        ).hexdigest()
        unanchored_files["checksums.json"] = (
            json.dumps(
                unanchored_checksums,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            + "\n"
        ).encode()
        unanchored_bundle = tmp_path / "unanchored-artifact.evidrun.zip"
        with zipfile.ZipFile(
            unanchored_bundle, "w", compression=zipfile.ZIP_DEFLATED
        ) as archive:
            for name, content in unanchored_files.items():
                archive.writestr(name, content)
        unanchored_verification = EvidenceBundleService(app.state.repository).verify(
            unanchored_bundle
        )
        assert unanchored_verification["valid"] is False
        assert unanchored_verification["records"]["artifact-manifest.json"] is False

        with zipfile.ZipFile(source_bundle) as archive:
            comparison_files = {name: archive.read(name) for name in archive.namelist()}
        comparison_document = json.loads(comparison_files["comparison.json"])
        comparison_document["baseline_run_id"] = comparison_document["candidate_run_id"]
        comparison_files["comparison.json"] = (
            json.dumps(
                comparison_document,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            + "\n"
        ).encode()
        comparison_checksums = json.loads(comparison_files["checksums.json"])
        comparison_checksums["files"]["comparison.json"] = hashlib.sha256(
            comparison_files["comparison.json"]
        ).hexdigest()
        comparison_files["checksums.json"] = (
            json.dumps(
                comparison_checksums,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            + "\n"
        ).encode()
        mismatched_comparison_bundle = tmp_path / "mismatched-comparison.evidrun.zip"
        with zipfile.ZipFile(
            mismatched_comparison_bundle, "w", compression=zipfile.ZIP_DEFLATED
        ) as archive:
            for name, content in comparison_files.items():
                archive.writestr(name, content)
        mismatched_comparison = EvidenceBundleService(app.state.repository).verify(
            mismatched_comparison_bundle
        )
        assert mismatched_comparison["valid"] is False
        assert mismatched_comparison["records"]["comparison.json"] is False

        with zipfile.ZipFile(source_bundle) as archive:
            unterminated_files = {name: archive.read(name) for name in archive.namelist()}
        event_file = next(name for name in unterminated_files if name.startswith("events/"))
        event_documents = [
            json.loads(line)
            for line in unterminated_files[event_file].splitlines()
            if line
        ]
        assert event_documents[-1]["type"] == "run.completed"
        event_documents.pop()
        unterminated_files[event_file] = (
            "\n".join(
                json.dumps(
                    event,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                for event in event_documents
            )
            + "\n"
        ).encode()
        unterminated_checksums = json.loads(unterminated_files["checksums.json"])
        unterminated_checksums["files"][event_file] = hashlib.sha256(
            unterminated_files[event_file]
        ).hexdigest()
        unterminated_files["checksums.json"] = (
            json.dumps(
                unterminated_checksums,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            + "\n"
        ).encode()
        unterminated_bundle = tmp_path / "unterminated-run.evidrun.zip"
        with zipfile.ZipFile(
            unterminated_bundle, "w", compression=zipfile.ZIP_DEFLATED
        ) as archive:
            for name, content in unterminated_files.items():
                archive.writestr(name, content)
        unterminated = EvidenceBundleService(app.state.repository).verify(
            unterminated_bundle
        )
        assert unterminated["valid"] is False
        run_id = Path(event_file).stem
        assert unterminated["records"][f"__terminal_event__:{run_id}"] is False

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

        with zipfile.ZipFile(source_bundle) as archive:
            plan_files = {name: archive.read(name) for name in archive.namelist()}
        plan_evaluations = json.loads(plan_files[evaluation_name])
        plan_evaluations[0]["plan_ref"]["logical_id"] = "substituted-plan"
        plan_document = {
            key: value
            for key, value in plan_evaluations[0].items()
            if key != "digest"
        }
        plan_evaluations[0]["digest"] = EvaluationRecord.model_validate(
            plan_document
        ).digest
        plan_files[evaluation_name] = (
            json.dumps(plan_evaluations, ensure_ascii=False, sort_keys=True, indent=2)
            + "\n"
        ).encode()
        plan_checksums = json.loads(plan_files["checksums.json"])
        plan_checksums["files"][evaluation_name] = hashlib.sha256(
            plan_files[evaluation_name]
        ).hexdigest()
        plan_files["checksums.json"] = (
            json.dumps(plan_checksums, ensure_ascii=False, sort_keys=True, indent=2)
            + "\n"
        ).encode()
        substituted_plan_bundle = tmp_path / "substituted-plan.evidrun.zip"
        with zipfile.ZipFile(
            substituted_plan_bundle, "w", compression=zipfile.ZIP_DEFLATED
        ) as archive:
            for name, content in plan_files.items():
                archive.writestr(name, content)
        plan_verification = EvidenceBundleService(app.state.repository).verify(
            substituted_plan_bundle
        )
        assert plan_verification["valid"] is False
        assert plan_verification["records"][evaluation_name] is False

        injected_bundle = tmp_path / "injected-extra-file.evidrun.zip"
        with zipfile.ZipFile(source_bundle) as source, zipfile.ZipFile(
            injected_bundle, "w", compression=zipfile.ZIP_DEFLATED
        ) as target:
            for name in source.namelist():
                target.writestr(name, source.read(name))
            target.writestr("unverified.txt", b"not covered by checksums")
        injected_verification = EvidenceBundleService(app.state.repository).verify(
            injected_bundle
        )
        assert injected_verification["valid"] is False
        assert (
            injected_verification["checksums"]["__complete_file_list__"] is False
        )

        duplicate_bundle = tmp_path / "duplicate-member.evidrun.zip"
        with zipfile.ZipFile(source_bundle) as source, zipfile.ZipFile(
            duplicate_bundle, "w", compression=zipfile.ZIP_DEFLATED
        ) as target:
            for name in source.namelist():
                target.writestr(name, source.read(name))
            with pytest.warns(UserWarning, match="Duplicate name"):
                target.writestr("report.md", source.read("report.md"))
        duplicate_verification = EvidenceBundleService(app.state.repository).verify(
            duplicate_bundle
        )
        assert duplicate_verification["valid"] is False
        assert duplicate_verification["checksums"]["__unique_file_names__"] is False

        with zipfile.ZipFile(source_bundle) as archive:
            evidence_files = {name: archive.read(name) for name in archive.namelist()}
        evidence_evaluations = json.loads(evidence_files[evaluation_name])
        evidence_evaluations[0]["dimension_values"][0]["evidence_refs"][0][
            "ref"
        ] = "event:fake"
        evidence_document = {
            key: value
            for key, value in evidence_evaluations[0].items()
            if key != "digest"
        }
        evidence_evaluations[0]["digest"] = EvaluationRecord.model_validate(
            evidence_document
        ).digest
        evidence_files[evaluation_name] = (
            json.dumps(evidence_evaluations, ensure_ascii=False, sort_keys=True, indent=2)
            + "\n"
        ).encode()
        evidence_checksums = json.loads(evidence_files["checksums.json"])
        evidence_checksums["files"][evaluation_name] = hashlib.sha256(
            evidence_files[evaluation_name]
        ).hexdigest()
        evidence_files["checksums.json"] = (
            json.dumps(evidence_checksums, ensure_ascii=False, sort_keys=True, indent=2)
            + "\n"
        ).encode()
        forged_evidence_bundle = tmp_path / "forged-evidence-ref.evidrun.zip"
        with zipfile.ZipFile(
            forged_evidence_bundle, "w", compression=zipfile.ZIP_DEFLATED
        ) as archive:
            for name, content in evidence_files.items():
                archive.writestr(name, content)
        evidence_verification = EvidenceBundleService(app.state.repository).verify(
            forged_evidence_bundle
        )
        assert evidence_verification["valid"] is False
        assert evidence_verification["records"][evaluation_name] is False

        with zipfile.ZipFile(source_bundle) as archive:
            duplicate_evaluation_files = {
                name: archive.read(name) for name in archive.namelist()
            }
        duplicate_event_name = next(
            name for name in duplicate_evaluation_files if name.startswith("events/")
        )
        duplicate_events = [
            json.loads(line)
            for line in duplicate_evaluation_files[duplicate_event_name].splitlines()
            if line
        ]
        evaluation_index = next(
            index
            for index, event in enumerate(duplicate_events)
            if event["type"] == "evaluation.completed"
        )
        forged_completion = {
            **duplicate_events[evaluation_index],
            "event_id": "evt_duplicate_evaluation_completion",
        }
        duplicate_events.insert(evaluation_index + 1, forged_completion)
        previous_hash: str | None = None
        for sequence, event in enumerate(duplicate_events, start=1):
            event["sequence"] = sequence
            event["prev_event_hash"] = previous_hash
            event.pop("event_hash", None)
            event["event_hash"] = sha256_json(event)
            previous_hash = event["event_hash"]
        duplicate_evaluation_files[duplicate_event_name] = (
            "\n".join(canonical_json(event) for event in duplicate_events) + "\n"
        ).encode()
        duplicate_evaluation_checksums = json.loads(
            duplicate_evaluation_files["checksums.json"]
        )
        duplicate_evaluation_checksums["files"][duplicate_event_name] = (
            hashlib.sha256(
                duplicate_evaluation_files[duplicate_event_name]
            ).hexdigest()
        )
        duplicate_evaluation_files["checksums.json"] = (
            json.dumps(
                duplicate_evaluation_checksums,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            + "\n"
        ).encode()
        duplicate_evaluation_bundle = tmp_path / "duplicate-evaluation-event.evidrun.zip"
        with zipfile.ZipFile(
            duplicate_evaluation_bundle, "w", compression=zipfile.ZIP_DEFLATED
        ) as archive:
            for name, content in duplicate_evaluation_files.items():
                archive.writestr(name, content)
        duplicate_evaluation_verification = EvidenceBundleService(
            app.state.repository
        ).verify(duplicate_evaluation_bundle)
        assert duplicate_evaluation_verification["valid"] is False
        run_evaluation_name = f"evaluations/{Path(duplicate_event_name).stem}.json"
        assert (
            duplicate_evaluation_verification["records"][run_evaluation_name]
            is False
        )


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
                "rationale": "Explicitly accepted during the integration test.",
            },
        )
        assert decision.status_code == 503
        assert "verified human authority is unavailable" in decision.json()["detail"]
        listed = client.get("/api/v1/contracts/revisions").json()
        stored = next(item for item in listed if item["id"] == revision_id)
        assert stored["status"] == "draft"

        changed = goal.model_copy(update={"title": "Mutated content"})
        conflict = client.post(
            "/api/v1/contracts/revisions",
            json={"document": changed.semantic_document()},
        )
        assert conflict.status_code == 409
        assert conflict.json()["detail"]["code"] == "register.immutability_conflict"
