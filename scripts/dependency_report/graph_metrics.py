"""Cycles, fan-in/fan-out, re-export surface and the internal/external split.

Every function here is pure over its input and returns sorted tuples, because the
report must be byte-identical for the same checkout.

`partition_edges` lives here rather than in `report.py` because both the checkout and
the merge-base side of the drift diff need it: importing it from `report` would make
`baseline` depend on `report`, which already imports `EdgeDrift` from `baseline`.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass

from import_graph import ImportGraph

InternalEdges = tuple[tuple[str, str], ...]
Adjacency = Mapping[str, frozenset[str]]


def partition_edges(
    graph: ImportGraph,
) -> tuple[InternalEdges, InternalEdges, Mapping[str, int]]:
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


@dataclass(frozen=True)
class FanMetrics:
    """How many distinct nodes depend on a node, and how many it depends on."""

    fan_in: Mapping[str, int]
    fan_out: Mapping[str, int]

    def nodes(self) -> tuple[str, ...]:
        return tuple(sorted(set(self.fan_in) | set(self.fan_out)))


def adjacency(edges: InternalEdges) -> Adjacency:
    """Deduplicated successor sets, with self-loops dropped.

    A module importing itself is a path artifact of re-export resolution, not a cycle
    a reader can act on.
    """
    successors: defaultdict[str, set[str]] = defaultdict(set)
    for source, destination in edges:
        if source != destination:
            successors[source].add(destination)
    return {node: frozenset(targets) for node, targets in successors.items()}


def fan_metrics(edges: InternalEdges) -> FanMetrics:
    fan_in: defaultdict[str, set[str]] = defaultdict(set)
    fan_out: defaultdict[str, set[str]] = defaultdict(set)
    for source, destination in edges:
        if source == destination:
            continue
        fan_out[source].add(destination)
        fan_in[destination].add(source)
    return FanMetrics(
        fan_in={node: len(sources) for node, sources in fan_in.items()},
        fan_out={node: len(targets) for node, targets in fan_out.items()},
    )


def cycles(adjacent: Adjacency) -> tuple[tuple[str, ...], ...]:
    """Strongly connected components larger than one node, sorted.

    Tarjan's algorithm run on an explicit stack: the graph is small today, but a
    recursive walk would make the report's failure mode depend on import depth.
    """
    index: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    on_stack: set[str] = set()
    component_stack: list[str] = []
    found: list[tuple[str, ...]] = []
    counter = 0

    reachable = {node for targets in adjacent.values() for node in targets}
    for start in sorted(set(adjacent) | reachable):
        if start in index:
            continue
        index[start] = lowlink[start] = counter
        counter += 1
        component_stack.append(start)
        on_stack.add(start)
        work: list[tuple[str, list[str], int]] = [(start, sorted(adjacent.get(start, ())), 0)]
        while work:
            node, successors, cursor = work[-1]
            if cursor < len(successors):
                work[-1] = (node, successors, cursor + 1)
                successor = successors[cursor]
                if successor not in index:
                    index[successor] = lowlink[successor] = counter
                    counter += 1
                    component_stack.append(successor)
                    on_stack.add(successor)
                    work.append((successor, sorted(adjacent.get(successor, ())), 0))
                elif successor in on_stack:
                    lowlink[node] = min(lowlink[node], index[successor])
                continue
            work.pop()
            if work:
                parent = work[-1][0]
                lowlink[parent] = min(lowlink[parent], lowlink[node])
            if lowlink[node] == index[node]:
                component: list[str] = []
                while True:
                    member = component_stack.pop()
                    on_stack.discard(member)
                    component.append(member)
                    if member == node:
                        break
                if len(component) > 1:
                    found.append(tuple(sorted(component)))
    return tuple(sorted(found))


def reexport_hubs(
    reexport_counts: Mapping[str, int], minimum: int
) -> tuple[tuple[str, int], ...]:
    """Modules re-exporting at least `minimum` symbols, sorted by name.

    Sorting by name rather than by count is deliberate: a count change must not move
    unrelated lines of the report.
    """
    return tuple(
        (module, count)
        for module, count in sorted(reexport_counts.items())
        if count >= minimum
    )
