"""Human and JSON renderings of a measured report.

Both renderings are pure functions of `DependencyReport`, and every collection they
walk is already sorted upstream. That is what makes the same checkout produce a
byte-identical document.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .report import (
    FAN_IN_CANDIDATE,
    FAN_OUT_CANDIDATE,
    REEXPORT_HUB_CANDIDATE,
    SCHEMA_VERSION,
    DependencyReport,
)
from .vocabulary import DependencyState


def json_document(report: DependencyReport) -> str:
    document: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "blocking": False,
        "scanned_files": report.scanned_files,
        "edge_count": report.edge_count,
        "internal_edge_count": len(report.internal_edges),
        "dependency_states": dict(report.state_counts()),
        "candidate_thresholds": {
            "fan_in": FAN_IN_CANDIDATE,
            "fan_out": FAN_OUT_CANDIDATE,
            "reexport_hub": REEXPORT_HUB_CANDIDATE,
        },
        "cycles": {
            "modules": [list(component) for component in report.module_cycles],
            "slices": [list(component) for component in report.slice_cycles],
        },
        "fan": [
            {
                "node": node,
                "fan_in": report.fan.fan_in.get(node, 0),
                "fan_out": report.fan.fan_out.get(node, 0),
            }
            for node in report.fan.nodes()
        ],
        "reexport_surface": [
            {"module": module, "reexports": count}
            for module, count in report.reexport_surface
        ],
        "slice_crossings": [
            {
                "source": source_slice,
                "destination": destination_slice,
                "edges": count,
                "against_conceptual_direction": against_direction,
            }
            for source_slice, destination_slice, count, against_direction in (
                report.slice_crossings
            )
        ],
        "external_dependencies": [usage.as_dict() for usage in report.externals],
        "forbidden_edges": [
            {"source": source, "destination": destination}
            for source, destination in report.forbidden_internal_edges()
        ],
        "forbidden_external_edges": [
            {"source": source, "destination": destination}
            for source, destination in report.forbidden_external_edges()
        ],
        "drift": report.drift.as_dict(),
        "findings": [finding.as_dict() for finding in report.findings],
    }
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"


def text_document(report: DependencyReport) -> str:
    states = report.state_counts()
    lines = [
        "Dependency report (warning-only: no finding blocks a merge)",
        (
            f"  files={report.scanned_files} edges={report.edge_count} "
            f"internal={len(report.internal_edges)}"
        ),
        (
            f"  edges by state: allowed={states[DependencyState.ALLOWED.value]} "
            f"forbidden={states[DependencyState.FORBIDDEN.value]} "
            f"suspicious={states[DependencyState.SUSPICIOUS.value]}"
        ),
        "",
    ]
    lines.extend(_findings_section(report))
    lines.extend(_fan_section(report))
    lines.extend(_reexport_section(report))
    lines.extend(_crossings_section(report))
    lines.extend(_externals_section(report))
    lines.extend(_drift_section(report))
    return "\n".join(lines) + "\n"


def _findings_section(report: DependencyReport) -> list[str]:
    if not report.findings:
        return ["No structural findings.", ""]
    lines = [f"Findings ({len(report.findings)}):"]
    for finding in report.findings:
        subjects = " -> ".join(finding.subjects)
        lines.append(f"  {finding.kind.value.upper()} {finding.code.value}: {subjects}")
        lines.append(f"    {finding.detail}")
    lines.append("")
    return lines


def _fan_section(report: DependencyReport) -> list[str]:
    """Every measured node, not only the ones over a candidate threshold.

    The spec asks for fan-in/fan-out per module in the human report; printing only
    threshold crossings would hide the distribution the thresholds are meant to be
    chosen from.
    """
    nodes = report.fan.nodes()
    if not nodes:
        return []
    lines = [f"Fan-in/fan-out by module ({len(nodes)}):"]
    for node in nodes:
        inbound = report.fan.fan_in.get(node, 0)
        outbound = report.fan.fan_out.get(node, 0)
        lines.append(f"  {node} fan_in={inbound} fan_out={outbound}")
    lines.append("")
    return lines


def _reexport_section(report: DependencyReport) -> list[str]:
    if not report.reexport_surface:
        return []
    lines = [f"Re-export surface by package ({len(report.reexport_surface)}):"]
    for module, count in report.reexport_surface:
        lines.append(f"  {module} reexports={count}")
    lines.append("")
    return lines


def _crossings_section(report: DependencyReport) -> list[str]:
    if not report.slice_crossings:
        return []
    lines = [f"Imports between slices ({len(report.slice_crossings)}):"]
    for source, destination, count, against in report.slice_crossings:
        marker = " AGAINST-DIRECTION" if against else ""
        lines.append(f"  {source} -> {destination} edges={count}{marker}")
    lines.append("")
    return lines



def _externals_section(report: DependencyReport) -> list[str]:
    if not report.externals:
        return []
    lines = [f"External dependencies by slice ({len(report.externals)}):"]
    for usage in report.externals:
        lines.append(
            f"  {usage.slice_name} -> {usage.package} "
            f"[{usage.runtime}] edges={usage.edge_count}"
        )
    lines.append("")
    return lines


def _drift_section(report: DependencyReport) -> list[str]:
    drift = report.drift
    if not drift.computed:
        return [f"New edges vs {drift.base_ref}: not computed ({drift.reason})", ""]
    if not drift.new_edges:
        return [f"New edges vs {drift.base_ref} ({drift.merge_base}): none", ""]
    lines = [f"New edges vs {drift.base_ref} ({drift.merge_base}):"]
    for source, destination in drift.new_edges:
        lines.append(f"  + {source} -> {destination}")
    lines.append("")
    return lines


def write_json(path: Path, report: DependencyReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json_document(report), encoding="utf-8")
