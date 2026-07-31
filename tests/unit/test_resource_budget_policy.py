from __future__ import annotations

from pathlib import Path

from tests.support.resource_budget_cli import commit_baseline, run_checker

BLOCKING_BASE = """
schema_version = "1"
[methodology]
noise_mad_ratio = 0.20
[scenarios.build]
profile = "build"
workload = "path_inventory"
paths = ["dist"]
repetitions = 1
[scenarios.build.metrics.output_bytes]
unit = "bytes"
classification = "generated"
enforcement = "blocking"
baseline = 5
limit = 8
""".strip() + "\n"


def _tracked_policy(tmp_path: Path, body: str = BLOCKING_BASE) -> Path:
    output = tmp_path / "dist"
    output.mkdir()
    (output / "app.js").write_bytes(b"1234567890")
    config = tmp_path / "resource-budget.toml"
    commit_baseline(tmp_path, config, body)
    return config


def test_raised_blocking_limit_requires_a_reviewable_adjustment(tmp_path: Path) -> None:
    config = _tracked_policy(tmp_path)
    changed = BLOCKING_BASE.replace("limit = 8", "limit = 16")
    config.write_text(changed, encoding="utf-8")

    refused = run_checker(tmp_path, config, "build", base_ref="HEAD")

    assert refused.returncode == 2
    assert "build.output_bytes raised 8 -> 16" in refused.stderr
    assert "limit_adjustments" in refused.stderr

    config.write_text(
        changed
        + """
[[limit_adjustments]]
scenario = "build"
metric = "output_bytes"
previous_limit = 8
new_limit = 16
justification = "The reviewed build adds a required production asset."
""",
        encoding="utf-8",
    )
    approved = run_checker(tmp_path, config, "build", base_ref="HEAD")
    assert approved.returncode == 0, approved.stderr


def test_warning_baseline_change_requires_a_reviewable_adjustment(tmp_path: Path) -> None:
    baseline = BLOCKING_BASE.replace(
        'enforcement = "blocking"\nbaseline = 5\nlimit = 8',
        'enforcement = "warning"\nbaseline = 4\nwarning_ratio = 1.5',
    )
    config = _tracked_policy(tmp_path, baseline)
    changed = baseline.replace("baseline = 4", "baseline = 8")
    config.write_text(changed, encoding="utf-8")

    refused = run_checker(tmp_path, config, "build", base_ref="HEAD")

    assert refused.returncode == 2
    assert "build.output_bytes changed warning baseline" in refused.stderr
    assert "baseline_adjustments" in refused.stderr

    config.write_text(
        changed
        + """
[[baseline_adjustments]]
scenario = "build"
metric = "output_bytes"
previous_baseline = 4
new_baseline = 8
previous_warning_ratio = 1.5
new_warning_ratio = 1.5
justification = "The reviewed runtime artifact has a new canonical member."
""",
        encoding="utf-8",
    )
    approved = run_checker(tmp_path, config, "build", base_ref="HEAD")
    assert approved.returncode == 0, approved.stderr


def test_enforcement_cannot_be_relaxed_without_a_policy_adjustment(tmp_path: Path) -> None:
    config = _tracked_policy(tmp_path)
    changed = BLOCKING_BASE.replace('enforcement = "blocking"', 'enforcement = "measure"')
    changed = changed.replace("limit = 8\n", "")
    config.write_text(changed, encoding="utf-8")

    refused = run_checker(tmp_path, config, "build", base_ref="HEAD")

    assert refused.returncode == 2
    assert "build.output_bytes changed enforcement" in refused.stderr
    assert "policy_adjustments" in refused.stderr


def test_metric_cannot_be_removed_without_a_policy_adjustment(tmp_path: Path) -> None:
    baseline = BLOCKING_BASE + """
[scenarios.build.metrics.output_files]
unit = "files"
classification = "generated"
enforcement = "blocking"
limit = 2
    """
    config = _tracked_policy(tmp_path, baseline)
    (tmp_path / "dist" / "app.js").write_bytes(b"1234")
    config.write_text(BLOCKING_BASE, encoding="utf-8")

    refused = run_checker(tmp_path, config, "build", base_ref="HEAD")

    assert refused.returncode == 2
    assert "build.output_files changed metric present -> removed" in refused.stderr

    config.write_text(
        BLOCKING_BASE
        + """
[[policy_adjustments]]
scenario = "build"
metric = "output_files"
field = "metric"
previous = "present"
new = "removed"
justification = "The reviewed policy now relies on the byte limit alone."
""",
        encoding="utf-8",
    )
    approved = run_checker(tmp_path, config, "build", base_ref="HEAD")
    assert approved.returncode == 0, approved.stderr
