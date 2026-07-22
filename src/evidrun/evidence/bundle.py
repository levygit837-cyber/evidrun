from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any

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

        valid = all(checksum_results.values()) and all(chain_results.values())
        return {"valid": valid, "checksums": checksum_results, "event_chains": chain_results}

    @staticmethod
    def _json_bytes(value: Any) -> bytes:
        return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()

    @staticmethod
    def _jsonl_bytes(events: list[dict[str, Any]]) -> bytes:
        return ("\n".join(canonical_json(event) for event in events) + "\n").encode()

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
