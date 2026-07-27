"""The packaged app needs both planes, under the exact names Electron spawns.

These are structural assertions, not a build: freezing takes minutes and needs the
`package` extra. What breaks silently is the mapping — a renamed console script or a
dropped target leaves the installed app unable to execute Runs, which is bug B2 all
over again. That mapping is cheap to pin.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from scripts import build_desktop_binaries as binaries
from scripts.build_desktop_binaries import TARGETS

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_both_planes_are_frozen() -> None:
    """The Control Plane and the durable executor are separate executables."""

    assert set(TARGETS) == {"evidrun-backend", "evidrun-worker"}


def test_targets_match_declared_console_scripts() -> None:
    """Each frozen target points at an entrypoint pyproject actually declares."""

    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    declared = set(pyproject["project"]["scripts"].values())
    assert set(TARGETS.values()) <= declared


def test_each_plane_maps_to_its_own_entrypoint() -> None:
    """The planes must not collapse onto one target.

    Pointing both names at the same entrypoint would still satisfy a subset check
    against the declared scripts, and would produce a packaged app that spawns
    `evidrun-backend serve` against a worker that has no `serve` subcommand.
    """

    assert TARGETS["evidrun-backend"] == "evidrun.entrypoints.cli.app:main"
    assert TARGETS["evidrun-worker"] == "evidrun.entrypoints.worker.app:main"
    assert len(set(TARGETS.values())) == len(TARGETS)


@pytest.mark.parametrize(
    ("platform", "expected"),
    [("win32", "evidrun-worker.exe"), ("darwin", "evidrun-worker"), ("linux", "evidrun-worker")],
)
def test_executable_name_follows_the_platform(
    monkeypatch: pytest.MonkeyPatch, platform: str, expected: str
) -> None:
    """`sidecar-path.ts` appends `.exe` on win32 and nothing elsewhere."""

    monkeypatch.setattr(binaries.sys, "platform", platform)
    assert binaries.executable_name("evidrun-worker") == expected
