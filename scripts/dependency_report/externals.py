"""External dependencies grouped by the package or app that imports them.

The report separates the standard library from third-party packages: only the latter
is a supply-chain surface worth watching, and mixing them would bury the signal.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from dataclasses import dataclass

from .slices import SliceIndex

STDLIB_MODULES = frozenset(sys.stdlib_module_names) | {"__future__"}
NODE_BUILTIN_PREFIX = "node:"
ASSET_SUFFIXES = (".css", ".scss", ".svg", ".png", ".json")


@dataclass(frozen=True, order=True)
class ExternalUsage:
    """One external package as used by one slice."""

    slice_name: str
    package: str
    edge_count: int
    runtime: str

    def as_dict(self) -> dict[str, object]:
        return {
            "slice": self.slice_name,
            "package": self.package,
            "runtime": self.runtime,
            "edges": self.edge_count,
        }


def package_of(destination: str) -> str | None:
    """The distributable package a destination names, or None when it is not one.

    Returns None for the standard library of either runtime and for asset imports,
    which are bundler inputs rather than dependencies of the module graph.
    """
    if destination.startswith(NODE_BUILTIN_PREFIX):
        return None
    if destination.endswith(ASSET_SUFFIXES):
        return None
    if destination.startswith("@"):
        parts = destination.split("/")
        return "/".join(parts[:2]) if len(parts) >= 2 else destination
    root = destination.split(".")[0].split("/")[0]
    if not root or root in STDLIB_MODULES:
        return None
    return root


def runtime_of(source_path: str) -> str:
    return "python" if source_path.endswith(".py") else "node"


def external_usage(
    external_edges: tuple[tuple[str, str], ...],
    slices: SliceIndex,
) -> tuple[ExternalUsage, ...]:
    """Group `(source_path, destination)` pairs into per-slice package usage."""
    counts: defaultdict[tuple[str, str, str], int] = defaultdict(int)
    for source_path, destination in external_edges:
        package = package_of(destination)
        if package is None:
            continue
        counts[(slices.slice_of(source_path), package, runtime_of(source_path))] += 1
    return tuple(
        sorted(
            ExternalUsage(
                slice_name=slice_name,
                package=package,
                edge_count=count,
                runtime=runtime,
            )
            for (slice_name, package, runtime), count in counts.items()
        )
    )


def unresolved_specifiers(
    external_edges: tuple[tuple[str, str], ...],
) -> tuple[tuple[str, str], ...]:
    """Relative specifiers that resolved to no versioned node.

    A relative path that stayed relative means the scanner could not name a target:
    either an asset or a file outside the scanned roots. It is reported so the gap is
    visible instead of silently counted as an external package.
    """
    return tuple(
        sorted(
            (source_path, destination)
            for source_path, destination in external_edges
            if destination.startswith(".")
        )
    )

