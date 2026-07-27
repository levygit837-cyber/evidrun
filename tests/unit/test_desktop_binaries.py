"""The packaged app needs both planes, under the exact names Electron spawns.

These are structural assertions, not a build: freezing takes minutes and needs the
`package` extra. What breaks silently is the mapping — a renamed console script or a
dropped target leaves the installed app unable to execute Runs, which is bug B2 all
over again. That mapping is cheap to pin.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from scripts.build_desktop_binaries import TARGETS, executable_name

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_both_planes_are_frozen() -> None:
    """The Control Plane and the durable executor are separate executables."""

    assert set(TARGETS) == {"evidrun-backend", "evidrun-worker"}


def test_targets_match_declared_console_scripts() -> None:
    """Each frozen target points at an entrypoint pyproject actually declares."""

    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    declared = set(pyproject["project"]["scripts"].values())
    assert set(TARGETS.values()) <= declared


def test_worker_target_is_the_durable_executor() -> None:
    """ADR 0014 keeps the executor separate from API and CLI; so does packaging."""

    assert TARGETS["evidrun-worker"] == "evidrun.entrypoints.worker.app:main"


def test_executable_name_matches_the_electron_lookup() -> None:
    """`backend-lifecycle.ts` appends `.exe` on win32 and nothing elsewhere."""

    assert executable_name("evidrun-worker") in {
        "evidrun-worker",
        "evidrun-worker.exe",
    }
