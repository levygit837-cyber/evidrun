"""Required migration evidence for intentionally breaking changes."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .parsing import Table, read_enum, read_patterns, read_table, read_text, read_text_tuple
from .vocabulary import ChangeClassification, ImpactDeclaration, ImpactLevel


class MigrationStrategy(StrEnum):
    EXPAND_CONTRACT = "expand-contract"
    MIGRATION = "migration"


@dataclass(frozen=True)
class BreakingPlan:
    justification: str
    strategy: MigrationStrategy
    versioning: str
    adr_successors: tuple[str, ...]
    previous_artifact_tests: tuple[str, ...]


def parse_breaking_plan(
    value: object,
    *,
    classification: ChangeClassification | None,
    impact: ImpactDeclaration | None,
    focused_tests: tuple[str, ...],
    errors: list[str],
) -> BreakingPlan | None:
    """Parse `[breaking]` and enforce the evidence promised by the classification."""

    if classification is not ChangeClassification.BREAKING:
        if value is not None:
            errors.append("[breaking] so pode ser usado com classification=breaking")
        return None
    table = read_table(value, "breaking", errors)
    if table is None:
        return None
    return _parse_required_plan(table, impact, focused_tests, errors)


def _parse_required_plan(
    table: Table,
    impact: ImpactDeclaration | None,
    focused_tests: tuple[str, ...],
    errors: list[str],
) -> BreakingPlan | None:
    justification = read_text(table, "justification", errors, prefix="breaking.")
    strategy = read_enum(
        table,
        "strategy",
        MigrationStrategy,
        errors,
        prefix="breaking.",
    )
    versioning = read_text(table, "versioning", errors, prefix="breaking.")
    successors = read_patterns(table, "adr_successors", errors, prefix="breaking.")
    previous_tests = read_text_tuple(
        table,
        "previous_artifact_tests",
        errors,
        prefix="breaking.",
        nonempty=True,
    )
    missing_tests = tuple(test for test in previous_tests if test not in focused_tests)
    if missing_tests:
        errors.append(
            "breaking.previous_artifact_tests deve constar em verification.focused: "
            + ", ".join(missing_tests)
        )
    if impact is not None and impact.normative is not ImpactLevel.NONE:
        if not successors:
            errors.append("breaking.adr_successors e obrigatorio para impacto normativo")
        invalid = tuple(path for path in successors if not path.startswith("docs/adr/"))
        if invalid:
            errors.append(
                "breaking.adr_successors deve apontar para docs/adr/: " + ", ".join(invalid)
            )
    if justification is None or strategy is None or versioning is None:
        return None
    return BreakingPlan(justification, strategy, versioning, successors, previous_tests)
