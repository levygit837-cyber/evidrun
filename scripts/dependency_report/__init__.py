"""Warning-only dependency and cycle report over the import graph."""

from .baseline import EdgeDrift, edge_drift, resolve_merge_base
from .externals import ExternalUsage, external_usage, package_of, unresolved_specifiers
from .findings import Finding
from .graph_metrics import (
    FanMetrics,
    adjacency,
    cycles,
    fan_metrics,
    partition_edges,
    reexport_hubs,
)
from .render import json_document, text_document, write_json
from .report import (
    FAN_IN_CANDIDATE,
    FAN_OUT_CANDIDATE,
    REEXPORT_HUB_CANDIDATE,
    SCHEMA_VERSION,
    DependencyReport,
    SliceCrossing,
    build_report,
)
from .slices import (
    LAYER_RANK,
    SliceIndex,
    crosses_conceptual_direction,
    slice_index,
)
from .vocabulary import DependencyState, FindingCode, FindingKind, ReportError

__all__ = [
    "FAN_IN_CANDIDATE",
    "FAN_OUT_CANDIDATE",
    "LAYER_RANK",
    "REEXPORT_HUB_CANDIDATE",
    "SCHEMA_VERSION",
    "DependencyReport",
    "DependencyState",
    "EdgeDrift",
    "ExternalUsage",
    "FanMetrics",
    "Finding",
    "FindingCode",
    "FindingKind",
    "ReportError",
    "SliceCrossing",
    "SliceIndex",
    "adjacency",
    "build_report",
    "crosses_conceptual_direction",
    "cycles",
    "edge_drift",
    "external_usage",
    "fan_metrics",
    "json_document",
    "package_of",
    "partition_edges",
    "reexport_hubs",
    "resolve_merge_base",
    "slice_index",
    "text_document",
    "unresolved_specifiers",
    "write_json",
]
