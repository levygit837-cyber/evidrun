"""Policy evaluation behind the change-contract interface."""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Any

from .git import AddedLine, ChangeSource, GitChange, GitSnapshot
from .model import ChangeContract, ImpactLevel, QuestionStatus

NORMATIVE_PATTERNS = (
    "AGENTS.md",
    "CONTEXT.md",
    "docs/adr/**",
    "docs/contracts/**",
)
PERSISTED_CONTRACT_PATTERNS = (
    "alembic/**",
    "docs/contracts/**",
    "schemas/**",
    "src/evidrun/contracts/**",
)
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
)
SAFE_SECRET_MARKERS = ("example", "fake", "dummy", "test-only", "redacted")


class Severity(StrEnum):
    BLOCKER = "blocker"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class Diagnostic:
    code: str
    severity: Severity
    message: str
    paths: tuple[str, ...] = ()
    remediation: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity.value,
            "message": self.message,
            "paths": list(self.paths),
            "remediation": self.remediation,
        }


@dataclass(frozen=True)
class CheckReport:
    contract_id: str
    issue: int
    classification: str
    base_ref: str
    merge_base: str
    head: str
    branch: str | None
    delivery_paths: tuple[str, ...]
    excluded_preexisting: tuple[str, ...]
    untracked: tuple[str, ...]
    diagnostics: tuple[Diagnostic, ...]

    @property
    def blockers(self) -> tuple[Diagnostic, ...]:
        return tuple(item for item in self.diagnostics if item.severity is Severity.BLOCKER)

    @property
    def warnings(self) -> tuple[Diagnostic, ...]:
        return tuple(item for item in self.diagnostics if item.severity is Severity.WARNING)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1",
            "contract": {
                "change_id": self.contract_id,
                "issue": self.issue,
                "classification": self.classification,
            },
            "git": {
                "base_ref": self.base_ref,
                "merge_base": self.merge_base,
                "head": self.head,
                "branch": self.branch,
            },
            "delivery_paths": list(self.delivery_paths),
            "excluded_preexisting": list(self.excluded_preexisting),
            "untracked_not_delivery": list(self.untracked),
            "summary": {
                "blockers": len(self.blockers),
                "warnings": len(self.warnings),
                "diagnostics": len(self.diagnostics),
            },
            "diagnostics": [item.as_dict() for item in self.diagnostics],
        }


def check_contract(contract: ChangeContract, snapshot: GitSnapshot) -> CheckReport:
    """Evaluate one plan against its candidate diff and dirty tracked worktree."""

    diagnostics: list[Diagnostic] = []
    excluded: set[str] = set()
    delivery: set[str] = set()
    contract_path = _relative_contract_path(contract, snapshot)
    _check_questions(contract, diagnostics)
    _check_branch(contract, snapshot, diagnostics)
    for change in snapshot.changes:
        affected = change.affected_paths
        _check_protected_change(contract, change, snapshot, diagnostics)
        if any(matches(path, contract.scope.preexisting) for path in affected):
            excluded.update(affected)
            diagnostics.append(
                Diagnostic(
                    code="workspace.preexisting_change",
                    severity=Severity.INFO,
                    message="Alteracao preexistente foi preservada e excluida da entrega.",
                    paths=tuple(sorted(affected)),
                )
            )
            continue
        delivery.update(affected)
        _check_scope_change(contract, change, contract_path, diagnostics)
        if ChangeSource.WORKTREE in change.sources:
            diagnostics.append(
                Diagnostic(
                    code="workspace.uncommitted_change",
                    severity=Severity.INFO,
                    message=(
                        "Arquivo rastreado ainda possui mudanca nao commitada; "
                        "ele foi avaliado."
                    ),
                    paths=tuple(sorted(affected)),
                )
            )
    _check_generated_sources(contract, tuple(sorted(delivery)), diagnostics)
    _check_untracked(snapshot, diagnostics)
    _check_secrets(snapshot.added_lines, diagnostics)
    ordered = tuple(
        sorted(
            _deduplicate(diagnostics),
            key=lambda item: (item.severity.value, item.code, item.paths, item.message),
        )
    )
    return CheckReport(
        contract_id=contract.change_id,
        issue=contract.issue,
        classification=contract.classification.value,
        base_ref=snapshot.base_ref,
        merge_base=snapshot.merge_base,
        head=snapshot.head,
        branch=snapshot.branch,
        delivery_paths=tuple(sorted(delivery)),
        excluded_preexisting=tuple(sorted(excluded)),
        untracked=snapshot.untracked,
        diagnostics=ordered,
    )


def matches(path: str, patterns: tuple[str, ...]) -> bool:
    """Match repository-relative paths with predictable glob semantics."""

    normalized = PurePosixPath(path).as_posix()
    for pattern in patterns:
        if pattern.endswith("/**") and (
            normalized == pattern[:-3] or normalized.startswith(pattern[:-2])
        ):
            return True
        if PurePosixPath(normalized).match(pattern) or fnmatch.fnmatchcase(normalized, pattern):
            return True
    return False


def secret_diagnostics(lines: tuple[AddedLine, ...]) -> tuple[Diagnostic, ...]:
    """Return high-confidence findings without returning matched secret material."""

    diagnostics: list[Diagnostic] = []
    for line in lines:
        lowered = line.content.lower()
        if any(marker in lowered for marker in SAFE_SECRET_MARKERS):
            continue
        if any(pattern.search(line.content) for pattern in SECRET_PATTERNS):
            diagnostics.append(
                Diagnostic(
                    code="security.secret_detected",
                    severity=Severity.BLOCKER,
                    message=f"Possivel segredo de alta confianca em {line.path}:{line.line}.",
                    paths=(line.path,),
                    remediation=(
                        "Remova e rotacione a credencial; nao adicione o valor "
                        "a allowlists."
                    ),
                )
            )
    return tuple(diagnostics)


