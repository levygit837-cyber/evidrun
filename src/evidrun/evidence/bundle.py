from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any

from evidrun.contracts import (
    AdmissionRecord,
    CheckpointRecord,
    ContractRef,
    EvaluationRecord,
    RunRecord,
    RunSpec,
    parse_revision,
    semantic_model_dump,
)
from evidrun.infrastructure.database import Repository
from evidrun.shared.types import canonical_json, sha256_json, utc_now


class EvidenceBundleService:
    def __init__(self, repository: Repository):
        self.repository = repository

    def export_comparison(self, comparison_id: str, output_path: Path) -> Path:
        comparison = self.repository.get_comparison(comparison_id)
        experiment = self.repository.get_experiment(comparison.experiment_revision_id)
        baseline = self.repository.get_run(comparison.baseline_run_id)
        candidate = self.repository.get_run(comparison.candidate_run_id)
        grades = [
            self._grade_dict(self.repository.get_grade(baseline.id)),
            self._grade_dict(self.repository.get_grade(candidate.id)),
        ]
        events = {
            baseline.id: self.repository.get_run_events(baseline.id),
            candidate.id: self.repository.get_run_events(candidate.id),
        }
        files: dict[str, bytes] = {
            "manifest.json": self._json_bytes(json.loads(experiment.manifest_json)),
            "comparison.json": self._json_bytes(
                {
                    "id": comparison.id,
                    "baseline_run_id": comparison.baseline_run_id,
                    "candidate_run_id": comparison.candidate_run_id,
                    "primary_variable": comparison.primary_variable,
                    "validity": comparison.validity,
                    "baseline_score": comparison.baseline_score,
                    "candidate_score": comparison.candidate_score,
                    "delta": comparison.delta,
                }
            ),
            "grades.json": self._json_bytes(grades),
            "report.md": comparison.report_markdown.encode("utf-8"),
            f"events/{baseline.id}.jsonl": self._jsonl_bytes(events[baseline.id]),
            f"events/{candidate.id}.jsonl": self._jsonl_bytes(events[candidate.id]),
        }
        checksums = {name: hashlib.sha256(content).hexdigest() for name, content in files.items()}
        files["checksums.json"] = self._json_bytes(
            {
                "schema_version": "1",
                "created_at": utc_now().isoformat(),
                "files": checksums,
            }
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, content in files.items():
                archive.writestr(name, content)
        return output_path

    def export_comparison_v2(self, comparison_id: str, output_path: Path) -> Path:
        comparison = self.repository.get_comparison(comparison_id)
        run_rows = [
            self.repository.get_run(comparison.baseline_run_id),
            self.repository.get_run(comparison.candidate_run_id),
        ]
        run_contracts: dict[str, tuple[RunSpec, AdmissionRecord]] = {}
        for run in run_rows:
            contracts = self.repository.get_run_contracts(run.id)
            if contracts is None:
                raise ValueError("Evidence Bundle v2 requires Study-based Runs")
            run_contracts[run.id] = contracts

        files: dict[str, bytes] = {
            "bundle.json": self._json_bytes(
                {
                    "schema_version": "2",
                    "kind": "comparison",
                    "comparison_id": comparison.id,
                    "run_ids": [run.id for run in run_rows],
                }
            ),
            "comparison.json": self._json_bytes(
                {
                    "id": comparison.id,
                    "baseline_run_id": comparison.baseline_run_id,
                    "candidate_run_id": comparison.candidate_run_id,
                    "primary_variable": comparison.primary_variable,
                    "validity": comparison.validity,
                    "baseline_score": comparison.baseline_score,
                    "candidate_score": comparison.candidate_score,
                    "delta": comparison.delta,
                }
            ),
            "report.md": comparison.report_markdown.encode("utf-8"),
        }

        revision_refs: dict[tuple[str, str, int], ContractRef] = {}
        for run in run_rows:
            spec, admission = run_contracts[run.id]
            if run.run_spec_id is None or run.admission_id is None:
                raise ValueError("Evidence Bundle v2 requires Run contract links")
            files[f"run-specs/{run.run_spec_id}.json"] = self._json_bytes(
                self._record_dict(spec)
            )
            files[f"admissions/{run.admission_id}.json"] = self._json_bytes(
                self._record_dict(admission)
            )
            run_record = self.repository.get_run_record(run.id)
            if run_record is None:
                raise ValueError("Evidence Bundle v2 requires a canonical RunRecord")
            files[f"runs/{run.id}.json"] = self._json_bytes(
                semantic_model_dump(run_record)
            )
            files[f"events/{run.id}.jsonl"] = self._jsonl_bytes(
                self.repository.get_run_events(run.id)
            )
            files[f"evaluations/{run.id}.json"] = self._json_bytes(
                [
                    self._record_dict(record)
                    for record in self.repository.get_evaluation_records(run.id)
                ]
            )
            files[f"checkpoints/{run.id}.json"] = self._json_bytes(
                [
                    self._record_dict(record, digest_field="checkpoint_hash")
                    for record in self.repository.get_checkpoint_records(run.id)
                ]
            )
            refs = (
                spec.study_ref,
                spec.goal_ref,
                spec.scenario_ref,
                spec.agent_inventory_ref,
                spec.workspace_template_ref,
                spec.interaction_protocol_ref,
                spec.evaluation_plan_ref,
            )
            for reference in refs:
                revision_refs[
                    (
                        reference.contract_type.value,
                        reference.logical_id,
                        reference.revision,
                    )
                ] = reference
            if spec.checkpoint_policy_ref is not None:
                reference = spec.checkpoint_policy_ref
                revision_refs[
                    (
                        reference.contract_type.value,
                        reference.logical_id,
                        reference.revision,
                    )
                ] = reference

        for (contract_type, logical_id, revision_number), reference in revision_refs.items():
            revision = self.repository.get_contract_revision_by_ref(reference)
            safe_id = logical_id.replace("/", "_")
            files[
                f"contracts/{contract_type}/{safe_id}@{revision_number}.json"
            ] = self._json_bytes(self._record_dict(revision))

        checksums = {name: hashlib.sha256(content).hexdigest() for name, content in files.items()}
        files["checksums.json"] = self._json_bytes(
            {
                "schema_version": "2",
                "created_at": utc_now().isoformat(),
                "files": checksums,
            }
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, content in files.items():
                archive.writestr(name, content)
        return output_path

    def verify(self, bundle_path: Path) -> dict[str, Any]:
        with zipfile.ZipFile(bundle_path) as archive:
            names = set(archive.namelist())
            if "checksums.json" not in names:
                raise ValueError("bundle has no checksums.json")
            checksums = json.loads(archive.read("checksums.json"))["files"]
            checksum_results: dict[str, bool] = {}
            for name, expected in checksums.items():
                actual = hashlib.sha256(archive.read(name)).hexdigest()
                checksum_results[name] = actual == expected

            chain_results: dict[str, bool] = {}
            for name in sorted(item for item in names if item.startswith("events/")):
                events = [json.loads(line) for line in archive.read(name).splitlines() if line]
                previous: str | None = None
                valid = True
                for event in events:
                    stored_hash = event.pop("event_hash")
                    if event["prev_event_hash"] != previous or sha256_json(event) != stored_hash:
                        valid = False
                        break
                    previous = stored_hash
                chain_results[name] = valid

            record_results: dict[str, bool] = {}
            if "bundle.json" in names:
                bundle_manifest = json.loads(archive.read("bundle.json"))
                if bundle_manifest.get("schema_version") == "2":
                    record_results = self._verify_v2_records(archive, names)

        valid = (
            all(checksum_results.values())
            and all(chain_results.values())
            and all(record_results.values())
        )
        return {
            "valid": valid,
            "checksums": checksum_results,
            "event_chains": chain_results,
            "records": record_results,
        }

    @staticmethod
    def _verify_v2_records(
        archive: zipfile.ZipFile, names: set[str]
    ) -> dict[str, bool]:
        results: dict[str, bool] = {}
        event_boundaries: dict[str, dict[int, str]] = {}
        for name in sorted(item for item in names if item.startswith("events/")):
            run_id = Path(name).stem
            events = [json.loads(line) for line in archive.read(name).splitlines() if line]
            event_boundaries[run_id] = {
                int(event["sequence"]): str(event["event_hash"]) for event in events
            }
        checkpoint_ids: dict[str, set[str]] = {}
        for name in sorted(item for item in names if item.startswith("checkpoints/")):
            run_id = Path(name).stem
            documents = json.loads(archive.read(name))
            checkpoint_ids[run_id] = {
                str(document["checkpoint_id"]) for document in documents
            }
        for name in sorted(names):
            try:
                if name.startswith("contracts/") and name.endswith(".json"):
                    document = json.loads(archive.read(name))
                    expected = document.pop("digest")
                    results[name] = parse_revision(document).digest == expected
                elif name.startswith("run-specs/") and name.endswith(".json"):
                    document = json.loads(archive.read(name))
                    expected = document.pop("digest")
                    results[name] = RunSpec.model_validate(document).digest == expected
                elif name.startswith("admissions/") and name.endswith(".json"):
                    document = json.loads(archive.read(name))
                    expected = document.pop("digest")
                    results[name] = AdmissionRecord.model_validate(document).digest == expected
                elif name.startswith("runs/") and name.endswith(".json"):
                    document = json.loads(archive.read(name))
                    record = RunRecord.model_validate(document)
                    spec_name = f"run-specs/{record.run_spec_id}.json"
                    admission_name = f"admissions/{record.admission_id}.json"
                    spec_document = json.loads(archive.read(spec_name))
                    admission_document = json.loads(archive.read(admission_name))
                    results[name] = (
                        record.run_id == Path(name).stem
                        and record.run_spec_digest == spec_document["digest"]
                        and record.admission_digest == admission_document["digest"]
                    )
                elif name.startswith("evaluations/") and name.endswith(".json"):
                    documents = json.loads(archive.read(name))
                    run_id = Path(name).stem
                    results[name] = all(
                        EvidenceBundleService._evaluation_record_valid(
                            document,
                            run_id=run_id,
                            event_boundaries=event_boundaries,
                            checkpoint_ids=checkpoint_ids,
                        )
                        for document in documents
                    )
                elif name.startswith("checkpoints/") and name.endswith(".json"):
                    documents = json.loads(archive.read(name))
                    run_id = Path(name).stem
                    results[name] = all(
                        EvidenceBundleService._checkpoint_record_valid(
                            document,
                            run_id=run_id,
                            event_boundaries=event_boundaries,
                        )
                        for document in documents
                    )
            except (KeyError, TypeError, ValueError):
                results[name] = False
        return results

    @staticmethod
    def _evaluation_record_valid(
        document: dict[str, Any],
        *,
        run_id: str,
        event_boundaries: dict[str, dict[int, str]],
        checkpoint_ids: dict[str, set[str]],
    ) -> bool:
        expected = document["digest"]
        record = EvaluationRecord.model_validate(
            {key: value for key, value in document.items() if key != "digest"}
        )
        if record.digest != expected or record.run_id != run_id:
            return False
        boundary = record.boundary
        if (
            boundary.up_to_event_sequence is not None
            and event_boundaries.get(run_id, {}).get(boundary.up_to_event_sequence)
            != boundary.event_hash
        ):
            return False
        return (
            boundary.checkpoint_id is None
            or boundary.checkpoint_id in checkpoint_ids.get(run_id, set())
        )

    @staticmethod
    def _checkpoint_record_valid(
        document: dict[str, Any],
        *,
        run_id: str,
        event_boundaries: dict[str, dict[int, str]],
    ) -> bool:
        expected = document["checkpoint_hash"]
        record = CheckpointRecord.model_validate(
            {
                key: value
                for key, value in document.items()
                if key != "checkpoint_hash"
            }
        )
        return (
            record.checkpoint_hash == expected
            and record.run_id == run_id
            and event_boundaries.get(run_id, {}).get(record.up_to_event_sequence)
            == record.event_hash
        )

    @staticmethod
    def _json_bytes(value: Any) -> bytes:
        return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()

    @staticmethod
    def _jsonl_bytes(events: list[dict[str, Any]]) -> bytes:
        return ("\n".join(canonical_json(event) for event in events) + "\n").encode()

    @staticmethod
    def _record_dict(model: Any, *, digest_field: str = "digest") -> dict[str, Any]:
        document = semantic_model_dump(model)
        document[digest_field] = getattr(model, digest_field)
        return document

    @staticmethod
    def _grade_dict(row: Any) -> dict[str, Any]:
        return {
            "id": row.id,
            "run_id": row.run_id,
            "grader_id": row.grader_id,
            "score": row.score,
            "passed": row.passed,
            "rationale": row.rationale,
            "evidence": json.loads(row.evidence_json),
        }
