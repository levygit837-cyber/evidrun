"""Typed, framework-free model for a planned repository change."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import cast

type Table = dict[str, object]


class ContractError(ValueError):
    """The contract cannot be evaluated safely."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = tuple(errors)
        super().__init__("; ".join(errors))


class ChangeClassification(StrEnum):
    REFACTOR = "refactor"
    BEHAVIOR_COMPATIBLE = "behavior-compatible"
    FEATURE = "feature"
    BREAKING = "breaking"
    DOCS_ONLY = "docs-only"
    GENERATED = "generated"


class ImpactLevel(StrEnum):
    NONE = "none"
    ADDITIVE = "additive"
    CHANGED = "changed"
    REMOVED = "removed"
    BREAKING = "breaking"


class QuestionStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"


REFACTOR_PRESERVES = {"capability", "persisted-contract", "fail-closed"}


@dataclass(frozen=True)
class ImpactDeclaration:
    capability: ImpactLevel
    persisted_contract: ImpactLevel
    normative: ImpactLevel
    notes: tuple[str, ...]


@dataclass(frozen=True)
class Question:
    text: str
    affects_semantics: bool
    status: QuestionStatus
    resolution: str | None


@dataclass(frozen=True)
class Expansion:
    patterns: tuple[str, ...]
    rationale: str


@dataclass(frozen=True)
class GeneratedPath:
    patterns: tuple[str, ...]
    source_patterns: tuple[str, ...]


@dataclass(frozen=True)
class Scope:
    expected: tuple[str, ...]
    forbidden: tuple[str, ...]
    preexisting: tuple[str, ...]
    expansions: tuple[Expansion, ...]
    generated: tuple[GeneratedPath, ...]

    @property
    def planned_patterns(self) -> tuple[str, ...]:
        expanded = tuple(pattern for item in self.expansions for pattern in item.patterns)
        generated = tuple(pattern for item in self.generated for pattern in item.patterns)
        return (*self.expected, *expanded, *generated)


@dataclass(frozen=True)
class Preservation:
    interfaces: tuple[str, ...]
    errors: tuple[str, ...]
    invariants: tuple[str, ...]


@dataclass(frozen=True)
class Verification:
    focused: tuple[str, ...]
    full_gates: tuple[str, ...]


@dataclass(frozen=True)
class RefactorOracle:
    kind: str
    command: str
    evidence: tuple[str, ...]
    preserves: tuple[str, ...]


@dataclass(frozen=True)
class ChangeContract:
    source: Path
    schema_version: str
    change_id: str
    issue: int
    title: str
    classification: ChangeClassification
    base_ref: str
    branch_pattern: str | None
    expected_outcome: str
    confirmed_facts: tuple[str, ...]
    stop_conditions: tuple[str, ...]
    impact: ImpactDeclaration
    scope: Scope
    preservation: Preservation
    verification: Verification
    questions: tuple[Question, ...]
    oracle: RefactorOracle | None


def load_contract(path: Path) -> ChangeContract:
    """Load and validate one change contract without consulting Git."""

    try:
        raw = cast(Table, tomllib.loads(path.read_text(encoding="utf-8")))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ContractError([f"nao foi possivel ler {path}: {error}"]) from error
    errors: list[str] = []
    contract = _parse_contract(path, raw, errors)
    if errors:
        raise ContractError(errors)
    assert contract is not None
    return contract


