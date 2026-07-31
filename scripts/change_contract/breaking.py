"""Required migration evidence for intentionally breaking changes."""

from __future__ import annotations

import shlex
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath

from .diagnostics import Diagnostic, Severity
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


def evidence_diagnostics(
    plan: BreakingPlan | None,
    root: Path,
) -> tuple[Diagnostic, ...]:
    """Require breaking evidence to resolve to files in the candidate tree."""

    if plan is None:
        return ()
    diagnostics: list[Diagnostic] = []
    missing_adrs = tuple(
        path
        for path in plan.adr_successors
        if ".." in PurePosixPath(path).parts or not (root / path).is_file()
    )
    if missing_adrs:
        diagnostics.append(
            Diagnostic(
                code="breaking.adr_successor_missing",
                severity=Severity.BLOCKER,
                message="ADR sucessor declarado nao existe no candidate.",
                paths=missing_adrs,
                remediation="Adicione o ADR sucessor referido pelo plano breaking.",
            )
        )
    if any(
        not _command_has_existing_test_target(command, root)
        for command in plan.previous_artifact_tests
    ):
        diagnostics.append(
            Diagnostic(
                code="breaking.previous_artifact_test_missing",
                severity=Severity.BLOCKER,
                message="Teste de artefato anterior nao aponta para target existente em tests/.",
                remediation=(
                    "Inclua no comando um path explicito e existente sob tests/ "
                    "e mantenha-o em verification.focused."
                ),
            )
        )
    return tuple(diagnostics)


def _command_has_existing_test_target(command: str, root: Path) -> bool:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return False
    for token in tokens:
        target = token.split("::", maxsplit=1)[0].removeprefix("./")
        pure = PurePosixPath(target)
        if (
            pure.parts
            and pure.parts[0] == "tests"
            and ".." not in pure.parts
            and (root / pure).exists()
        ):
            return True
    return False


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
