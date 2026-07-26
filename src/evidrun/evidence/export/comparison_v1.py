"""Bundle v1: the legacy comparison export.

v1 carries no `bundle.json`, so verification has no record layer for it: the format
predates contract-linked Runs. Kept for the CLI's `--legacy-v1` path; new exports use
v2 for comparisons and v3 for a single Run.
"""

from __future__ import annotations

import json
from pathlib import Path

from evidrun.evidence import archive as ar
from evidrun.infrastructure.database import Repository
from evidrun.infrastructure.database.models import ComparisonRow


def export_comparison(repository: Repository, comparison_id: str, output_path: Path) -> Path:
    comparison = repository.read_model.get_comparison(comparison_id)
    experiment = repository.read_model.get_experiment(comparison.experiment_revision_id)
    baseline = repository.read_model.get_run(comparison.baseline_run_id)
    candidate = repository.read_model.get_run(comparison.candidate_run_id)
    files: dict[str, bytes] = {
        "manifest.json": ar.json_bytes(json.loads(experiment.manifest_json)),
        "comparison.json": ar.json_bytes(comparison_document(comparison)),
        "grades.json": ar.json_bytes(
            [
                ar.grade_dict(repository.read_model.get_grade(baseline.id)),
                ar.grade_dict(repository.read_model.get_grade(candidate.id)),
            ]
        ),
        "report.md": comparison.report_markdown.encode("utf-8"),
        f"events/{baseline.id}.jsonl": ar.jsonl_bytes(
            repository.read_model.get_run_events(baseline.id)
        ),
        f"events/{candidate.id}.jsonl": ar.jsonl_bytes(
            repository.read_model.get_run_events(candidate.id)
        ),
    }
    return ar.write_bundle(output_path, files, schema_version="1")


def comparison_document(comparison: ComparisonRow) -> dict[str, object]:
    """O documento de comparison, idêntico em v1 e v2."""

    return {
        "id": comparison.id,
        "baseline_run_id": comparison.baseline_run_id,
        "candidate_run_id": comparison.candidate_run_id,
        "primary_variable": comparison.primary_variable,
        "validity": comparison.validity,
        "baseline_score": comparison.baseline_score,
        "candidate_score": comparison.candidate_score,
        "delta": comparison.delta,
    }
