"""Slice identity and the conceptual direction between slices.

Slices are the coarse units `docs/architecture/codebase-layout.md` already names.

Classifying a node needs to know which dotted names are packages: `evidrun.settings`
and `evidrun.contracts` are indistinguishable as strings, yet the first is a module
directly under `src/evidrun/` and the second is a slice of its own. Only the graph
knows which is which, so `SliceIndex` carries that knowledge and `slice_of` is a
method on it rather than a free function over a bare `str`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

PYTHON_SLICE_PREFIX = "evidrun."
PYTHON_SOURCE_PREFIX = "src/evidrun/"
EXTERNAL_SLICE = "<external>"
ROOT_SLICE = "evidrun.<root>"

TYPESCRIPT_SLICES: tuple[tuple[str, str], ...] = (
    ("apps/desktop/src/main/", "desktop/main"),
    ("apps/desktop/src/preload/", "desktop/preload"),
    ("apps/desktop/src/shared/", "desktop/shared"),
    ("apps/desktop/src/", "desktop/other"),
    ("apps/web/src/", "web/renderer"),
)

# Rank of the documented linear flow in `docs/architecture/codebase-layout.md`:
# `entrypoints -> authoring -> compilation -> admission -> run coordination -> evidence`.
# A lower rank may be imported by a higher one. `shared` is rank 0 because nothing
# inside `evidrun` may sit below it.
#
# Only slices that appear in that flow get a rank. Every other slice — `authority`,
# `evaluations`, `security`, `providers`, `experiments`, `contexts`,
# `subject_runners`, `infrastructure` and `evidrun.<root>` — is absent on purpose: the
# diagram claims no order for them, and inventing one would make the report assert a
# direction no document supports. `infrastructure` is drawn there as a side branch
# (`\-> infrastructure adapters <-/`), not a step, and its one ordered constraint is
# the blocking rule `PY-INFRASTRUCTURE-RUNS`, which the direction gate already owns.
#
# Consequence a reader must know: an edge touching an unranked slice is never
# `suspicious` by direction. `allowed` there means "no documented direction to break",
# not "reviewed and approved".
LAYER_RANK: Mapping[str, int] = MappingProxyType(
    {
        "evidrun.shared": 0,
        "evidrun.contracts": 1,
        "evidrun.evidence": 2,
        "evidrun.runs": 3,
        "evidrun.entrypoints": 4,
    }
)


@dataclass(frozen=True)
class SliceIndex:
    """Slice classification for one graph, aware of which dotted names are packages."""

    packages: frozenset[str]

    def slice_of(self, node: str) -> str:
        """The slice a graph node belongs to, or `<external>` for a package.

        Accepts both node vocabularies of the graph: a dotted Python module and a
        repository-relative source path. External edges are keyed by path so the
        runtime can be told from the suffix, so both must classify to the same slice.
        """
        for prefix, name in TYPESCRIPT_SLICES:
            if node.startswith(prefix):
                return name
        if node.startswith(PYTHON_SOURCE_PREFIX):
            head, separator, _ = node[len(PYTHON_SOURCE_PREFIX) :].partition("/")
            return f"{PYTHON_SLICE_PREFIX}{head}" if separator else ROOT_SLICE
        if node == "evidrun":
            return ROOT_SLICE
        if node.startswith(PYTHON_SLICE_PREFIX):
            head = node[len(PYTHON_SLICE_PREFIX) :].partition(".")[0]
            candidate = f"{PYTHON_SLICE_PREFIX}{head}"
            return candidate if candidate in self.packages else ROOT_SLICE
        return EXTERNAL_SLICE


def slice_index(python_modules: frozenset[str]) -> SliceIndex:
    """Derive the package names of `evidrun` from the graph's module set.

    A dotted name is a package when some other module sits beneath it. That is what
    separates `evidrun.contracts`, a slice, from `evidrun.settings`, a module of the
    root slice.
    """
    packages = {
        f"{PYTHON_SLICE_PREFIX}{module[len(PYTHON_SLICE_PREFIX) :].partition('.')[0]}"
        for module in python_modules
        if module.startswith(PYTHON_SLICE_PREFIX) and "." in module[len(PYTHON_SLICE_PREFIX) :]
    }
    return SliceIndex(packages=frozenset(packages))


def crosses_conceptual_direction(source_slice: str, destination_slice: str) -> bool:
    """True when the edge runs against the documented layer order.

    Slices outside `LAYER_RANK` have no documented rank, so no direction is claimed
    for them and the answer is False rather than a guess.
    """
    source_rank = LAYER_RANK.get(source_slice)
    destination_rank = LAYER_RANK.get(destination_slice)
    if source_rank is None or destination_rank is None:
        return False
    return destination_rank > source_rank
