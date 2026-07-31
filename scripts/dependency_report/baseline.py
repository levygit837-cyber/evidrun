"""New edges of this checkout against a merge-base revision.

The comparison is a set difference over normalized edges, so a new edge appears as
its own line without reformatting the rest of the report. When the merge-base cannot
be resolved — a shallow clone, or a repository with no common ancestor — the drift
section reports itself as not computed instead of guessing an empty diff.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from import_graph import RevisionSource, build_graph

from .vocabulary import ReportError


@dataclass(frozen=True)
class EdgeDrift:
    """Edges present in the checkout and absent from the merge-base."""

    base_ref: str
    merge_base: str | None
    new_edges: tuple[tuple[str, str], ...]
    computed: bool
    reason: str | None = None

    def as_dict(self) -> dict[str, object]:
        document: dict[str, object] = {
            "base_ref": self.base_ref,
            "merge_base": self.merge_base,
            "computed": self.computed,
            "new_edges": [
                {"source": source, "destination": destination}
                for source, destination in self.new_edges
            ],
        }
        if self.reason is not None:
            document["reason"] = self.reason
        return document


def resolve_merge_base(root: Path, base_ref: str) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(root), "merge-base", "HEAD", base_ref],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.decode("utf-8", errors="replace").strip() or None


def edge_drift(
    root: Path,
    base_ref: str,
    current_edges: tuple[tuple[str, str], ...],
) -> EdgeDrift:
    """Diff `current_edges` against the same normalization at the merge-base."""
    merge_base = resolve_merge_base(root, base_ref)
    if merge_base is None:
        return EdgeDrift(
            base_ref=base_ref,
            merge_base=None,
            new_edges=(),
            computed=False,
            reason=f"repository cannot resolve a merge-base with {base_ref}",
        )
    try:
        base_graph = build_graph(root, RevisionSource(root, merge_base))
    except (subprocess.CalledProcessError, OSError, SyntaxError, ValueError) as exc:
        raise ReportError(f"cannot read the graph at {merge_base}: {exc}") from exc
    base_edges = {
        (edge.source_module, edge.destination)
        for edge in base_graph.edges
        if edge.destination in base_graph.internal_destinations()
    }
    return EdgeDrift(
        base_ref=base_ref,
        merge_base=merge_base,
        new_edges=tuple(sorted(set(current_edges) - base_edges)),
        computed=True,
    )
