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
from .graph_metrics import FanMetrics, adjacency, cycles, fan_metrics, reexport_hubs
from .slices import crosses_conceptual_direction, slice_of
from .vocabulary import DependencyState, FindingCode

SCHEMA_VERSION = "1"

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
    slice_crossings: tuple[tuple[str, str, int], ...]
    externals: tuple[ExternalUsage, ...]
    drift: EdgeDrift
    findings: tuple[Finding, ...]

    def suspicious_edges(self) -> tuple[tuple[str, str], ...]:
        """Internal edges no rule forbids that still deserve a reader's attention.

        An edge is suspicious when both endpoints sit in one cycle, or when it runs
        against the documented conceptual direction. Forbidden always wins: the gate's
        verdict is not softened into a hint.
        """
        forbidden = set(self.forbidden_edges)
        in_cycle = {
            member for component in self.module_cycles for member in component
        }
        return tuple(
            sorted(
                (source, destination)
                for source, destination in self.internal_edges
                if (source, destination) not in forbidden
                and (
                    (source in in_cycle and destination in in_cycle)
                    or crosses_conceptual_direction(slice_of(source), slice_of(destination))
                )
            )
        )

    def allowed_edges(self) -> tuple[tuple[str, str], ...]:
        excluded = set(self.forbidden_edges) | set(self.suspicious_edges())
        return tuple(
            edge for edge in self.internal_edges if edge not in excluded
        )

    def state_counts(self) -> Mapping[str, int]:
        """Counts of one partition over internal edges, plus forbidden edges.

        All three are edge counts so they can be compared. `forbidden` may exceed the
        internal total, because a forbidden edge can point at an external package.
        """
        return {
            DependencyState.ALLOWED.value: len(self.allowed_edges()),
            DependencyState.FORBIDDEN.value: len(set(self.forbidden_edges)),
            DependencyState.SUSPICIOUS.value: len(self.suspicious_edges()),
        }


def partition_edges(
    graph: ImportGraph,
) -> tuple[tuple[tuple[str, str], ...], tuple[tuple[str, str], ...], Mapping[str, int]]:
    """Split the graph into internal edges, external edges and re-export counts.

    Internal edges are keyed by module so a cycle names modules, not file paths.
    External edges keep the source path, because the runtime of a dependency is
    decided by the importing file's suffix.

    A re-export is one name a package `__init__` binds from another internal module.
    That measures the forwarded surface, which is the blast radius of the hub: an
    importer of the package can reach every one of those names. Counting resolved
    chains instead would measure how often the hub was traversed, which is traffic,
    not surface.
    """
    internal: set[tuple[str, str]] = set()
    external: set[tuple[str, str]] = set()
    reexport_counts: defaultdict[str, int] = defaultdict(int)
    internal_destinations = graph.internal_destinations()
    for edge in graph.edges:
        if edge.destination in internal_destinations:
            internal.add((edge.source_module, edge.destination))
        else:
            external.add((edge.source_path, edge.destination))
        if (
            edge.source_path.endswith("/__init__.py")
            and edge.bound_name is not None
            and edge.destination in internal_destinations
        ):
            reexport_counts[edge.source_module] += 1
    return tuple(sorted(internal)), tuple(sorted(external)), dict(reexport_counts)


def build_report(
    graph: ImportGraph,
    forbidden_edges: tuple[tuple[str, str], ...],
    drift: EdgeDrift,
) -> DependencyReport:
    internal_edges, external_edges, reexport_counts = partition_edges(graph)

    fan = fan_metrics(internal_edges)
    module_cycles = cycles(adjacency(internal_edges))
    slice_edges = tuple(
        sorted(
            {
                (slice_of(source), slice_of(destination))
                for source, destination in internal_edges
                if slice_of(source) != slice_of(destination)
            }
        )
    )
    slice_cycles = cycles(adjacency(slice_edges))
    crossings = _slice_crossings(internal_edges)
    externals = external_usage(external_edges)
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
    )


def _slice_crossings(
    internal_edges: tuple[tuple[str, str], ...],
) -> tuple[tuple[str, str, int], ...]:
    counts: defaultdict[tuple[str, str], int] = defaultdict(int)
    for source, destination in internal_edges:
        source_slice = slice_of(source)
        destination_slice = slice_of(destination)
        if source_slice == destination_slice:
            continue
        counts[(source_slice, destination_slice)] += 1
    return tuple(
        sorted(
            (source_slice, destination_slice, count)
            for (source_slice, destination_slice), count in counts.items()
        )
    )


def _findings(
    *,
    module_cycles: tuple[tuple[str, ...], ...],
    slice_cycles: tuple[tuple[str, ...], ...],
    fan: FanMetrics,
    hubs: tuple[tuple[str, int], ...],
    crossings: tuple[tuple[str, str, int], ...],
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
    for source_slice, destination_slice, count in crossings:
        if crosses_conceptual_direction(source_slice, destination_slice):
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


