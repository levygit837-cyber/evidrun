"""Assembly of the warning-only dependency report.

The report reads the same normalized graph as the direction gate and adds no policy of
its own about what is forbidden: `forbidden_edges` is supplied by the gate. What this
module owns is the *suspicious* class — shapes that no rule forbids but that grow blast
radius, which is exactly the signal issue #51 asks to surface before any threshold
becomes blocking.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass

from import_graph import ImportGraph

from .baseline import EdgeDrift
from .externals import ExternalUsage, external_usage, unresolved_specifiers
from .findings import Finding
from .graph_metrics import (
    FanMetrics,
    adjacency,
    cycles,
    fan_metrics,
    partition_edges,
    reexport_hubs,
)
from .slices import SliceIndex, crosses_conceptual_direction, slice_index
from .vocabulary import DependencyState, FindingCode

SCHEMA_VERSION = "1"

# One crossing between slices: source, destination, edge count, and whether it runs
# against the documented conceptual direction. The verdict is computed once, during
# assembly, and carried here so no consumer re-derives it.
SliceCrossing = tuple[str, str, int, bool]

# Candidate thresholds only. Issue #51 requires the first phase to inform, so these
# gate nothing: they decide which lines are printed, never the exit code. Real values
# are chosen after this baseline is observed for false positives.
FAN_IN_CANDIDATE = 25
FAN_OUT_CANDIDATE = 20
REEXPORT_HUB_CANDIDATE = 15


@dataclass(frozen=True)
class DependencyReport:
    """Everything measured for one checkout, ready to render."""

    scanned_files: int
    edge_count: int
    internal_edges: tuple[tuple[str, str], ...]
    forbidden_edges: tuple[tuple[str, str], ...]
    fan: FanMetrics
    module_cycles: tuple[tuple[str, ...], ...]
    slice_cycles: tuple[tuple[str, ...], ...]
    slice_crossings: tuple[SliceCrossing, ...]
    externals: tuple[ExternalUsage, ...]
    drift: EdgeDrift
    findings: tuple[Finding, ...]
    slices: SliceIndex
    reexport_surface: tuple[tuple[str, int], ...]

    def forbidden_internal_edges(self) -> tuple[tuple[str, str], ...]:
        """Forbidden edges whose destination is a node of this graph.

        Only these can take part in the partition over internal edges. A rule may
        forbid an edge that points at an external package — `PY-CONTRACTS-EXTERNALS`
        names `fastapi`, `TS-RENDERER-NATIVE` names `node:*` — and counting those in
        would make the three states exceed the internal total.
        """
        internal = set(self.internal_edges)
        return tuple(edge for edge in sorted(set(self.forbidden_edges)) if edge in internal)

    def forbidden_external_edges(self) -> tuple[tuple[str, str], ...]:
        """Forbidden edges pointing outside the graph, reported beside the partition."""
        internal = set(self.internal_edges)
        return tuple(
            edge for edge in sorted(set(self.forbidden_edges)) if edge not in internal
        )

    def suspicious_edges(self) -> tuple[tuple[str, str], ...]:
        """Internal edges no rule forbids that still deserve a reader's attention.

        An edge is suspicious when both endpoints sit in one cycle, or when it runs
        against the documented conceptual direction. Forbidden always wins: the gate's
        verdict is not softened into a hint.

        The direction verdict is read from `slice_crossings`, where assembly already
        decided it, rather than re-derived here.
        """
        forbidden = set(self.forbidden_edges)
        in_cycle = {member for component in self.module_cycles for member in component}
        against_direction = {
            (source_slice, destination_slice)
            for source_slice, destination_slice, _, against in self.slice_crossings
            if against
        }
        return tuple(
            sorted(
                (source, destination)
                for source, destination in self.internal_edges
                if (source, destination) not in forbidden
                and (
                    (source in in_cycle and destination in in_cycle)
                    or (self.slices.slice_of(source), self.slices.slice_of(destination))
                    in against_direction
                )
            )
        )

    def allowed_edges(self) -> tuple[tuple[str, str], ...]:
        excluded = set(self.forbidden_edges) | set(self.suspicious_edges())
        return tuple(
            edge for edge in self.internal_edges if edge not in excluded
        )

    def state_counts(self) -> Mapping[str, int]:
        """One partition over the internal edges: the three counts sum to their total.

        Forbidden edges that leave the graph are excluded here and reported by
        `forbidden_external_edges`, so the partition stays an identity a reader can
        check by adding three numbers.
        """
        return {
            DependencyState.ALLOWED.value: len(self.allowed_edges()),
            DependencyState.FORBIDDEN.value: len(self.forbidden_internal_edges()),
            DependencyState.SUSPICIOUS.value: len(self.suspicious_edges()),
        }



def build_report(
    graph: ImportGraph,
    forbidden_edges: tuple[tuple[str, str], ...],
    drift: EdgeDrift,
) -> DependencyReport:
    internal_edges, external_edges, reexport_counts = partition_edges(graph)
    slices = slice_index(graph.python_modules)

    fan = fan_metrics(internal_edges)
    module_cycles = cycles(adjacency(internal_edges))
    crossings = _slice_crossings(internal_edges, slices)
    slice_edges = tuple(
        sorted({(source, destination) for source, destination, _, _ in crossings})
    )
    slice_cycles = cycles(adjacency(slice_edges))
    externals = external_usage(external_edges, slices)
    hubs = reexport_hubs(reexport_counts, REEXPORT_HUB_CANDIDATE)
    findings = _findings(
        module_cycles=module_cycles,
        slice_cycles=slice_cycles,
        fan=fan,
        hubs=hubs,
        crossings=crossings,
        unresolved=unresolved_specifiers(external_edges),
        drift=drift,
    )
    return DependencyReport(
        scanned_files=len(graph.paths),
        edge_count=len(graph.edges),
        internal_edges=internal_edges,
        forbidden_edges=tuple(sorted(set(forbidden_edges))),
        fan=fan,
        module_cycles=module_cycles,
        slice_cycles=slice_cycles,
        slice_crossings=crossings,
        externals=externals,
        drift=drift,
        findings=findings,
        slices=slices,
        reexport_surface=tuple(sorted(reexport_counts.items())),
    )


def _slice_crossings(
    internal_edges: tuple[tuple[str, str], ...],
    slices: SliceIndex,
) -> tuple[SliceCrossing, ...]:
    """Edges between slices, each carrying the direction verdict already decided.

    The verdict travels with the row so no consumer re-derives it: the renderer only
    renders, and `suspicious_edges` reads one boolean instead of calling the predicate
    a second time.
    """
    counts: defaultdict[tuple[str, str], int] = defaultdict(int)
    for source, destination in internal_edges:
        source_slice = slices.slice_of(source)
        destination_slice = slices.slice_of(destination)
        if source_slice == destination_slice:
            continue
        counts[(source_slice, destination_slice)] += 1
    return tuple(
        sorted(
            (
                source_slice,
                destination_slice,
                count,
                crosses_conceptual_direction(source_slice, destination_slice),
            )
            for (source_slice, destination_slice), count in counts.items()
        )
    )


def _findings(
    *,
    module_cycles: tuple[tuple[str, ...], ...],
    slice_cycles: tuple[tuple[str, ...], ...],
    fan: FanMetrics,
    hubs: tuple[tuple[str, int], ...],
    crossings: tuple[SliceCrossing, ...],
    unresolved: tuple[tuple[str, str], ...],
    drift: EdgeDrift,
) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    for component in module_cycles:
        findings.append(
            Finding(
                code=FindingCode.MODULE_CYCLE,
                subjects=component,
                detail=f"{len(component)} modules import each other transitively",
                metrics=(("members", len(component)),),
            )
        )
    for component in slice_cycles:
        findings.append(
            Finding(
                code=FindingCode.SLICE_CYCLE,
                subjects=component,
                detail=f"{len(component)} slices depend on each other transitively",
                metrics=(("members", len(component)),),
            )
        )
    for node in fan.nodes():
        inbound = fan.fan_in.get(node, 0)
        if inbound >= FAN_IN_CANDIDATE:
            findings.append(
                Finding(
                    code=FindingCode.FAN_IN_HIGH,
                    subjects=(node,),
                    detail=f"{inbound} distinct modules depend on this node",
                    metrics=(("fan_in", inbound), ("candidate", FAN_IN_CANDIDATE)),
                )
            )
        outbound = fan.fan_out.get(node, 0)
        if outbound >= FAN_OUT_CANDIDATE:
            findings.append(
                Finding(
                    code=FindingCode.FAN_OUT_HIGH,
                    subjects=(node,),
                    detail=f"this node depends on {outbound} distinct modules",
                    metrics=(("fan_out", outbound), ("candidate", FAN_OUT_CANDIDATE)),
                )
            )
    for module, count in hubs:
        findings.append(
            Finding(
                code=FindingCode.REEXPORT_HUB,
                subjects=(module,),
                detail=f"package init re-exports {count} symbols from other modules",
                metrics=(("reexports", count), ("candidate", REEXPORT_HUB_CANDIDATE)),
            )
        )
    for source_slice, destination_slice, count, against_direction in crossings:
        if against_direction:
            findings.append(
                Finding(
                    code=FindingCode.SLICE_CROSSING,
                    subjects=(source_slice, destination_slice),
                    detail="edge runs against the documented conceptual direction",
                    metrics=(("edges", count),),
                )
            )
    for source_path, destination in unresolved:
        findings.append(
            Finding(
                code=FindingCode.UNRESOLVED_SPECIFIER,
                subjects=(source_path, destination),
                detail="relative specifier resolved to no versioned source node",
            )
        )
    for source, destination in drift.new_edges:
        findings.append(
            Finding(
                code=FindingCode.NEW_EDGE,
                subjects=(source, destination),
                detail=f"edge is absent from {drift.base_ref}",
            )
        )
    return tuple(sorted(findings))


