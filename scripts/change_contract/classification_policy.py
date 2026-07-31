"""Consistency rules between declared change class and detected contract diffs."""

from __future__ import annotations

import fnmatch
from pathlib import PurePosixPath

from .diagnostics import Diagnostic, Severity
from .model import ChangeContract
from .schema_diff import Compatibility, ContractDiffReport, ContractSurface
from .vocabulary import ChangeClassification, ImpactLevel

_BREAKING_IMPACTS = {ImpactLevel.REMOVED, ImpactLevel.BREAKING}
_PERSISTED_SURFACES = {
    ContractSurface.JSON_SCHEMA,
    ContractSurface.PERSISTED_MODEL,
    ContractSurface.EVENT,
}
_CAPABILITY_SURFACES = {
    ContractSurface.OPENAPI,
    ContractSurface.CLI,
    ContractSurface.EXPORT,
}


def classification_diagnostics(
    contract: ChangeContract,
    reports: tuple[ContractDiffReport, ...],
    delivery_paths: tuple[str, ...],
    contract_path: str,
) -> tuple[Diagnostic, ...]:
    """Explain detected changes and fail closed on contradictory declarations."""

    diagnostics = [
        Diagnostic(
            code="compatibility.change_detected",
            severity=Severity.INFO,
            message=(
                f"{report.surface.value}:{change.kind} em {change.pointer} "
                f"({change.compatibility.value}): {change.message}"
            ),
            paths=(report.path,),
        )
        for report in reports
        for change in report.changes
    ]
    changes = tuple(change for report in reports for change in report.changes)
    breaking_reports = tuple(
        report
        for report in reports
        if any(change.compatibility is Compatibility.BREAKING for change in report.changes)
    )
    if contract.classification is ChangeClassification.REFACTOR and changes:
        diagnostics.append(
            _blocker(
                "classification.refactor_semantic_diff",
                "Refactor declarou equivalencia, mas o diff possui mudanca contratual.",
                reports,
                "Reclassifique a mudanca ou restaure a superficie preservada pelo oraculo.",
            )
        )
    elif contract.classification is not ChangeClassification.BREAKING and breaking_reports:
        diagnostics.append(
            _blocker(
                "classification.breaking_mismatch",
                "O diff detectado e breaking, mas a classificacao declarada nao e breaking.",
                breaking_reports,
                "Use classification=breaking e registre [breaking] com migracao e compatibilidade.",
            )
        )
    diagnostics.extend(_class_requirements(contract, delivery_paths, contract_path))
    diagnostics.extend(_impact_requirements(contract, breaking_reports))
    return tuple(diagnostics)


def _class_requirements(
    contract: ChangeContract,
    delivery_paths: tuple[str, ...],
    contract_path: str,
) -> tuple[Diagnostic, ...]:
    diagnostics: list[Diagnostic] = []
    impacts = (
        contract.impact.capability,
        contract.impact.persisted_contract,
        contract.impact.normative,
    )
    if contract.classification is ChangeClassification.BEHAVIOR_COMPATIBLE and any(
        impact in _BREAKING_IMPACTS for impact in impacts
    ):
        diagnostics.append(
            Diagnostic(
                code="classification.behavior_impact_mismatch",
                severity=Severity.BLOCKER,
                message="behavior-compatible nao pode declarar impacto removed ou breaking.",
                remediation="Use classification=breaking ou reduza o impacto real.",
            )
        )
    if contract.classification is ChangeClassification.FEATURE and any(
        impact in _BREAKING_IMPACTS for impact in impacts
    ):
        diagnostics.append(
            Diagnostic(
                code="classification.feature_impact_mismatch",
                severity=Severity.BLOCKER,
                message="feature nao pode declarar remocao ou quebra de contrato/capability.",
                remediation="Use classification=breaking e registre o plano obrigatorio.",
            )
        )
    if contract.classification is ChangeClassification.DOCS_ONLY:
        unexpected = tuple(
            path
            for path in delivery_paths
            if not (
                path.startswith("docs/")
                or path == contract_path
                or path.endswith(".md")
            )
        )
        if unexpected:
            diagnostics.append(
                Diagnostic(
                    code="classification.docs_only_code",
                    severity=Severity.BLOCKER,
                    message="docs-only incluiu arquivos que nao sao documentacao.",
                    paths=unexpected,
                    remediation="Reclassifique a entrega ou remova codigo e artefatos executaveis.",
                )
            )
    if contract.classification is ChangeClassification.GENERATED:
        generated = tuple(pattern for item in contract.scope.generated for pattern in item.patterns)
        unexpected = tuple(
            path
            for path in delivery_paths
            if not path.startswith("changes/") and not _matches(path, generated)
        )
        if not generated or unexpected:
            diagnostics.append(
                Diagnostic(
                    code="classification.generated_scope",
                    severity=Severity.BLOCKER,
                    message=(
                        "generated exige entrega limitada aos patterns declarados como gerados."
                    ),
                    paths=unexpected,
                    remediation="Declare scope.generated ou reclassifique a mudanca da fonte.",
                )
            )
    return tuple(diagnostics)


def _impact_requirements(
    contract: ChangeContract,
    breaking_reports: tuple[ContractDiffReport, ...],
) -> tuple[Diagnostic, ...]:
    persisted = tuple(
        report for report in breaking_reports if report.surface in _PERSISTED_SURFACES
    )
    capability = tuple(
        report for report in breaking_reports if report.surface in _CAPABILITY_SURFACES
    )
    diagnostics: list[Diagnostic] = []
    if persisted and contract.impact.persisted_contract not in _BREAKING_IMPACTS:
        diagnostics.append(
            _blocker(
                "impact.persisted_breaking_mismatch",
                "Superficie persistida quebrou sem persisted_contract=removed|breaking.",
                persisted,
                "Declare impacto breaking e forneca estrategia e fixtures anteriores.",
            )
        )
    if capability and contract.impact.capability not in _BREAKING_IMPACTS:
        diagnostics.append(
            _blocker(
                "impact.capability_breaking_mismatch",
                "API, CLI ou export publico quebrou sem capability=removed|breaking.",
                capability,
                "Declare o impacto breaking e registre versionamento e migracao.",
            )
        )
    return tuple(diagnostics)


def _blocker(
    code: str,
    message: str,
    reports: tuple[ContractDiffReport, ...],
    remediation: str,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=Severity.BLOCKER,
        message=message,
        paths=tuple(sorted({report.path for report in reports})),
        remediation=remediation,
    )


def _matches(path: str, patterns: tuple[str, ...]) -> bool:
    normalized = PurePosixPath(path).as_posix()
    return any(
        PurePosixPath(normalized).match(pattern) or fnmatch.fnmatchcase(normalized, pattern)
        for pattern in patterns
    )