def _parse_contract(path: Path, raw: Table, errors: list[str]) -> ChangeContract | None:
    schema_version = _text(raw, "schema_version", errors)
    change_id = _text(raw, "change_id", errors)
    issue = _positive_int(raw, "issue", errors)
    title = _text(raw, "title", errors)
    base_ref = _text(raw, "base_ref", errors)
    expected_outcome = _text(raw, "expected_outcome", errors)
    classification = _enum(raw, "classification", ChangeClassification, errors)
    branch_pattern = _optional_text(raw, "branch_pattern", errors)
    confirmed_facts = _text_tuple(raw, "confirmed_facts", errors, nonempty=True)
    stop_conditions = _text_tuple(raw, "stop_conditions", errors, nonempty=True)
    impact = _parse_impact(raw.get("impact"), errors)
    scope = _parse_scope(raw.get("scope"), errors)
    preservation = _parse_preservation(raw.get("preserve"), errors)
    verification = _parse_verification(raw.get("verification"), errors)
    questions = _parse_questions(raw.get("questions", []), errors)
    oracle = _parse_oracle(raw.get("oracle"), errors)
    if classification is ChangeClassification.REFACTOR:
        if oracle is None:
            errors.append("refactor exige [oracle] de caracterizacao ou equivalencia")
        if impact is not None and any(
            value is not ImpactLevel.NONE
            for value in (impact.capability, impact.persisted_contract, impact.normative)
        ):
            errors.append("refactor exige impactos capability, persisted_contract e normative=none")
        if oracle is not None and verification is not None:
            if oracle.command not in verification.focused:
                errors.append("oracle.command deve constar em verification.focused")
            missing = REFACTOR_PRESERVES.difference(oracle.preserves)
            if missing:
                errors.append(
                    "oracle.preserves deve incluir: " + ", ".join(sorted(missing))
                )
    if schema_version and schema_version != "1":
        errors.append(f"schema_version desconhecida: {schema_version}")
    if errors:
        return None
    assert schema_version is not None
    assert change_id is not None
    assert issue is not None
    assert title is not None
    assert classification is not None
    assert base_ref is not None
    assert expected_outcome is not None
    assert impact is not None
    assert scope is not None
    assert preservation is not None
    assert verification is not None
    return ChangeContract(
        source=path,
        schema_version=schema_version,
        change_id=change_id,
        issue=issue,
        title=title,
        classification=classification,
        base_ref=base_ref,
        branch_pattern=branch_pattern,
        expected_outcome=expected_outcome,
        confirmed_facts=confirmed_facts,
        stop_conditions=stop_conditions,
        impact=impact,
        scope=scope,
        preservation=preservation,
        verification=verification,
        questions=questions,
        oracle=oracle,
    )


def _parse_impact(value: object, errors: list[str]) -> ImpactDeclaration | None:
    table = _table(value, "impact", errors)
    if table is None:
        return None
    capability = _enum(table, "capability", ImpactLevel, errors, prefix="impact.")
    persisted = _enum(table, "persisted_contract", ImpactLevel, errors, prefix="impact.")
    normative = _enum(table, "normative", ImpactLevel, errors, prefix="impact.")
    notes = _text_tuple(table, "notes", errors, prefix="impact.")
    if capability is None or persisted is None or normative is None:
        return None
    return ImpactDeclaration(capability, persisted, normative, notes)


def _parse_scope(value: object, errors: list[str]) -> Scope | None:
    table = _table(value, "scope", errors)
    if table is None:
        return None
    expected = _patterns(table, "expected", errors, nonempty=True)
    forbidden = _patterns(table, "forbidden", errors)
    preexisting = _patterns(table, "preexisting", errors)
    expansions: list[Expansion] = []
    expansion_tables = _table_list(table.get("expansions", []), "scope.expansions", errors)
    for index, item in enumerate(expansion_tables):
        patterns = _patterns(
            item,
            "patterns",
            errors,
            prefix=f"scope.expansions[{index}].",
            nonempty=True,
        )
        rationale = _text(item, "rationale", errors, prefix=f"scope.expansions[{index}].")
        if rationale:
            expansions.append(Expansion(patterns, rationale))
    generated: list[GeneratedPath] = []
    generated_tables = _table_list(table.get("generated", []), "scope.generated", errors)
    for index, item in enumerate(generated_tables):
        patterns = _patterns(
            item,
            "patterns",
            errors,
            prefix=f"scope.generated[{index}].",
            nonempty=True,
        )
        sources = _patterns(
            item,
            "source_patterns",
            errors,
            prefix=f"scope.generated[{index}].",
            nonempty=True,
        )
        generated.append(GeneratedPath(patterns, sources))
    return Scope(expected, forbidden, preexisting, tuple(expansions), tuple(generated))


def _parse_preservation(value: object, errors: list[str]) -> Preservation | None:
    table = _table(value, "preserve", errors)
    if table is None:
        return None
    return Preservation(
        interfaces=_text_tuple(table, "interfaces", errors, prefix="preserve."),
        errors=_text_tuple(table, "errors", errors, prefix="preserve."),
        invariants=_text_tuple(table, "invariants", errors, prefix="preserve.", nonempty=True),
    )


def _parse_verification(value: object, errors: list[str]) -> Verification | None:
    table = _table(value, "verification", errors)
    if table is None:
        return None
    return Verification(
        focused=_text_tuple(table, "focused", errors, prefix="verification.", nonempty=True),
        full_gates=_text_tuple(table, "full_gates", errors, prefix="verification.", nonempty=True),
    )


