"""Protect baselines and blocking policy from silent relaxation."""

from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path
from typing import Any


def validate_baseline_changes(
    root: Path,
    config_path: Path,
    config: dict[str, Any],
    base_ref: str,
) -> None:
    """Compare policy at the merge-base and require reviewable change records."""

    base = _config_at_ref(root, config_path, base_ref)
    if base is None:
        return
    _check_global_policy_field(
        config,
        "methodology.noise_mad_ratio",
        base.get("methodology", {}).get("noise_mad_ratio"),
        config.get("methodology", {}).get("noise_mad_ratio"),
    )
    _check_global_policy_field(
        config,
        "classifications.cache_excluded",
        base.get("classifications", {}).get("cache_excluded", []),
        config.get("classifications", {}).get("cache_excluded", []),
    )
    current_scenarios = config["scenarios"]
    for scenario_id, base_scenario in base.get("scenarios", {}).items():
        current_scenario = current_scenarios.get(scenario_id)
        if current_scenario is None:
            _require_policy_adjustment(
                config, scenario_id, "*", "scenario", "present", "removed"
            )
            continue
        for field in ("profile", "workload", "repetitions", "paths"):
            _check_policy_field(config, scenario_id, "*", field, base_scenario, current_scenario)
        for metric_name, base_metric in base_scenario.get("metrics", {}).items():
            current_metric = current_scenario.get("metrics", {}).get(metric_name)
            if current_metric is None:
                _require_policy_adjustment(
                    config, scenario_id, metric_name, "metric", "present", "removed"
                )
                continue
            for field in ("classification", "enforcement", "unit"):
                _check_policy_field(
                    config,
                    scenario_id,
                    metric_name,
                    field,
                    base_metric,
                    current_metric,
                )
            _check_metric_baseline(config, scenario_id, metric_name, base_metric, current_metric)
            _check_blocking_bounds(
                config,
                scenario_id,
                metric_name,
                base_metric,
                current_metric,
            )


def _check_global_policy_field(
    config: dict[str, Any], field: str, previous: object, new: object
) -> None:
    if previous != new:
        _require_policy_adjustment(config, "*", "*", field, previous, new)


def _check_policy_field(
    config: dict[str, Any],
    scenario_id: str,
    metric_name: str,
    field: str,
    base: dict[str, Any],
    current: dict[str, Any],
) -> None:
    if base.get(field) != current.get(field):
        _require_policy_adjustment(
            config,
            scenario_id,
            metric_name,
            field,
            base.get(field, "absent"),
            current.get(field, "removed"),
        )


def _check_metric_baseline(
    config: dict[str, Any],
    scenario_id: str,
    metric_name: str,
    base: dict[str, Any],
    current: dict[str, Any],
) -> None:
    old_baseline = base.get("baseline")
    new_baseline = current.get("baseline")
    old_ratio = base.get("warning_ratio")
    new_ratio = current.get("warning_ratio")
    if old_baseline == new_baseline and old_ratio == new_ratio:
        return
    rendered_old_baseline: object = (
        old_baseline if "baseline" in base else "absent"
    )
    rendered_new_baseline: object = (
        new_baseline if "baseline" in current else "removed"
    )
    expected = {
        "scenario": scenario_id,
        "metric": metric_name,
        "previous_baseline": rendered_old_baseline,
        "new_baseline": rendered_new_baseline,
    }
    if "warning_ratio" in base or "warning_ratio" in current:
        expected.update(
            previous_warning_ratio=(
                old_ratio if "warning_ratio" in base else "absent"
            ),
            new_warning_ratio=(
                new_ratio if "warning_ratio" in current else "removed"
            ),
        )
    if not _has_exact_adjustment(config.get("baseline_adjustments", []), **expected):
        raise ValueError(
            f"{scenario_id}.{metric_name} changed declared baseline "
            f"{rendered_old_baseline} x {old_ratio} -> "
            f"{rendered_new_baseline} x {new_ratio}; "
            "add a matching [[baseline_adjustments]] record with a reviewable justification"
        )


def _check_blocking_bounds(
    config: dict[str, Any],
    scenario_id: str,
    metric_name: str,
    base: dict[str, Any],
    current: dict[str, Any],
) -> None:
    if base.get("enforcement") != "blocking" or current.get("enforcement") != "blocking":
        return
    old_limit = base.get("limit")
    new_limit = current.get("limit")
    if (
        old_limit is not None
        and (new_limit is None or new_limit > old_limit)
    ):
        _require_limit_adjustment(
            config, scenario_id, metric_name, "maximum", old_limit, new_limit
        )
    old_minimum = base.get("minimum")
    new_minimum = current.get("minimum")
    if (
        old_minimum is not None
        and (new_minimum is None or new_minimum < old_minimum)
    ):
        _require_limit_adjustment(
            config, scenario_id, metric_name, "minimum", old_minimum, new_minimum
        )


def _require_policy_adjustment(
    config: dict[str, Any],
    scenario_id: str,
    metric_name: str,
    field: str,
    previous: object,
    new: object,
) -> None:
    if _has_exact_adjustment(
        config.get("policy_adjustments", []),
        scenario=scenario_id,
        metric=metric_name,
        field=field,
        previous=previous,
        new=new,
    ):
        return
    subject = scenario_id if metric_name == "*" else f"{scenario_id}.{metric_name}"
    raise ValueError(
        f"{subject} changed {field} {previous} -> {new}; add a matching "
        "[[policy_adjustments]] record with a reviewable justification"
    )


def _require_limit_adjustment(
    config: dict[str, Any],
    scenario_id: str,
    metric_name: str,
    bound: str,
    previous: int | float,
    new: int | float | None,
) -> None:
    rendered_new: object = "removed" if new is None else new
    expected = {
        "scenario": scenario_id,
        "metric": metric_name,
        "previous_limit": previous,
        "new_limit": rendered_new,
    }
    adjustments = config.get("limit_adjustments", [])
    if _has_exact_adjustment(adjustments, bound=bound, **expected) or (
        bound == "maximum" and _has_exact_adjustment(adjustments, **expected)
    ):
        return
    action = "raised" if bound == "maximum" else "lowered minimum"
    raise ValueError(
        f"{scenario_id}.{metric_name} {action} {previous} -> {rendered_new} "
        "and relaxed the old bound; add a matching "
        "[[limit_adjustments]] record with a reviewable justification"
    )


def _has_exact_adjustment(
    adjustments: list[dict[str, Any]], **expected: object
) -> bool:
    return any(
        all(adjustment.get(key) == value for key, value in expected.items())
        and _reviewable(adjustment.get("justification"))
        for adjustment in adjustments
    )


def _reviewable(value: object) -> bool:
    justification = str(value or "").strip()
    return len(justification) >= 20 and justification.lower() not in {
        "pending",
        "tbd",
        "todo",
        "n/a",
    }


def _config_at_ref(root: Path, config_path: Path, base_ref: str) -> dict[str, Any] | None:
    try:
        relative = config_path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError("--config must be inside --root when --base-ref is used") from exc
    merge_base = subprocess.run(
        ["git", "-C", str(root), "merge-base", "HEAD", base_ref],
        check=False,
        capture_output=True,
        text=True,
    )
    if merge_base.returncode != 0:
        raise ValueError(f"cannot resolve merge-base with {base_ref}")
    revision = merge_base.stdout.strip()
    shown = subprocess.run(
        ["git", "-C", str(root), "show", f"{revision}:{relative.as_posix()}"],
        check=False,
        capture_output=True,
        text=True,
    )
    if shown.returncode != 0:
        return None
    return tomllib.loads(shown.stdout)
