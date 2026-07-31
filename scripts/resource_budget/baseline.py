"""Protect blocking limits from being raised without reviewable justification."""

from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path
from typing import Any


def validate_limit_adjustments(
    root: Path,
    config_path: Path,
    config: dict[str, Any],
    document: dict[str, Any],
    base_ref: str,
) -> None:
    """Require an explicit record when this checkout exceeds and raises an old limit."""

    base = _config_at_ref(root, config_path, base_ref)
    if base is None:
        return
    measured = {
        (scenario["id"], metric["name"]): metric["value"]
        for scenario in document["scenarios"]
        for metric in scenario["metrics"]
    }
    adjustments = config.get("limit_adjustments", [])
    for scenario_id, current_scenario in config["scenarios"].items():
        base_scenario = base.get("scenarios", {}).get(scenario_id)
        if base_scenario is None:
            continue
        for metric_name, current_metric in current_scenario["metrics"].items():
            base_metric = base_scenario.get("metrics", {}).get(metric_name)
            if base_metric is None:
                continue
            old_limit = base_metric.get("limit")
            new_limit = current_metric.get("limit")
            old_minimum = base_metric.get("minimum")
            new_minimum = current_metric.get("minimum")
            value = measured.get((scenario_id, metric_name))
            if (
                old_limit is None
                or new_limit is None
                or new_limit <= old_limit
                or value is None
                or value <= old_limit
            ):
                pass
            elif not _has_adjustment(
                adjustments,
                scenario_id=scenario_id,
                metric_name=metric_name,
                old_limit=old_limit,
                new_limit=new_limit,
                bound="maximum",
            ):
                raise ValueError(
                    f"{scenario_id}.{metric_name} raised {old_limit} -> {new_limit} "
                    "while the measurement exceeds the old limit; add a matching "
                    "[[limit_adjustments]] record with a reviewable justification"
                )
            if (
                old_minimum is not None
                and new_minimum is not None
                and new_minimum < old_minimum
                and value is not None
                and value < old_minimum
                and not _has_adjustment(
                    adjustments,
                    scenario_id=scenario_id,
                    metric_name=metric_name,
                    old_limit=old_minimum,
                    new_limit=new_minimum,
                    bound="minimum",
                )
            ):
                raise ValueError(
                    f"{scenario_id}.{metric_name} lowered minimum "
                    f"{old_minimum} -> {new_minimum} while the measurement is below "
                    "the old minimum; add a matching [[limit_adjustments]] record "
                    "with bound = 'minimum' and a reviewable justification"
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


def _has_adjustment(
    adjustments: list[dict[str, Any]],
    *,
    scenario_id: str,
    metric_name: str,
    old_limit: int | float,
    new_limit: int | float,
    bound: str,
) -> bool:
    for adjustment in adjustments:
        justification = str(adjustment.get("justification", "")).strip()
        if (
            adjustment.get("scenario") == scenario_id
            and adjustment.get("metric") == metric_name
            and adjustment.get("previous_limit") == old_limit
            and adjustment.get("new_limit") == new_limit
            and adjustment.get("bound", "maximum") == bound
            and len(justification) >= 20
            and justification.lower() not in {"pending", "tbd", "todo", "n/a"}
        ):
            return True
    return False
