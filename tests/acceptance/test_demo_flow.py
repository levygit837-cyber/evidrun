from __future__ import annotations

from pathlib import Path
from uuid import UUID

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
    assert all(UUID(run["id"].removeprefix("run_")).version == 7 for run in runs.values())
    assert runs["head-truncation"]["grade"]["score"] == 0
    assert runs["tail-preservation"]["grade"]["score"] == 1
    assert runs["head-truncation"]["output"] == "[REDACTED]"
    assert runs["tail-preservation"]["output"] == "[REDACTED]"
    assert all(
        run["context_snapshot"]["selected_content"] == "[REDACTED]"
        for run in runs.values()
    )
    terminal_by_variant = {
        variant_id: repository.get_run_events(run["id"])[-1]["payload"]
        for variant_id, run in runs.items()
    }
    assert terminal_by_variant["head-truncation"]["goal_result"] == {
        "goal_mode": "goal_state",
        "state": "not_achieved",
    }
    assert terminal_by_variant["tail-preservation"]["goal_result"] == {
        "goal_mode": "goal_state",
        "state": "achieved",
    }
    assert result["context_diff"]["added_root_cause"] is True

    bundle = tmp_path / "demo.evidrun.zip"
    bundle_service = EvidenceBundleService(repository)
    bundle_service.export_comparison(result["comparison_id"], bundle)
    verification = bundle_service.verify(bundle)
    assert verification["valid"] is True