def _check_questions(contract: ChangeContract, diagnostics: list[Diagnostic]) -> None:
    for question in contract.questions:
        if question.affects_semantics and question.status is QuestionStatus.OPEN:
            diagnostics.append(
                Diagnostic(
                    code="planning.semantic_question_open",
                    severity=Severity.BLOCKER,
                    message=f"Pergunta que altera semantica continua aberta: {question.text}",
                    remediation=(
                        "Resolva a pergunta e registre a decisao antes de marcar "
                        "ready-for-agent."
                    ),
                )
            )


def _check_branch(
    contract: ChangeContract, snapshot: GitSnapshot, diagnostics: list[Diagnostic]
) -> None:
    if contract.branch_pattern is None or snapshot.branch is None:
        return
    if not fnmatch.fnmatchcase(snapshot.branch, contract.branch_pattern):
        diagnostics.append(
            Diagnostic(
                code="identity.branch_mismatch",
                severity=Severity.WARNING,
                message=(
                    f"Branch {snapshot.branch} nao corresponde ao pattern declarado "
                    f"{contract.branch_pattern}."
                ),
                remediation="Confirme a issue/worktree ou emende branch_pattern com justificativa.",
            )
        )


def _check_protected_change(
    contract: ChangeContract,
    change: GitChange,
    snapshot: GitSnapshot,
    diagnostics: list[Diagnostic],
) -> None:
    affected = tuple(sorted(change.affected_paths))
    if any(matches(path, contract.scope.forbidden) for path in affected):
        diagnostics.append(
            Diagnostic(
                code="scope.forbidden_path",
                severity=Severity.BLOCKER,
                message="O diff toca path explicitamente proibido pelo plano.",
                paths=affected,
                remediation="Pare ou emende o contrato antes de editar esse path.",
            )
        )
    if contract.impact.normative is ImpactLevel.NONE and any(
        path in snapshot.normative_documents or matches(path, NORMATIVE_PATTERNS)
        for path in affected
    ):
        diagnostics.append(
            Diagnostic(
                code="impact.normative_undeclared",
                severity=Severity.BLOCKER,
                message="Documento normativo mudou, mas impact.normative=none.",
                paths=affected,
                remediation=(
                    "Declare o impacto e crie ADR sucessor quando uma decisao "
                    "aceita mudar."
                ),
            )
        )
    if contract.impact.persisted_contract is ImpactLevel.NONE and any(
        matches(path, PERSISTED_CONTRACT_PATTERNS) for path in affected
    ):
        diagnostics.append(
            Diagnostic(
                code="impact.persisted_contract_undeclared",
                severity=Severity.BLOCKER,
                message=(
                    "Schema, migration ou contrato mudou sem impacto persistido "
                    "declarado."
                ),
                paths=affected,
                remediation="Declare o impacto, compatibilidade, migration e fixtures anteriores.",
            )
        )


def _check_scope_change(
    contract: ChangeContract,
    change: GitChange,
    contract_path: str,
    diagnostics: list[Diagnostic],
) -> None:
    affected = tuple(sorted(change.affected_paths))
    unplanned = tuple(
        path
        for path in affected
        if path != contract_path and not matches(path, contract.scope.planned_patterns)
    )
    if unplanned:
        diagnostics.append(
            Diagnostic(
                code="scope.unplanned_path",
                severity=Severity.WARNING,
                message=(
                    "Path nao previsto foi descoberto; a capacidade do agente "
                    "nao foi bloqueada."
                ),
                paths=unplanned,
                remediation=(
                    "Adicione uma [[scope.expansions]] com patterns e rationale antes do handoff."
                ),
            )
        )


def _check_generated_sources(
    contract: ChangeContract,
    delivery_paths: tuple[str, ...],
    diagnostics: list[Diagnostic],
) -> None:
    for generated in contract.scope.generated:
        generated_paths = tuple(
            path for path in delivery_paths if matches(path, generated.patterns)
        )
        if generated_paths and not any(
            matches(path, generated.source_patterns) for path in delivery_paths
        ):
            diagnostics.append(
                Diagnostic(
                    code="generated.source_missing",
                    severity=Severity.WARNING,
                    message="Arquivo gerado mudou sem uma fonte declarada no mesmo diff.",
                    paths=generated_paths,
                    remediation="Altere a fonte ou justifique a regeneracao em scope.expansions.",
                )
            )


def _check_untracked(snapshot: GitSnapshot, diagnostics: list[Diagnostic]) -> None:
    if snapshot.untracked:
        diagnostics.append(
            Diagnostic(
                code="workspace.untracked_not_delivery",
                severity=Severity.WARNING,
                message="Arquivos untracked foram observados, mas nao contam como entrega.",
                paths=snapshot.untracked,
                remediation=(
                    "Revise e adicione intencionalmente ao indice apenas o que "
                    "pertence a issue."
                ),
            )
        )


def _check_secrets(lines: tuple[AddedLine, ...], diagnostics: list[Diagnostic]) -> None:
    diagnostics.extend(secret_diagnostics(lines))


def _relative_contract_path(contract: ChangeContract, snapshot: GitSnapshot) -> str:
    try:
        return contract.source.resolve().relative_to(snapshot.root).as_posix()
    except ValueError:
        return contract.source.as_posix()


def _deduplicate(diagnostics: list[Diagnostic]) -> tuple[Diagnostic, ...]:
    unique: dict[tuple[str, Severity, str, tuple[str, ...]], Diagnostic] = {}
    for diagnostic in diagnostics:
        key = (diagnostic.code, diagnostic.severity, diagnostic.message, diagnostic.paths)
        unique[key] = diagnostic
    return tuple(unique.values())
