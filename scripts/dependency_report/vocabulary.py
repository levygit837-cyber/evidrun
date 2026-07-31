"""Vocabulary of the warning-only dependency report.

The report never blocks. It classifies each dependency into one of three states and
names structural observations as findings, so a reader can tell a rule violation
apart from a shape that merely deserves attention.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from types import MappingProxyType


class DependencyState(StrEnum):
    """How a single edge stands against the direction gate.

    `FORBIDDEN` is decided by `check_import_directions.evaluate`, never by this
    report: a second opinion on what is forbidden would be a second convention.
    """

    ALLOWED = "allowed"
    FORBIDDEN = "forbidden"
    SUSPICIOUS = "suspicious"


class FindingCode(StrEnum):
    MODULE_CYCLE = "dependency.module_cycle"
    SLICE_CYCLE = "dependency.slice_cycle"
    FAN_IN_HIGH = "dependency.fan_in_high"
    FAN_OUT_HIGH = "dependency.fan_out_high"
    REEXPORT_HUB = "dependency.reexport_hub"
    SLICE_CROSSING = "dependency.slice_crossing"
    UNRESOLVED_SPECIFIER = "dependency.unresolved_specifier"
    NEW_EDGE = "dependency.new_edge"


class FindingKind(StrEnum):
    """Why a finding exists, independent of its severity.

    `STRUCTURE` is a property of this checkout. `DRIFT` is a difference against the
    merge-base and disappears once the branch lands.
    """

    STRUCTURE = "structure"
    DRIFT = "drift"


KIND_BY_CODE: Mapping[FindingCode, FindingKind] = MappingProxyType(
    {
        FindingCode.MODULE_CYCLE: FindingKind.STRUCTURE,
        FindingCode.SLICE_CYCLE: FindingKind.STRUCTURE,
        FindingCode.FAN_IN_HIGH: FindingKind.STRUCTURE,
        FindingCode.FAN_OUT_HIGH: FindingKind.STRUCTURE,
        FindingCode.REEXPORT_HUB: FindingKind.STRUCTURE,
        FindingCode.SLICE_CROSSING: FindingKind.STRUCTURE,
        FindingCode.UNRESOLVED_SPECIFIER: FindingKind.STRUCTURE,
        FindingCode.NEW_EDGE: FindingKind.DRIFT,
    }
)


class ReportError(RuntimeError):
    """Configuration or repository state the report cannot read."""


def validate_finding_tables() -> None:
    declared = set(FindingCode)
    missing = declared - set(KIND_BY_CODE)
    orphaned = set(KIND_BY_CODE) - declared
    if missing or orphaned:
        raise ValueError(
            "KIND_BY_CODE must cover every FindingCode exactly: "
            f"missing={sorted(code.value for code in missing)} "
            f"orphaned={sorted(code.value for code in orphaned)}"
        )


validate_finding_tables()