def _parse_questions(value: object, errors: list[str]) -> tuple[Question, ...]:
    questions: list[Question] = []
    for index, item in enumerate(_table_list(value, "questions", errors)):
        prefix = f"questions[{index}]."
        text = _text(item, "text", errors, prefix=prefix)
        affects = item.get("affects_semantics")
        if not isinstance(affects, bool):
            errors.append(f"{prefix}affects_semantics deve ser booleano")
            affects = False
        status = _enum(item, "status", QuestionStatus, errors, prefix=prefix)
        resolution = _optional_text(item, "resolution", errors, prefix=prefix)
        if status is QuestionStatus.RESOLVED and not resolution:
            errors.append(f"{prefix}resolution e obrigatoria quando status=resolved")
        if text and status:
            questions.append(Question(text, affects, status, resolution))
    return tuple(questions)


def _parse_oracle(value: object, errors: list[str]) -> RefactorOracle | None:
    if value is None:
        return None
    table = _table(value, "oracle", errors)
    if table is None:
        return None
    kind = _text(table, "kind", errors, prefix="oracle.")
    command = _text(table, "command", errors, prefix="oracle.")
    evidence = _patterns(table, "evidence", errors, prefix="oracle.", nonempty=True)
    preserves = _text_tuple(table, "preserves", errors, prefix="oracle.", nonempty=True)
    if kind not in {"characterization", "equivalence"}:
        errors.append("oracle.kind deve ser characterization ou equivalence")
    if not kind or not command:
        return None
    return RefactorOracle(kind, command, evidence, preserves)


def _table(value: object, name: str, errors: list[str]) -> Table | None:
    if not isinstance(value, dict):
        errors.append(f"[{name}] e obrigatorio")
        return None
    return cast(Table, value)


def _table_list(value: object, name: str, errors: list[str]) -> list[Table]:
    if not isinstance(value, list):
        errors.append(f"{name} deve ser uma lista de tabelas")
        return []
    items = cast(list[object], value)
    if any(not isinstance(item, dict) for item in items):
        errors.append(f"{name} deve ser uma lista de tabelas")
        return []
    return cast(list[Table], value)


def _text(
    table: Table, key: str, errors: list[str], *, prefix: str = ""
) -> str | None:
    value = table.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{prefix}{key} deve ser texto nao vazio")
        return None
    return value.strip()


def _optional_text(
    table: Table, key: str, errors: list[str], *, prefix: str = ""
) -> str | None:
    value = table.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{prefix}{key} deve ser texto nao vazio quando presente")
        return None
    return value.strip()


def _positive_int(table: Table, key: str, errors: list[str]) -> int | None:
    value = table.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        errors.append(f"{key} deve ser inteiro positivo")
        return None
    return value


def _enum[EnumValue: StrEnum](
    table: Table,
    key: str,
    enum_type: type[EnumValue],
    errors: list[str],
    *,
    prefix: str = "",
) -> EnumValue | None:
    value = table.get(key)
    try:
        return enum_type(value)
    except (ValueError, TypeError):
        choices = ", ".join(item.value for item in enum_type)
        errors.append(f"{prefix}{key} deve ser um de: {choices}")
        return None


def _text_tuple(
    table: Table,
    key: str,
    errors: list[str],
    *,
    prefix: str = "",
    nonempty: bool = False,
) -> tuple[str, ...]:
    value = table.get(key, [])
    if not isinstance(value, list):
        errors.append(f"{prefix}{key} deve ser uma lista de textos nao vazios")
        return ()
    normalized_items: list[str] = []
    for item in cast(list[object], value):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{prefix}{key} deve ser uma lista de textos nao vazios")
            return ()
        normalized_items.append(item.strip())
    normalized = tuple(normalized_items)
    if nonempty and not normalized:
        errors.append(f"{prefix}{key} nao pode ser vazio")
    if len(set(normalized)) != len(normalized):
        errors.append(f"{prefix}{key} contem duplicatas")
    return normalized


def _patterns(
    table: Table,
    key: str,
    errors: list[str],
    *,
    prefix: str = "",
    nonempty: bool = False,
) -> tuple[str, ...]:
    patterns = _text_tuple(table, key, errors, prefix=prefix, nonempty=nonempty)
    for pattern in patterns:
        pure = PurePosixPath(pattern)
        if pure.is_absolute() or ".." in pure.parts or "\\" in pattern:
            errors.append(f"{prefix}{key} contem pattern inseguro: {pattern}")
    return patterns
