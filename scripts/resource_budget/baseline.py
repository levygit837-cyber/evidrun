"""Protect baselines and blocking policy from silent relaxation."""

from __future__ import annotations

import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

METHODOLOGY_FIELDS = ("noise_spread_ratio", "dispersion", "statistic")
METRIC_POLICY_FIELDS = ("classification", "enforcement", "unit")
SCENARIO_POLICY_FIELDS = ("profile", "workload", "repetitions", "paths")
PLACEHOLDER_JUSTIFICATIONS = frozenset({"pending", "tbd", "todo", "n/a", "-", "?"})
MINIMUM_JUSTIFICATION_LENGTH = 20


@dataclass(frozen=True)
class PolicyComparison:
    """The versioned policy on both sides of a change.

    Both documents travel together through every check, and the adjustment records are
    read from both: a record that already existed at the merge-base cannot authorise
    the change this diff introduces.
    """

    base: dict[str, Any]
    current: dict[str, Any]

    def authorises(self, table: str, **expected: object) -> bool:
        """True when this change adds a reviewable record matching `expected`.

        The record must be *new*. Matching against the current document alone let an
        approved 8 -> 16 record stay behind after a tightening back to 8 and silently
        re-authorise the next 8 -> 16, so each relaxation would only ever need one
        justification in the repository's whole history.
        """
        return self._matches(self.current, table, expected) > self._matches(
            self.base, table, expected
        )

    @staticmethod
    def _matches(
        document: dict[str, Any], table: str, expected: dict[str, object]
    ) -> int:
        records: list[dict[str, Any]] = document.get(table, [])
        return sum(
            all(record.get(key) == value for key, value in expected.items())
            and _reviewable(record.get("justification"))
            for record in records
        )


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
    comparison = PolicyComparison(base=base, current=config)
    for field in METHODOLOGY_FIELDS:
        _check_global_policy_field(
            comparison,
            f"methodology.{field}",
            base.get("methodology", {}).get(field),
            config.get("methodology", {}).get(field),
        )
    _check_global_policy_field(
        comparison,
        "classifications.cache_excluded",
        base.get("classifications", {}).get("cache_excluded", []),
        config.get("classifications", {}).get("cache_excluded", []),
    )
    current_scenarios = config["scenarios"]
    for scenario_id, base_scenario in base.get("scenarios", {}).items():
        current_scenario = current_scenarios.get(scenario_id)
        if current_scenario is None:
            _require_policy_adjustment(
                comparison, scenario_id, "*", "scenario", "present", "removed"
            )
            continue
        for field in SCENARIO_POLICY_FIELDS:
            _check_policy_field(
                comparison, scenario_id, "*", field, base_scenario, current_scenario
            )
        for metric_name, base_metric in base_scenario.get("metrics", {}).items():
            current_metric = current_scenario.get("metrics", {}).get(metric_name)
            if current_metric is None:
                _require_policy_adjustment(
                    comparison, scenario_id, metric_name, "metric", "present", "removed"
                )
                continue
            for field in METRIC_POLICY_FIELDS:
                _check_policy_field(
                    comparison,
                    scenario_id,
                    metric_name,
                    field,
                    base_metric,
                    current_metric,
                )
            _check_metric_baseline(
                comparison, scenario_id, metric_name, base_metric, current_metric
            )
            _check_blocking_bounds(
                comparison, scenario_id, metric_name, base_metric, current_metric
            )


def _check_global_policy_field(
    comparison: PolicyComparison, field: str, previous: object, new: object
) -> None:
    """Require a record for a repository-wide policy change.

    Absent values render as `absent`/`removed`, the same convention the metric fields
    already use. TOML has no null, so a record could not name `None`, which made
    renaming a methodology field unauthorisable: the checker demanded a record whose
    `previous` no author could write.
    """

    if previous == new:
        return
    _require_policy_adjustment(
        comparison,
        "*",
        "*",
        field,
        "absent" if previous is None else previous,
        "removed" if new is None else new,
    )


