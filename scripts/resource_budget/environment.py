"""Describe the environment that produced a resource report."""

from __future__ import annotations

import platform
import subprocess
import sys
from pathlib import Path


def measurement_environment(root: Path) -> dict[str, str]:
    return {
        "git_commit": _command(root, ["git", "rev-parse", "HEAD"]),
        "node": _command(root, ["node", "--version"]),
        "os": f"{platform.system()} {platform.release()} {platform.machine()}",
        "python": platform.python_version(),
        "python_executable": Path(sys.executable).name,
    }


def _command(root: Path, command: list[str]) -> str:
    """The command's output, or `unavailable` when it cannot describe anything.

    `check=False` suppresses a non-zero exit code but not the `FileNotFoundError` a
    missing binary raises, so describing the environment aborted the whole run before
    any JSON existed. A runner without `node` is the same fact as `node` failing:
    unavailable. Found by CI, where `node` lives outside the restricted PATH.
    """

    try:
        completed = subprocess.run(
            command,
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return "unavailable"
    return completed.stdout.strip() if completed.returncode == 0 else "unavailable"
