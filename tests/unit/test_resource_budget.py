from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from resource_budget.statistics import evaluate_samples  # noqa: E402

from tests.support.resource_budget_cli import run_checker, write_config  # noqa: E402


def test_build_outputs_are_measured_from_real_files(tmp_path: Path) -> None:
    output = tmp_path / "apps" / "web" / "dist"
    output.mkdir(parents=True)
    (output / "index.html").write_bytes(b"12345")
    assets = output / "assets"
    assets.mkdir()
    (assets / "app.js").write_bytes(b"abc")
    config = write_config(
        tmp_path,
        """
schema_version = "1"

[methodology]
noise_spread_ratio = 0.20

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
""",
    )

    completed = run_checker(tmp_path, config, "build")

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


def test_build_inventory_excludes_declared_cache_patterns(tmp_path: Path) -> None:
    output = tmp_path / "apps" / "web" / "dist"
    output.mkdir(parents=True)
    (output / "index.html").write_bytes(b"1234")
    cache = output / "node_modules" / ".cache"
    cache.mkdir(parents=True)
    (cache / "bundle.bin").write_bytes(b"ignored cache bytes")
    config = write_config(
        tmp_path,
        """
schema_version = "1"
[methodology]
noise_spread_ratio = 0.20
[classifications]
cache_excluded = ["**/node_modules/**"]
[scenarios.web_build]
profile = "build"
workload = "path_inventory"
paths = ["apps/web/dist"]
repetitions = 1
[scenarios.web_build.metrics.output_bytes]
unit = "bytes"
classification = "generated"
enforcement = "blocking"
limit = 4
[scenarios.web_build.metrics.output_files]
unit = "files"
classification = "generated"
enforcement = "blocking"
limit = 1
""",
    )

    completed = run_checker(tmp_path, config, "build")

    assert completed.returncode == 0, completed.stderr
    metrics = json.loads(completed.stdout)["scenarios"][0]["metrics"]
    assert [(metric["name"], metric["value"]) for metric in metrics] == [
        ("output_bytes", 4),
        ("output_files", 1),
    ]


def test_warning_metric_reports_a_regression_without_blocking(tmp_path: Path) -> None:
    output = tmp_path / "artifacts"
    output.mkdir()
    (output / "bundle.zip").write_bytes(b"12345678")
    config = write_config(
        tmp_path,
        """
schema_version = "1"

[methodology]
noise_spread_ratio = 0.20

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
""",
    )

    completed = run_checker(tmp_path, config, "build")

    assert completed.returncode == 0, completed.stderr
    metric = json.loads(completed.stdout)["scenarios"][0]["metrics"][0]
    assert metric["status"] == "regression"
    assert metric["threshold"] == 6


def test_noisy_repeated_measurement_is_inconclusive_instead_of_a_regression() -> None:
    result = evaluate_samples(
        (100.0, 140.0, 160.0, 200.0, 240.0),
        baseline=80.0,
        warning_ratio=1.5,
        noise_spread_ratio=0.20,
    )

    assert result.value == 160.0
    assert result.relative_spread == 0.875
    assert result.status == "inconclusive"


def test_a_single_outlier_cannot_be_reported_as_a_stable_measurement() -> None:
    """Relative spread exists because a median absolute deviation was blind here.

    With three samples the deviations from the median are `[b-a, 0, c-b]`, so their
    median is `min(b-a, c-b)`: one tight pair reported MAD 0.0099 for a tenfold
    outlier. Measured on the real python profile, `crl_ctx_002.duration_ms` scored
    relative MAD 0.0000 against a true spread of 0.0531.
    """
    result = evaluate_samples(
        (100.0, 101.0, 1000.0),
        baseline=100.0,
        warning_ratio=2.0,
        noise_spread_ratio=0.60,
    )

    assert result.value == 101.0
    assert result.relative_spread > 0.60
    assert result.status == "inconclusive"


def test_a_tight_repeated_measurement_stays_conclusive() -> None:
    """The noise guard must not swallow every sample: a stable one still concludes."""
    result = evaluate_samples(
        (100.0, 101.0, 102.0),
        baseline=100.0,
        warning_ratio=2.0,
        noise_spread_ratio=0.60,
    )

    assert result.status == "ok"
    assert result.relative_spread < 0.05