def _check_policy_field(
    comparison: PolicyComparison,
    scenario_id: str,
    metric_name: str,
    field: str,
    base: dict[str, Any],
    current: dict[str, Any],
) -> None:
    if base.get(field) != current.get(field):
        _require_policy_adjustment(
            comparison,
            scenario_id,
            metric_name,
            field,
            base.get(field, "absent"),
            current.get(field, "removed"),
        )


def _check_metric_baseline(
    comparison: PolicyComparison,
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
    rendered_old_baseline: object = old_baseline if "baseline" in base else "absent"
    rendered_new_baseline: object = new_baseline if "baseline" in current else "removed"
    expected: dict[str, object] = {
        "scenario": scenario_id,
        "metric": metric_name,
        "previous_baseline": rendered_old_baseline,
        "new_baseline": rendered_new_baseline,
    }
    if "warning_ratio" in base or "warning_ratio" in current:
        expected.update(
            previous_warning_ratio=(old_ratio if "warning_ratio" in base else "absent"),
            new_warning_ratio=(new_ratio if "warning_ratio" in current else "removed"),
        )
    if not comparison.authorises("baseline_adjustments", **expected):
        raise ValueError(
            f"{scenario_id}.{metric_name} changed declared baseline "
            f"{rendered_old_baseline} x {old_ratio} -> "
            f"{rendered_new_baseline} x {new_ratio}; "
            "add a matching [[baseline_adjustments]] record with a reviewable justification"
        )


def _check_blocking_bounds(
    comparison: PolicyComparison,
    scenario_id: str,
    metric_name: str,
    base: dict[str, Any],
    current: dict[str, Any],
) -> None:
    """Require a record whenever a bound the merge-base enforced gets weaker.

    The base side alone decides whether a bound existed. Requiring both sides to be
    `blocking` would let one approved enforcement change carry a simultaneous limit
    relaxation with no record of its own.
    """
    if base.get("enforcement") != "blocking":
        return
    old_limit = base.get("limit")
    new_limit = current.get("limit") if current.get("enforcement") == "blocking" else None
    if old_limit is not None and (new_limit is None or new_limit > old_limit):
        _require_limit_adjustment(
            comparison, scenario_id, metric_name, "maximum", old_limit, new_limit
        )
    old_minimum = base.get("minimum")
    new_minimum = (
        current.get("minimum") if current.get("enforcement") == "blocking" else None
    )
    if old_minimum is not None and (new_minimum is None or new_minimum < old_minimum):
        _require_limit_adjustment(
            comparison, scenario_id, metric_name, "minimum", old_minimum, new_minimum
        )


def _require_policy_adjustment(
    comparison: PolicyComparison,
    scenario_id: str,
    metric_name: str,
    field: str,
    previous: object,
    new: object,
) -> None:
    if comparison.authorises(
        "policy_adjustments",
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
    comparison: PolicyComparison,
    scenario_id: str,
    metric_name: str,
    bound: str,
    previous: int | float,
    new: int | float | None,
) -> None:
    rendered_new: object = "removed" if new is None else new
    expected: dict[str, object] = {
        "scenario": scenario_id,
        "metric": metric_name,
        "previous_limit": previous,
        "new_limit": rendered_new,
    }
    if comparison.authorises("limit_adjustments", bound=bound, **expected) or (
        bound == "maximum" and comparison.authorises("limit_adjustments", **expected)
    ):
        return
    action = "raised" if bound == "maximum" else "lowered minimum"
    raise ValueError(
        f"{scenario_id}.{metric_name} {action} {previous} -> {rendered_new} "
        "and relaxed the old bound; add a matching "
        "[[limit_adjustments]] record with a reviewable justification"
    )


def _reviewable(value: object) -> bool:
    justification = str(value or "").strip()
    return (
        len(justification) >= MINIMUM_JUSTIFICATION_LENGTH
        and justification.lower() not in PLACEHOLDER_JUSTIFICATIONS
    )


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
