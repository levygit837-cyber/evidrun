from __future__ import annotations

from pathlib import Path

from evidrun.evidence.bundle import EvidenceBundleService
from evidrun.infrastructure.database import Repository
from evidrun.runs import EvidrunService

ROOT = Path(__file__).resolve().parents[2]


def test_demo_runs_end_to_end_and_bundle_verifies(
    repository: Repository, tmp_path: Path
) -> None:
    result = EvidrunService(repository).bootstrap_demo(ROOT / "benchmarks")
    dashboard = repository.latest_dashboard()

    assert dashboard["summary"]["runs"] == 2
    assert dashboard["summary"]["comparisons"] == 1
    assert dashboard["summary"]["events"] >= 12

    runs = {run["variant_id"]: run for run in dashboard["runs"]}
    assert runs["head-truncation"]["grade"]["score"] == 0
    assert runs["tail-preservation"]["grade"]["score"] == 1
    assert result["context_diff"]["added_root_cause"] is True

    bundle = tmp_path / "demo.evidrun.zip"
    bundle_service = EvidenceBundleService(repository)
    bundle_service.export_comparison(result["comparison_id"], bundle)
    verification = bundle_service.verify(bundle)
    assert verification["valid"] is True