def test_python_profile_measures_a_real_evidrun_import(tmp_path: Path) -> None:
    config = write_config(
        tmp_path,
        """
schema_version = "1"

[methodology]
noise_spread_ratio = 0.50

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
""",
    )

    completed = run_checker(ROOT, config, "python")

    assert completed.returncode == 0, completed.stderr
    metrics = json.loads(completed.stdout)["scenarios"][0]["metrics"]
    assert [metric["name"] for metric in metrics] == ["duration_ms", "peak_rss_kib"]
    assert all(len(metric["samples"]) == 3 for metric in metrics)
    assert all(metric["value"] > 0 for metric in metrics)


def test_application_build_runs_real_pnpm_three_times(tmp_path: Path) -> None:
    """The real build workload, exercised by the node CI job.

    The python job has no `pnpm`, so it skips. `.github/workflows/ci.yml` runs this
    file in the node job for exactly that reason: a skip is not coverage, and the
    earlier message claimed coverage the node job did not provide.
    """
    if shutil.which("pnpm") is None:
        pytest.skip("pnpm is absent here; the node CI job runs this file with pnpm present")
    (tmp_path / "package.json").write_text(
        json.dumps({"scripts": {"build": "node build.mjs"}}), encoding="utf-8"
    )
    (tmp_path / "build.mjs").write_text(
        "import { mkdirSync, writeFileSync } from 'node:fs';\n"
        "mkdirSync('dist', { recursive: true });\n"
        "writeFileSync('dist/app.js', 'real build output');\n",
        encoding="utf-8",
    )
    config = write_config(
        tmp_path,
        """
schema_version = "1"
[methodology]
noise_spread_ratio = 0.50
[scenarios.application_build]
profile = "build"
workload = "application_build"
repetitions = 3
[scenarios.application_build.metrics.duration_ms]
unit = "milliseconds"
classification = "timing"
enforcement = "warning"
baseline = 10000
warning_ratio = 2.0
[scenarios.application_build.metrics.peak_rss_kib]
unit = "KiB"
classification = "memory"
enforcement = "warning"
baseline = 1000000
warning_ratio = 2.0
""",
    )

    completed = run_checker(tmp_path, config, "build", timeout=30)

    assert completed.returncode == 0, completed.stderr
    metrics = json.loads(completed.stdout)["scenarios"][0]["metrics"]
    assert all(len(metric["samples"]) == 3 for metric in metrics)
    assert all(metric["value"] > 0 for metric in metrics)
    assert (tmp_path / "dist" / "app.js").read_text() == "real build output"


def test_crl_fixture_and_bundle_use_the_real_runtime(tmp_path: Path) -> None:
    config = write_config(
        tmp_path,
        """
schema_version = "1"

[methodology]
noise_spread_ratio = 0.50

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

[scenarios.crl_ctx_002.metrics.artifact_files]
unit = "files"
classification = "runtime_artifact"
enforcement = "measure"

[scenarios.crl_ctx_002.metrics.artifact_bytes]
unit = "bytes"
classification = "runtime_artifact"
enforcement = "measure"

[scenarios.crl_ctx_002.metrics.database_bytes]
unit = "bytes"
classification = "runtime_artifact"
enforcement = "measure"

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
""",
    )

    completed = run_checker(ROOT, config, "python", timeout=60)

    assert completed.returncode == 0, completed.stderr
    scenarios = {
        scenario["id"]: {metric["name"]: metric for metric in scenario["metrics"]}
        for scenario in json.loads(completed.stdout)["scenarios"]
    }
    assert scenarios["crl_ctx_002"]["run_count"]["value"] == 2
    assert scenarios["crl_ctx_002"]["comparison_count"]["value"] == 1
    assert scenarios["crl_ctx_002"]["event_count"]["value"] >= 12
    assert scenarios["crl_ctx_002"]["artifact_files"]["value"] > 0
    assert scenarios["crl_ctx_002"]["artifact_bytes"]["value"] > 0
    assert scenarios["crl_ctx_002"]["database_bytes"]["value"] > 0
    assert scenarios["run_bundle"]["bundle_bytes"]["value"] > 0
    assert scenarios["run_bundle"]["bundle_files"]["value"] > 0
    assert scenarios["run_bundle"]["bundle_schema_version"]["value"] == 4
    assert scenarios["run_bundle"]["verification_valid"]["value"] == 1


