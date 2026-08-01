from __future__ import annotations

from pathlib import Path

from tests.support.resource_budget_cli import commit_baseline, run_checker

BLOCKING_BASE = """
schema_version = "1"
[methodology]
noise_spread_ratio = 0.20
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
    (tmp_path / "dist" / "app.js").write_bytes(b"1234")
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
    assert "build.output_bytes changed declared baseline" in refused.stderr
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


def test_blocking_baseline_change_requires_a_reviewable_adjustment(tmp_path: Path) -> None:
    config = _tracked_policy(tmp_path)
    (tmp_path / "dist" / "app.js").write_bytes(b"1234")
    changed = BLOCKING_BASE.replace("baseline = 5", "baseline = 6")
    config.write_text(changed, encoding="utf-8")

    refused = run_checker(tmp_path, config, "build", base_ref="HEAD")

    assert refused.returncode == 2
    assert "build.output_bytes changed declared baseline" in refused.stderr

    config.write_text(
        changed
        + """
[[baseline_adjustments]]
scenario = "build"
metric = "output_bytes"
previous_baseline = 5
new_baseline = 6
justification = "The reviewed deterministic baseline reflects the canonical output."
""",
        encoding="utf-8",
    )
    approved = run_checker(tmp_path, config, "build", base_ref="HEAD")
    assert approved.returncode == 0, approved.stderr


def test_blocking_limit_removal_requires_a_reviewable_adjustment(tmp_path: Path) -> None:
    baseline = BLOCKING_BASE.replace("limit = 8", "minimum = 1\nlimit = 8")
    config = _tracked_policy(tmp_path, baseline)
    (tmp_path / "dist" / "app.js").write_bytes(b"1234")
    changed = baseline.replace("limit = 8\n", "")
    config.write_text(changed, encoding="utf-8")

    refused = run_checker(tmp_path, config, "build", base_ref="HEAD")

    assert refused.returncode == 2
    assert "build.output_bytes raised 8 -> removed" in refused.stderr

    config.write_text(
        changed
        + """
[[limit_adjustments]]
scenario = "build"
metric = "output_bytes"
previous_limit = 8
new_limit = "removed"
justification = "The reviewed policy retains only the lower structural boundary."
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



def test_an_adjustment_already_present_at_the_merge_base_does_not_reauthorise(
    tmp_path: Path,
) -> None:
    """A record has to be new for the change it authorises.

    Matching against the current file alone let an approved 8 -> 16 record stay behind
    after a tightening back to 8 and silently authorise the next 8 -> 16, so one
    justification would cover that relaxation for the repository's whole history.
    """
    stale = (
        "\n[[limit_adjustments]]\n"
        'scenario = "build"\n'
        'metric = "output_bytes"\n'
        "previous_limit = 8\n"
        "new_limit = 16\n"
        'justification = "Historical approval that already landed on the base branch."\n'
    )
    config = _tracked_policy(tmp_path, BLOCKING_BASE + stale)
    (tmp_path / "dist" / "app.js").write_bytes(b"123456789012")
    config.write_text(
        BLOCKING_BASE.replace("limit = 8", "limit = 16") + stale, encoding="utf-8"
    )

    refused = run_checker(tmp_path, config, "build", base_ref="HEAD")

    assert refused.returncode == 2
    assert "build.output_bytes raised 8 -> 16" in refused.stderr

    config.write_text(
        BLOCKING_BASE.replace("limit = 8", "limit = 16")
        + stale
        + stale.replace(
            "Historical approval that already landed on the base branch.",
            "This change re-approves the bound with a fresh reviewable record.",
        ),
        encoding="utf-8",
    )

    approved = run_checker(tmp_path, config, "build", base_ref="HEAD")

    assert approved.returncode == 0, approved.stderr


def test_a_limit_relaxed_while_leaving_blocking_still_needs_a_record(
    tmp_path: Path,
) -> None:
    """One approved enforcement change must not smuggle a limit relaxation with it.

    The base side alone decides whether a bound existed, so dropping to `warning` does
    not retire the old limit without its own record.
    """
    config = _tracked_policy(tmp_path)
    (tmp_path / "dist" / "app.js").write_bytes(b"123456789012")
    # Enforcement and baseline changes are both approved here, so the only unrecorded
    # relaxation left is the blocking limit that the merge-base held.
    config.write_text(
        BLOCKING_BASE.replace('enforcement = "blocking"', 'enforcement = "warning"')
        .replace("limit = 8\n", "warning_ratio = 4.0\n")
        + """
[[policy_adjustments]]
scenario = "build"
metric = "output_bytes"
field = "enforcement"
previous = "blocking"
new = "warning"
justification = "The reviewed change demotes this metric while it is recalibrated."

[[baseline_adjustments]]
scenario = "build"
metric = "output_bytes"
previous_baseline = 5
new_baseline = 5
previous_warning_ratio = "absent"
new_warning_ratio = 4.0
justification = "The demoted metric needs a warning ratio while it is recalibrated."
""",
        encoding="utf-8",
    )

    refused = run_checker(tmp_path, config, "build", base_ref="HEAD")

    assert refused.returncode == 2
    assert "build.output_bytes raised 8 -> removed" in refused.stderr
    assert "limit_adjustments" in refused.stderr


def test_a_methodology_field_the_base_lacked_can_be_authorised(tmp_path: Path) -> None:
    """An absent side must be nameable, or the demanded record cannot be written.

    The global check passed `None` straight through while TOML has no null, so adding a
    methodology field demanded a record whose `previous` no author could express. This
    is the real shape of #120's own change: `noise_spread_ratio` did not exist at the
    merge-base. Absent renders as `absent`, matching the metric-level fields.
    """
    config = _tracked_policy(tmp_path)
    # The fixture writes 10 bytes against `limit = 8`; this test is about the record,
    # not the bound, so the measurement has to stay inside it.
    (tmp_path / "dist" / "app.js").write_bytes(b"1234")
    added = BLOCKING_BASE.replace(
        "noise_spread_ratio = 0.20",
        'noise_spread_ratio = 0.20\nstatistic = "median"',
    )
    config.write_text(added, encoding="utf-8")

    refused = run_checker(tmp_path, config, "build", base_ref="HEAD")

    assert refused.returncode == 2
    assert "changed methodology.statistic absent -> median" in refused.stderr

    config.write_text(
        added
        + """
[[policy_adjustments]]
scenario = "*"
metric = "*"
field = "methodology.statistic"
previous = "absent"
new = "median"
justification = "The reviewed change pins the statistic the report already used."
""",
        encoding="utf-8",
    )

    approved = run_checker(tmp_path, config, "build", base_ref="HEAD")

    assert approved.returncode == 0, approved.stderr