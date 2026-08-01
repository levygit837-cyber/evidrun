"""Validation for the versioned resource-budget policy."""

from __future__ import annotations

from typing import Any, cast

WORKLOAD_METRICS = {
    "path_inventory": frozenset({"output_bytes", "output_files"}),
    "application_build": frozenset({"duration_ms", "peak_rss_kib"}),
    "startup_import": frozenset({"duration_ms", "peak_rss_kib"}),
    "crl_ctx_002": frozenset(
        {
            "duration_ms",
            "peak_rss_kib",
            "run_count",
            "comparison_count",
            "event_count",
            "artifact_files",
            "artifact_bytes",
            "database_bytes",
        }
    ),
    "run_bundle_export_verify": frozenset(
        {
            "duration_ms",
            "peak_rss_kib",
            "bundle_bytes",
            "bundle_files",
            "bundle_schema_version",
            "verification_valid",
        }
    ),
}
CLASSIFICATIONS = frozenset(
    {"timing", "memory", "generated", "runtime_artifact", "structural", "contract"}
)
ENFORCEMENTS = frozenset({"measure", "warning", "blocking"})


def validate_policy(config: dict[str, Any]) -> None:
    if config.get("schema_version") != "1":
        raise ValueError("resource budget schema_version must be '1'")
    noise_ratio = config.get("methodology", {}).get("noise_spread_ratio")
    if not isinstance(noise_ratio, (int, float)) or not 0 <= noise_ratio <= 1:
        raise ValueError("methodology.noise_spread_ratio must be between 0 and 1")
    raw_classifications = cast(object, config.get("classifications", {}))
    if not isinstance(raw_classifications, dict):
        raise ValueError("classifications must be a table")
    classifications = cast(dict[str, object], raw_classifications)
    raw_cache_excluded = classifications.get("cache_excluded", [])
    if not isinstance(raw_cache_excluded, list):
        raise ValueError("classifications.cache_excluded must be a list of glob patterns")
    cache_excluded = cast(list[object], raw_cache_excluded)
    if not all(
        isinstance(pattern, str) and pattern.strip() for pattern in cache_excluded
    ):
        raise ValueError("classifications.cache_excluded must be a list of glob patterns")
    raw_scenarios = config.get("scenarios")
    if not isinstance(raw_scenarios, dict) or not raw_scenarios:
        raise ValueError("at least one scenario is required")
    scenarios = cast(dict[str, dict[str, Any]], raw_scenarios)
    for scenario_id, scenario in scenarios.items():
        _validate_scenario(str(scenario_id), scenario)


def _validate_scenario(scenario_id: str, scenario: dict[str, Any]) -> None:
    if scenario.get("profile") not in {"python", "build"}:
        raise ValueError(f"{scenario_id}.profile must be python or build")
    workload = scenario.get("workload")
    if workload not in WORKLOAD_METRICS:
        raise ValueError(f"{scenario_id}.workload is unknown: {workload}")
    repetitions = scenario.get("repetitions")
    if not isinstance(repetitions, int) or repetitions < 1:
        raise ValueError(f"{scenario_id}.repetitions must be a positive integer")
    if workload == "path_inventory" and not scenario.get("paths"):
        raise ValueError(f"{scenario_id}.paths must name at least one build output")
    raw_metrics = scenario.get("metrics")
    if not isinstance(raw_metrics, dict) or not raw_metrics:
        raise ValueError(f"{scenario_id}.metrics must not be empty")
    metrics = cast(dict[str, dict[str, Any]], raw_metrics)
    unknown = set(metrics) - WORKLOAD_METRICS[workload]
    if unknown:
        raise ValueError(f"{scenario_id} has unsupported metrics: {sorted(unknown)}")
    for metric_name, metric in metrics.items():
        _validate_metric(scenario_id, str(metric_name), metric, repetitions)


def _validate_metric(
    scenario_id: str,
    metric_name: str,
    metric: dict[str, Any],
    repetitions: int,
) -> None:
    prefix = f"{scenario_id}.{metric_name}"
    classification = metric.get("classification")
    enforcement = metric.get("enforcement")
    if classification not in CLASSIFICATIONS:
        raise ValueError(f"{prefix}.classification is unknown")
    if enforcement not in ENFORCEMENTS:
        raise ValueError(f"{prefix}.enforcement is unknown")
    if not str(metric.get("unit", "")).strip():
        raise ValueError(f"{prefix}.unit is required")
    if classification in {"timing", "memory"}:
        if enforcement != "warning":
            raise ValueError("timing and memory must remain warning-only in Issue #48")
        if repetitions < 3:
            raise ValueError(f"{prefix} requires at least three repetitions")
    if enforcement == "warning":
        baseline = metric.get("baseline")
        ratio = metric.get("warning_ratio")
        if not isinstance(baseline, (int, float)) or baseline < 0:
            raise ValueError(f"{prefix}.baseline must be a non-negative number")
        if not isinstance(ratio, (int, float)) or ratio <= 1:
            raise ValueError(f"{prefix}.warning_ratio must be greater than 1")
    if enforcement == "blocking":
        minimum = metric.get("minimum")
        limit = metric.get("limit")
        if minimum is None and limit is None:
            raise ValueError(f"{prefix} blocking policy needs minimum or limit")
        if minimum is not None and limit is not None and minimum > limit:
            raise ValueError(f"{prefix}.minimum cannot exceed limit")