def test_text_report_and_json_artifact_describe_the_same_measurement(tmp_path: Path) -> None:
    output = tmp_path / "dist"
    output.mkdir()
    (output / "app.js").write_bytes(b"1234")
    config = write_config(
        tmp_path,
        """
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
baseline = 4
limit = 8
""",
    )
    artifact = tmp_path / "reports" / "resources.json"

    completed = run_checker(
        tmp_path, config, "build", base_ref="HEAD", output_format=None, json_out=artifact
    )

    assert completed.returncode == 2  # the directory is not a Git repository
    assert "cannot resolve merge-base" in completed.stderr

    completed = run_checker(
        tmp_path, config, "build", output_format=None, json_out=artifact
    )

    assert completed.returncode == 0, completed.stderr
    assert "Resource budgets — build" in completed.stdout
    assert "OK build.output_bytes = 4 bytes" in completed.stdout
    document = json.loads(artifact.read_text(encoding="utf-8"))
    assert document["scenarios"][0]["metrics"][0]["value"] == 4


def test_blocking_minimum_catches_an_invalid_real_measurement(tmp_path: Path) -> None:
    (tmp_path / "dist").mkdir()
    config = write_config(
        tmp_path,
        """
schema_version = "1"
[methodology]
noise_spread_ratio = 0.20
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
""",
    )

    completed = run_checker(tmp_path, config, "build")

    assert completed.returncode == 1
    metric = json.loads(completed.stdout)["scenarios"][0]["metrics"][0]
    assert metric["status"] == "violation"
    assert metric["minimum"] == 1


def test_timing_and_memory_cannot_be_promoted_to_blocking_by_configuration(
    tmp_path: Path,
) -> None:
    (tmp_path / "dist").mkdir()
    config = write_config(
        tmp_path,
        """
schema_version = "1"
[methodology]
noise_spread_ratio = 0.20
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
""",
    )

    completed = run_checker(tmp_path, config, "build")

    assert completed.returncode == 2
    assert "timing and memory must remain warning-only" in completed.stderr


def test_missing_real_build_output_is_reported_as_unavailable(tmp_path: Path) -> None:
    config = write_config(
        tmp_path,
        """
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
baseline = 4
limit = 8
""",
    )

    completed = run_checker(tmp_path, config, "build")

    assert completed.returncode == 2
    metric = json.loads(completed.stdout)["scenarios"][0]["metrics"][0]
    assert metric["status"] == "unavailable"
    assert metric["reason"] == "required paths do not exist: dist"


def test_missing_tooling_is_an_unavailable_measurement_not_a_config_error(
    tmp_path: Path,
) -> None:
    """A tool the runner lacks is a property of the environment, not a broken policy.

    It used to raise before any JSON was written, so the report could not explain
    itself, and a warning-only metric ended up blocking on exit 2.
    """
    (tmp_path / "package.json").write_text('{"scripts":{"build":"node -e 1"}}', "utf-8")
    config = write_config(
        tmp_path,
        """
schema_version = "1"
[methodology]
noise_spread_ratio = 0.60
[scenarios.application_build]
profile = "build"
workload = "application_build"
repetitions = 3
[scenarios.application_build.metrics.duration_ms]
unit = "milliseconds"
classification = "timing"
enforcement = "warning"
baseline = 10000
warning_ratio = 2.0
""",
    )

    completed = run_checker(tmp_path, config, "build", path=("/usr/bin", "/bin"))

    assert completed.returncode == 0, completed.stderr
    document = json.loads(completed.stdout)
    metric = document["scenarios"][0]["metrics"][0]
    assert metric["status"] == "unavailable"
    assert metric["reason"] == "pnpm is not available on this runner"
    assert document["summary"]["unavailable"] == 1


def test_an_unavailable_blocking_metric_still_fails_the_gate(tmp_path: Path) -> None:
    """A bound that cannot be measured leaves the gate unprotected, so it must fail."""
    config = write_config(
        tmp_path,
        """
schema_version = "1"
[methodology]
noise_spread_ratio = 0.60
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
""",
    )

    completed = run_checker(tmp_path, config, "build")

    assert completed.returncode == 2
    metric = json.loads(completed.stdout)["scenarios"][0]["metrics"][0]
    assert metric["status"] == "unavailable"
    assert metric["enforcement"] == "blocking"


def test_requested_profile_cannot_pass_without_any_scenario(tmp_path: Path) -> None:
    config = write_config(
        tmp_path,
        """
schema_version = "1"
[methodology]
noise_spread_ratio = 0.20
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
""",
    )

    completed = run_checker(tmp_path, config, "build")

    assert completed.returncode == 2
    assert "profile build has no scenarios" in completed.stderr
