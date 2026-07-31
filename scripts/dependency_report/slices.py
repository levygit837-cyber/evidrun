"""Slice identity and the conceptual direction between slices.

Slices are the coarse units `docs/architecture/codebase-layout.md` already names. The
layer order below mirrors its conceptual direction, so a crossing against that order
is reported as suspicious without being a rule violation.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

PYTHON_SLICE_PREFIX = "evidrun."
PYTHON_SOURCE_PREFIX = "src/evidrun/"
EXTERNAL_SLICE = "<external>"

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
# `infrastructure` is deliberately absent: the same diagram draws it as a side branch
# (`\-> infrastructure adapters <-/`), not a step of the flow, so no direction is
# claimed for it here. Its one ordered constraint is the blocking rule
# `PY-INFRASTRUCTURE-RUNS`, which the direction gate already owns.
LAYER_RANK: Mapping[str, int] = MappingProxyType(
    {
        "evidrun.shared": 0,
        "evidrun.contracts": 1,
        "evidrun.authority": 2,
        "evidrun.evaluations": 3,
        "evidrun.evidence": 4,
        "evidrun.runs": 5,
        "evidrun.entrypoints": 6,
    }
)


def slice_of(node: str) -> str:
    """The slice a graph node belongs to, or `<external>` for a package.

    Accepts both node vocabularies of the graph: a dotted Python module and a
    repository-relative source path. External edges are keyed by path so the runtime
    can be told from the suffix, so both must classify to the same slice.
    """
    for prefix, name in TYPESCRIPT_SLICES:
        if node.startswith(prefix):
            return name
    if node.startswith(PYTHON_SOURCE_PREFIX):
        remainder = node[len(PYTHON_SOURCE_PREFIX) :]
        head = remainder.split("/")[0]
        return "evidrun.<root>" if head.endswith(".py") else f"evidrun.{head}"
    if node == "evidrun":
        return "evidrun.<root>"
    if node.startswith(PYTHON_SLICE_PREFIX):
        return f"evidrun.{node.split('.')[1]}"
    return EXTERNAL_SLICE


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
