"""Measure versioned resource budgets for representative repository scenarios."""

from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
import tomllib
from pathlib import Path
from statistics import median
from typing import Any

from resource_budget.baseline import validate_baseline_changes
from resource_budget.environment import measurement_environment
from resource_budget.policy import validate_policy
from resource_budget.render import json_document, text_document
from resource_budget.statistics import evaluate_samples


def _path_inventory(
    root: Path, paths: list[str], excluded_patterns: list[str]
) -> dict[str, int] | None:
    files: list[Path] = []
    for relative in paths:
        target = root / relative
        if not target.exists():
            return None
        files.extend(
            path
            for path in target.rglob("*")
            if path.is_file()
            and not any(
                fnmatch.fnmatch(path.relative_to(root).as_posix(), pattern)
                for pattern in excluded_patterns
            )
        )
    return {
        "output_bytes": sum(path.stat().st_size for path in files),
        "output_files": len(files),
    }


def _evaluate_metric(
    name: str,
    samples: list[float],
    policy: dict[str, Any],
    *,
    noise_mad_ratio: float,
) -> dict[str, Any]:
    value = float(median(samples))
    status = "ok"
    limit = policy.get("limit")
    minimum = policy.get("minimum")
    threshold = None
    relative_mad = None
    if policy.get("enforcement") == "blocking" and limit is not None and any(
        sample > limit for sample in samples
    ):
        status = "violation"
    if policy.get("enforcement") == "blocking" and minimum is not None and any(
        sample < minimum for sample in samples
    ):
        status = "violation"
    if policy.get("enforcement") == "warning":
        baseline = policy.get("baseline")
        warning_ratio = policy.get("warning_ratio")
        if baseline is not None and warning_ratio is not None:
            if len(samples) >= 3:
                evaluation = evaluate_samples(
                    tuple(samples),
                    baseline=float(baseline),
                    warning_ratio=float(warning_ratio),
                    noise_mad_ratio=noise_mad_ratio,
                )
                value = evaluation.value
                threshold = evaluation.threshold
                relative_mad = evaluation.relative_mad
                status = evaluation.status
            else:
                threshold = baseline * warning_ratio
                if value > threshold:
                    status = "regression"
    return {
        "name": name,
        "value": value,
        "samples": samples,
        "relative_mad": relative_mad,
        "unit": policy["unit"],
        "classification": policy["classification"],
        "enforcement": policy["enforcement"],
        "baseline": policy.get("baseline"),
        "limit": limit,
        "minimum": minimum,
        "threshold": threshold,
        "status": status,
    }


def _run_workload(root: Path, workload: str, repetitions: int) -> dict[str, list[float]]:
    samples: dict[str, list[float]] = {}
    runner = Path(__file__).with_name("resource_budget") / "workloads.py"
    for _ in range(repetitions):
        completed = subprocess.run(
            [
                sys.executable,
                str(runner),
                "--workload",
                workload,
                "--root",
                str(root),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise ValueError(completed.stderr.strip() or f"{workload} failed")
        document = json.loads(completed.stdout)
        for name, value in document.items():
            samples.setdefault(name, []).append(float(value))
    return samples


def _document(root: Path, config: dict[str, Any], profile: str) -> dict[str, Any]:
    scenarios: list[dict[str, Any]] = []
    noise_mad_ratio = float(config["methodology"]["noise_mad_ratio"])
    for scenario_id, scenario in sorted(config["scenarios"].items()):
        if scenario["profile"] != profile:
            continue
        workload = scenario["workload"]
        if workload == "path_inventory":
            inventory = _path_inventory(
                root,
                scenario["paths"],
                list(config.get("classifications", {}).get("cache_excluded", [])),
            )
            measured = (
                None
                if inventory is None
                else {name: [float(value)] for name, value in inventory.items()}
            )
        else:
            measured = _run_workload(root, workload, int(scenario["repetitions"]))
        metrics: list[dict[str, Any]]
        if measured is None:
            reason = "required paths do not exist: " + ", ".join(scenario["paths"])
            metrics = [
                {
                    "name": name,
                    "value": None,
                    "samples": [],
                    "relative_mad": None,
                    "unit": policy["unit"],
                    "classification": policy["classification"],
                    "enforcement": policy["enforcement"],
                    "baseline": policy.get("baseline"),
                    "limit": policy.get("limit"),
                    "minimum": policy.get("minimum"),
                    "status": "unavailable",
                    "reason": reason,
                }
                for name, policy in sorted(scenario["metrics"].items())
            ]
        else:
            metrics = [
                _evaluate_metric(
                    name,
                    measured[name],
                    policy,
                    noise_mad_ratio=noise_mad_ratio,
                )
                for name, policy in sorted(scenario["metrics"].items())
            ]
        scenarios.append({"id": scenario_id, "metrics": metrics})
    if not scenarios:
        raise ValueError(f"profile {profile} has no scenarios")
    statuses = ("inconclusive", "ok", "regression", "unavailable", "violation")
    return {
        "schema_version": "1",
        "profile": profile,
        "baseline_environment": config.get("baseline_environment", {}),
        "measurement_environment": measurement_environment(root),
        "methodology": config["methodology"],
        "classifications": config.get("classifications", {}),
        "summary": {
            status: sum(
                metric["status"] == status
                for scenario in scenarios
                for metric in scenario["metrics"]
            )
            for status in statuses
        },
        "scenarios": scenarios,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--profile", choices=("python", "build"), required=True)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--base-ref", default="origin/main")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    config_path = args.config or root / "resource-budget.toml"
    try:
        config = tomllib.loads(config_path.read_text(encoding="utf-8"))
        validate_policy(config)
        document = _document(root, config, args.profile)
        if args.base_ref != "none":
            validate_baseline_changes(root, config_path, config, document, args.base_ref)
    except (OSError, KeyError, TypeError, ValueError, tomllib.TOMLDecodeError) as exc:
        print(f"CONFIG ERROR: {exc}", file=sys.stderr)
        return 2
    rendered_json = json_document(document)
    sys.stdout.write(rendered_json if args.format == "json" else text_document(document))
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(rendered_json, encoding="utf-8")
    if document["summary"]["unavailable"]:
        return 2
    if document["summary"]["violation"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
