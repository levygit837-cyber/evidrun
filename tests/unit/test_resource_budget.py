from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "scripts" / "check_resource_budgets.py"
sys.path.insert(0, str(ROOT / "scripts"))

from resource_budget.statistics import evaluate_samples  # noqa: E402


def test_build_outputs_are_measured_from_real_files(tmp_path: Path) -> None:
    output = tmp_path / "apps" / "web" / "dist"
    output.mkdir(parents=True)
    (output / "index.html").write_bytes(b"12345")
    assets = output / "assets"
    assets.mkdir()
    (assets / "app.js").write_bytes(b"abc")
    config = tmp_path / "resource-budget.toml"
    config.write_text(
        """
schema_version = "1"

[methodology]
noise_mad_ratio = 0.20

[scenarios.web_build]
profile = "build"
workload = "path_inventory"
paths = ["apps/web/dist"]
repetitions = 1

[scenarios.web_build.metrics.output_bytes]
unit = "bytes"
classification = "generated"
enforcement = "blocking"
baseline = 8
limit = 16

[scenarios.web_build.metrics.output_files]
unit = "files"
classification = "generated"
enforcement = "blocking"
baseline = 2
limit = 3
""".strip()
        + "\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--root",
            str(tmp_path),
            "--config",
            str(config),
            "--profile",
            "build",
            "--base-ref",
            "none",
            "--format",
            "json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    document = json.loads(completed.stdout)
    assert document["schema_version"] == "1"
    assert document["summary"] == {
        "inconclusive": 0,
        "ok": 2,
        "regression": 0,
        "unavailable": 0,
        "violation": 0,
    }
    assert document["scenarios"][0]["id"] == "web_build"
    assert [
        (metric["name"], metric["value"], metric["status"])
        for metric in document["scenarios"][0]["metrics"]
    ] == [
        ("output_bytes", 8, "ok"),
        ("output_files", 2, "ok"),
    ]


def test_warning_metric_reports_a_regression_without_blocking(tmp_path: Path) -> None:
    output = tmp_path / "artifacts"
    output.mkdir()
    (output / "bundle.zip").write_bytes(b"12345678")
    config = tmp_path / "resource-budget.toml"
    config.write_text(
        """
schema_version = "1"

[methodology]
noise_mad_ratio = 0.20

[scenarios.bundle]
profile = "build"
workload = "path_inventory"
paths = ["artifacts"]
repetitions = 1

[scenarios.bundle.metrics.output_bytes]
unit = "bytes"
classification = "runtime_artifact"
enforcement = "warning"
baseline = 4
warning_ratio = 1.5
""".strip()
        + "\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--root",
            str(tmp_path),
            "--config",
            str(config),
            "--profile",
            "build",
            "--base-ref",
            "none",
            "--format",
            "json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    metric = json.loads(completed.stdout)["scenarios"][0]["metrics"][0]
    assert metric["status"] == "regression"
    assert metric["threshold"] == 6


def test_noisy_timing_is_inconclusive_instead_of_a_regression() -> None:
    result = evaluate_samples(
        (100.0, 140.0, 160.0, 200.0, 240.0),
        baseline=80.0,
        warning_ratio=1.5,
        noise_mad_ratio=0.20,
    )

    assert result.value == 160.0
    assert result.relative_mad == 0.25
    assert result.status == "inconclusive"


def test_python_profile_measures_a_real_evidrun_import(tmp_path: Path) -> None:
    config = tmp_path / "resource-budget.toml"
    config.write_text(
        """
schema_version = "1"

[methodology]
noise_mad_ratio = 0.50

[scenarios.startup_import]
profile = "python"
workload = "startup_import"
repetitions = 3

[scenarios.startup_import.metrics.duration_ms]
unit = "milliseconds"
classification = "timing"
enforcement = "warning"
baseline = 10000
warning_ratio = 2.0

[scenarios.startup_import.metrics.peak_rss_kib]
unit = "KiB"
classification = "memory"
enforcement = "warning"
baseline = 1000000
warning_ratio = 2.0
""".strip()
        + "\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--root",
            str(ROOT),
            "--config",
            str(config),
            "--profile",
            "python",
            "--base-ref",
            "none",
            "--format",
            "json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    metrics = json.loads(completed.stdout)["scenarios"][0]["metrics"]
    assert [metric["name"] for metric in metrics] == ["duration_ms", "peak_rss_kib"]
    assert all(len(metric["samples"]) == 3 for metric in metrics)
    assert all(metric["value"] > 0 for metric in metrics)


def test_crl_fixture_and_bundle_use_the_real_runtime(tmp_path: Path) -> None:
    config = tmp_path / "resource-budget.toml"
    config.write_text(
        """
schema_version = "1"

[methodology]
noise_mad_ratio = 0.50

[scenarios.crl_ctx_002]
profile = "python"
workload = "crl_ctx_002"
repetitions = 1

[scenarios.crl_ctx_002.metrics.run_count]
unit = "records"
classification = "structural"
enforcement = "measure"
baseline = 2

[scenarios.crl_ctx_002.metrics.comparison_count]
unit = "records"
classification = "structural"
enforcement = "measure"
baseline = 1

[scenarios.crl_ctx_002.metrics.event_count]
unit = "records"
classification = "structural"
enforcement = "measure"
baseline = 18

[scenarios.run_bundle]
profile = "python"
workload = "run_bundle_export_verify"
repetitions = 1

[scenarios.run_bundle.metrics.bundle_bytes]
unit = "bytes"
classification = "runtime_artifact"
enforcement = "warning"
baseline = 1000000
warning_ratio = 2.0

[scenarios.run_bundle.metrics.bundle_files]
unit = "files"
classification = "runtime_artifact"
enforcement = "measure"
baseline = 20

[scenarios.run_bundle.metrics.bundle_schema_version]
unit = "version"
classification = "contract"
enforcement = "measure"
baseline = 4

[scenarios.run_bundle.metrics.verification_valid]
unit = "boolean"
classification = "contract"
enforcement = "blocking"
baseline = 1
limit = 1
""".strip()
        + "\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--root",
            str(ROOT),
            "--config",
            str(config),
            "--profile",
            "python",
            "--base-ref",
            "none",
            "--format",
            "json",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert completed.returncode == 0, completed.stderr
    scenarios = {
        scenario["id"]: {metric["name"]: metric for metric in scenario["metrics"]}
        for scenario in json.loads(completed.stdout)["scenarios"]
    }
    assert scenarios["crl_ctx_002"]["run_count"]["value"] == 2
    assert scenarios["crl_ctx_002"]["comparison_count"]["value"] == 1
    assert scenarios["crl_ctx_002"]["event_count"]["value"] >= 12
    assert scenarios["run_bundle"]["bundle_bytes"]["value"] > 0
    assert scenarios["run_bundle"]["bundle_files"]["value"] > 0
    assert scenarios["run_bundle"]["bundle_schema_version"]["value"] == 4
    assert scenarios["run_bundle"]["verification_valid"]["value"] == 1


def test_raised_blocking_limit_requires_a_reviewable_adjustment(tmp_path: Path) -> None:
    output = tmp_path / "dist"
    output.mkdir()
    (output / "app.js").write_bytes(b"1234567890")
    config = tmp_path / "resource-budget.toml"
    baseline_config = """
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
    config.write_text(baseline_config, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "resource-budget.toml"], cwd=tmp_path, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Resource Test",
            "-c",
            "user.email=resource@example.invalid",
            "commit",
            "-qm",
            "baseline",
        ],
        cwd=tmp_path,
        check=True,
    )
    config.write_text(baseline_config.replace("limit = 8", "limit = 16"), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--root",
            str(tmp_path),
            "--config",
            str(config),
            "--profile",
            "build",
            "--base-ref",
            "HEAD",
            "--format",
            "json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 2
    assert "build.output_bytes raised 8 -> 16" in completed.stderr
    assert "limit_adjustments" in completed.stderr

    config.write_text(
        baseline_config.replace("limit = 8", "limit = 16")
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
    approved = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--root",
            str(tmp_path),
            "--config",
            str(config),
            "--profile",
            "build",
            "--base-ref",
            "HEAD",
            "--format",
            "json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert approved.returncode == 0, approved.stderr


def test_text_report_and_json_artifact_describe_the_same_measurement(tmp_path: Path) -> None:
    output = tmp_path / "dist"
    output.mkdir()
    (output / "app.js").write_bytes(b"1234")
    config = tmp_path / "resource-budget.toml"
    config.write_text(
        """
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
baseline = 4
limit = 8
""".strip()
        + "\n",
        encoding="utf-8",
    )
    artifact = tmp_path / "reports" / "resources.json"

    completed = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--root",
            str(tmp_path),
            "--config",
            str(config),
            "--profile",
            "build",
            "--base-ref",
            "HEAD",
            "--json-out",
            str(artifact),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 2  # the directory is not a Git repository
    assert "cannot resolve merge-base" in completed.stderr

    completed = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--root",
            str(tmp_path),
            "--config",
            str(config),
            "--profile",
            "build",
            "--base-ref",
            "none",
            "--json-out",
            str(artifact),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "Resource budgets — build" in completed.stdout
    assert "OK build.output_bytes = 4 bytes" in completed.stdout
    document = json.loads(artifact.read_text(encoding="utf-8"))
    assert document["scenarios"][0]["metrics"][0]["value"] == 4


def test_blocking_minimum_catches_an_invalid_real_measurement(tmp_path: Path) -> None:
    (tmp_path / "dist").mkdir()
    config = tmp_path / "resource-budget.toml"
    config.write_text(
        """
schema_version = "1"
[methodology]
noise_mad_ratio = 0.20
[scenarios.build]
profile = "build"
workload = "path_inventory"
paths = ["dist"]
repetitions = 1
[scenarios.build.metrics.output_files]
unit = "files"
classification = "generated"
enforcement = "blocking"
baseline = 1
minimum = 1
""".strip()
        + "\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--root",
            str(tmp_path),
            "--config",
            str(config),
            "--profile",
            "build",
            "--base-ref",
            "none",
            "--format",
            "json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    metric = json.loads(completed.stdout)["scenarios"][0]["metrics"][0]
    assert metric["status"] == "violation"
    assert metric["minimum"] == 1


def test_timing_and_memory_cannot_be_promoted_to_blocking_by_configuration(
    tmp_path: Path,
) -> None:
    (tmp_path / "dist").mkdir()
    config = tmp_path / "resource-budget.toml"
    config.write_text(
        """
schema_version = "1"
[methodology]
noise_mad_ratio = 0.20
[scenarios.build]
profile = "build"
workload = "path_inventory"
paths = ["dist"]
repetitions = 1
[scenarios.build.metrics.output_files]
unit = "files"
classification = "timing"
enforcement = "blocking"
baseline = 0
limit = 1
""".strip()
        + "\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--root",
            str(tmp_path),
            "--config",
            str(config),
            "--profile",
            "build",
            "--base-ref",
            "none",
            "--format",
            "json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 2
    assert "timing and memory must remain warning-only" in completed.stderr


def test_missing_real_build_output_is_reported_as_unavailable(tmp_path: Path) -> None:
    config = tmp_path / "resource-budget.toml"
    config.write_text(
        """
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
baseline = 4
limit = 8
""".strip()
        + "\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--root",
            str(tmp_path),
            "--config",
            str(config),
            "--profile",
            "build",
            "--base-ref",
            "none",
            "--format",
            "json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 2
    metric = json.loads(completed.stdout)["scenarios"][0]["metrics"][0]
    assert metric["status"] == "unavailable"
    assert metric["reason"] == "required paths do not exist: dist"


def test_requested_profile_cannot_pass_without_any_scenario(tmp_path: Path) -> None:
    config = tmp_path / "resource-budget.toml"
    config.write_text(
        """
schema_version = "1"
[methodology]
noise_mad_ratio = 0.20
[scenarios.startup]
profile = "python"
workload = "startup_import"
repetitions = 3
[scenarios.startup.metrics.duration_ms]
unit = "milliseconds"
classification = "timing"
enforcement = "warning"
baseline = 1000
warning_ratio = 1.5
""".strip()
        + "\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--root",
            str(tmp_path),
            "--config",
            str(config),
            "--profile",
            "build",
            "--base-ref",
            "none",
            "--format",
            "json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 2
    assert "profile build has no scenarios" in completed.stderr
