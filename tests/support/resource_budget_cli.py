"""Test helpers for exercising the resource-budget CLI as a real process."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "scripts" / "check_resource_budgets.py"


def write_config(root: Path, body: str) -> Path:
    config = root / "resource-budget.toml"
    config.write_text(body.strip() + "\n", encoding="utf-8")
    return config


def run_checker(
    root: Path,
    config: Path,
    profile: str,
    *,
    base_ref: str = "none",
    output_format: str | None = "json",
    json_out: Path | None = None,
    timeout: int | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(CHECKER),
        "--root",
        str(root),
        "--config",
        str(config),
        "--profile",
        profile,
        "--base-ref",
        base_ref,
    ]
    if output_format is not None:
        command.extend(("--format", output_format))
    if json_out is not None:
        command.extend(("--json-out", str(json_out)))
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def commit_baseline(root: Path, config: Path, body: str) -> None:
    config.write_text(body, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", config.name], cwd=root, check=True)
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
        cwd=root,
        check=True,
    )
