"""Where read-only packaged resources live, frozen or not.

`Path(__file__).parents[...]` walks to the repository root when running from a
checkout, and to a PyInstaller extraction directory when frozen — silently, and to a
path that holds no repository. PyInstaller sets `sys._MEIPASS` to that directory and
`sys.frozen`, so the two cases are distinguishable rather than guessable.

This is deliberately about read-only material shipped with the app, such as the
benchmark package. Writable state belongs to `Settings.data_dir`, which the desktop
handshake supplies and which is never derived from where the code happens to live.
"""

from __future__ import annotations

import sys
from pathlib import Path


def _extraction_dir() -> str | None:
    """PyInstaller's extraction directory, or `None` when not frozen.

    `sys._MEIPASS` is injected at runtime by the bootloader, so it is absent from the
    typeshed stubs and read dynamically.
    """

    if not getattr(sys, "frozen", False):
        return None
    path = getattr(sys, "_MEIPASS", None)
    return path if isinstance(path, str) else None


def is_frozen() -> bool:
    """Whether this process is a PyInstaller-built executable."""

    return _extraction_dir() is not None


def resource_root() -> Path:
    """Root holding bundled read-only resources.

    Frozen, that is the extraction directory PyInstaller reports. From a checkout, it
    is the repository root, four levels above this file
    (`src/evidrun/shared/resources.py`).
    """

    extraction_dir = _extraction_dir()
    if extraction_dir is not None:
        return Path(extraction_dir)
    return Path(__file__).resolve().parents[3]


def benchmarks_root() -> Path:
    """The bundled benchmark package.

    The build adds `benchmarks/` under this name, so the layout matches a checkout and
    callers do not branch on frozen-ness.
    """

    return resource_root() / "benchmarks"
