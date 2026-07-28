"""Bundled resources must resolve the same way frozen and from a checkout.

The failure this pins is silent: `Path(__file__).parents[...]` still returns *a* path
inside a PyInstaller bundle, just one that holds no repository, so the benchmark package
goes missing and `doctor` reports it unavailable instead of erroring.

`sys._MEIPASS` is simulated rather than built here, because freezing takes minutes and
needs the `package` extra. What the simulation covers is the branch, which is the part
that was wrong.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from evidrun.shared import resources


def test_checkout_root_holds_the_benchmark_package() -> None:
    """Running from source, the root is the repository itself."""

    assert (resources.resource_root() / "pyproject.toml").is_file()
    assert (resources.benchmarks_root() / "experiments/crl-ctx-002-demo.yaml").is_file()


def test_checkout_is_not_reported_as_frozen() -> None:
    assert resources.is_frozen() is False


def test_frozen_root_follows_the_extraction_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Frozen, the root is what PyInstaller reports, not where the module sits."""

    monkeypatch.setattr(resources.sys, "frozen", True, raising=False)
    monkeypatch.setattr(resources.sys, "_MEIPASS", str(tmp_path), raising=False)
    assert resources.is_frozen() is True
    assert resources.resource_root() == tmp_path
    assert resources.benchmarks_root() == tmp_path / "benchmarks"


def test_frozen_root_never_falls_back_to_the_module_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The regression guard: a frozen process must not resolve to the checkout."""

    monkeypatch.setattr(resources.sys, "frozen", True, raising=False)
    monkeypatch.setattr(resources.sys, "_MEIPASS", str(tmp_path), raising=False)
    assert resources.resource_root() != Path(resources.__file__).resolve().parents[3]


def test_build_bundles_the_benchmark_package() -> None:
    """`--add-data` must place `benchmarks/` where `benchmarks_root()` looks."""

    from scripts.build_desktop_binaries import REPO_ROOT, bundled_data

    source, destination = bundled_data()
    assert source == REPO_ROOT / "benchmarks"
    assert destination == "benchmarks"
