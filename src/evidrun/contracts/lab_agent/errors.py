"""O catálogo de recusas do Lab Agent: etapas, códigos e tabelas totais de tradução.

Costura separada de `TriageError` e `ScopeError` pela mesma razão que aquelas duas são
separadas entre si: recusar uma tool call de copiloto não é uma das seis fases que
antecedem uma Run, nem a criação de uma fronteira do Control Plane. Ver
`docs/contracts/observable-errors.md`.

`remediation` é obrigatória aqui, ao contrário de `TriageError`, porque o leitor primário
da recusa é o modelo dentro do laço: negar sem nomear a próxima ação convida à repetição,
e repetição é o laço de tool call que o produto evita sem heurística.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import IntEnum, StrEnum
from types import MappingProxyType
from typing import Any

from pydantic import computed_field, model_validator

from evidrun.contracts.base import ContractModel, NonEmptyStr


class LabAgentStage(StrEnum):
    """A etapa que recusou.

    As cinco primeiras espelham a ordem de verificação do loop v1. `AUTHORITY` e `DRAFT`
    não são posições do laço: são recusas de natureza, válidas em qualquer ponto.
    """

    CATALOG = "catalog"
    BUDGET = "budget"
    SCHEMA = "schema"
    SCOPE = "scope"
    CLASSIFICATION = "classification"
    AUTHORITY = "authority"
    DRAFT = "draft"


class LabAgentErrorCode(StrEnum):
    CATALOG_TOOL_UNKNOWN = "catalog.tool_unknown"
    CATALOG_TOOL_NOT_OFFERED = "catalog.tool_not_offered"

    BUDGET_TOOL_CALLS_EXHAUSTED = "budget.tool_calls_exhausted"
    BUDGET_ROUND_TRIPS_EXHAUSTED = "budget.round_trips_exhausted"
    BUDGET_WALL_TIME_EXHAUSTED = "budget.wall_time_exhausted"
    BUDGET_REFUSALS_EXHAUSTED = "budget.refusals_exhausted"
    BUDGET_REFUSAL_REPEATED = "budget.refusal_repeated"

    SCHEMA_ARGUMENT_SET_INVALID = "schema.argument_set_invalid"
    SCHEMA_ARGUMENT_TYPE_INVALID = "schema.argument_type_invalid"
    SCHEMA_ARGUMENT_LIMIT_EXCEEDED = "schema.argument_limit_exceeded"
    SCHEMA_SCOPE_ARGUMENT_FORBIDDEN = "schema.scope_argument_forbidden"

    SCOPE_TARGET_NOT_VISIBLE = "scope.target_not_visible"
    SCOPE_FOCUS_MISMATCH = "scope.focus_mismatch"
    SCOPE_PROJECT_REQUIRED = "scope.project_required"

    CLASSIFICATION_GRANT_REQUIRED = "classification.grant_required"

    AUTHORITY_HUMAN_DECISION_REQUIRED = "authority.human_decision_required"
    AUTHORITY_LEDGER_WRITE_FORBIDDEN = "authority.ledger_write_forbidden"
    AUTHORITY_PERSISTED_EFFECT_FORBIDDEN = "authority.persisted_effect_forbidden"

    DRAFT_VALIDATION_FAILED = "draft.validation_failed"
    DRAFT_NOT_VALIDATED = "draft.not_validated"
    DRAFT_SCOPE_OVERRIDE_FORBIDDEN = "draft.scope_override_forbidden"

    @property
    def stage(self) -> LabAgentStage:
        prefix, _separator, _name = self.value.partition(".")
        return LabAgentStage(prefix)


class LabAgentErrorCategory(StrEnum):
    INVALID = "invalid"
    REJECTED = "rejected"
    NOT_FOUND = "not_found"
    FORBIDDEN = "forbidden"
    EXHAUSTED = "exhausted"


class LabAgentCliExitCode(IntEnum):
    INVALID = 2
    REJECTED = 3
    NOT_FOUND = 4
    FORBIDDEN = 6
    EXHAUSTED = 7


class LabAgentError(ContractModel):
    """Uma recusa nomeada do Lab Agent.

    `category` é derivada do `code`, nunca da mensagem: nenhuma borda deduz causa por
    texto. `message` é português brasileiro livre e traduzível; código, categoria, etapa,
    forma do payload, status HTTP e exit code são o contrato.
    """

    stage: LabAgentStage
    code: LabAgentErrorCode
    message: NonEmptyStr
    remediation: NonEmptyStr
    field_path: tuple[NonEmptyStr, ...] = ()
    tool_name: NonEmptyStr | None = None

    @computed_field
    @property
    def category(self) -> LabAgentErrorCategory:
        return CATEGORY_BY_CODE[self.code]

    @model_validator(mode="after")
    def validate_code_stage(self) -> LabAgentError:
        if self.code.stage != self.stage:
            raise ValueError("code prefix must match stage")
        return self


CATEGORY_BY_CODE: Mapping[LabAgentErrorCode, LabAgentErrorCategory] = MappingProxyType(
    {
        LabAgentErrorCode.CATALOG_TOOL_UNKNOWN: LabAgentErrorCategory.NOT_FOUND,
        LabAgentErrorCode.CATALOG_TOOL_NOT_OFFERED: LabAgentErrorCategory.NOT_FOUND,
        LabAgentErrorCode.BUDGET_TOOL_CALLS_EXHAUSTED: LabAgentErrorCategory.EXHAUSTED,
        LabAgentErrorCode.BUDGET_ROUND_TRIPS_EXHAUSTED: LabAgentErrorCategory.EXHAUSTED,
        LabAgentErrorCode.BUDGET_WALL_TIME_EXHAUSTED: LabAgentErrorCategory.EXHAUSTED,
        LabAgentErrorCode.BUDGET_REFUSALS_EXHAUSTED: LabAgentErrorCategory.EXHAUSTED,
        LabAgentErrorCode.BUDGET_REFUSAL_REPEATED: LabAgentErrorCategory.EXHAUSTED,
        LabAgentErrorCode.SCHEMA_ARGUMENT_SET_INVALID: LabAgentErrorCategory.INVALID,
        LabAgentErrorCode.SCHEMA_ARGUMENT_TYPE_INVALID: LabAgentErrorCategory.INVALID,
        LabAgentErrorCode.SCHEMA_ARGUMENT_LIMIT_EXCEEDED: LabAgentErrorCategory.INVALID,
        LabAgentErrorCode.SCHEMA_SCOPE_ARGUMENT_FORBIDDEN: LabAgentErrorCategory.INVALID,
        LabAgentErrorCode.SCOPE_TARGET_NOT_VISIBLE: LabAgentErrorCategory.NOT_FOUND,
        LabAgentErrorCode.SCOPE_FOCUS_MISMATCH: LabAgentErrorCategory.NOT_FOUND,
        LabAgentErrorCode.SCOPE_PROJECT_REQUIRED: LabAgentErrorCategory.REJECTED,
        LabAgentErrorCode.CLASSIFICATION_GRANT_REQUIRED: LabAgentErrorCategory.FORBIDDEN,
        LabAgentErrorCode.AUTHORITY_HUMAN_DECISION_REQUIRED: LabAgentErrorCategory.REJECTED,
        LabAgentErrorCode.AUTHORITY_LEDGER_WRITE_FORBIDDEN: LabAgentErrorCategory.REJECTED,
        LabAgentErrorCode.AUTHORITY_PERSISTED_EFFECT_FORBIDDEN: LabAgentErrorCategory.REJECTED,
        LabAgentErrorCode.DRAFT_VALIDATION_FAILED: LabAgentErrorCategory.INVALID,
        LabAgentErrorCode.DRAFT_NOT_VALIDATED: LabAgentErrorCategory.REJECTED,
        LabAgentErrorCode.DRAFT_SCOPE_OVERRIDE_FORBIDDEN: LabAgentErrorCategory.REJECTED,
    }
)

#: Traduzir por categoria, e não por código, é o que mantém `scope.target_not_visible`
#: indistinguível: um status próprio para "não é seu" seria um oráculo de existência.
HTTP_STATUS_BY_CATEGORY: Mapping[LabAgentErrorCategory, int] = MappingProxyType(
    {
        LabAgentErrorCategory.INVALID: 422,
        LabAgentErrorCategory.REJECTED: 422,
        LabAgentErrorCategory.NOT_FOUND: 404,
        LabAgentErrorCategory.FORBIDDEN: 403,
        LabAgentErrorCategory.EXHAUSTED: 429,
    }
)

HTTP_STATUS_BY_CODE: Mapping[LabAgentErrorCode, int] = MappingProxyType(
    {code: HTTP_STATUS_BY_CATEGORY[category] for code, category in CATEGORY_BY_CODE.items()}
)

CLI_EXIT_BY_CATEGORY: Mapping[LabAgentErrorCategory, LabAgentCliExitCode] = MappingProxyType(
    {
        LabAgentErrorCategory.INVALID: LabAgentCliExitCode.INVALID,
        LabAgentErrorCategory.REJECTED: LabAgentCliExitCode.REJECTED,
        LabAgentErrorCategory.NOT_FOUND: LabAgentCliExitCode.NOT_FOUND,
        LabAgentErrorCategory.FORBIDDEN: LabAgentCliExitCode.FORBIDDEN,
        LabAgentErrorCategory.EXHAUSTED: LabAgentCliExitCode.EXHAUSTED,
    }
)

CLI_EXIT_BY_CODE: Mapping[LabAgentErrorCode, LabAgentCliExitCode] = MappingProxyType(
    {code: CLI_EXIT_BY_CATEGORY[category] for code, category in CATEGORY_BY_CODE.items()}
)


def validate_lab_agent_error_tables(
    http_status_by_code: Mapping[Any, Any] = HTTP_STATUS_BY_CODE,
    cli_exit_by_code: Mapping[Any, Any] = CLI_EXIT_BY_CODE,
) -> None:
    declared = set(LabAgentErrorCode)
    for name, entries in (
        ("category table", set(CATEGORY_BY_CODE)),
        ("HTTP status table", set(http_status_by_code)),
        ("CLI exit table", set(cli_exit_by_code)),
    ):
        missing = declared - entries
        orphaned = entries - declared
        if missing or orphaned:
            raise ValueError(
                f"{name} must match declared Lab Agent codes; "
                f"missing={sorted(str(item) for item in missing)}, "
                f"orphaned={sorted(str(item) for item in orphaned)}"
            )


validate_lab_agent_error_tables()


class LabAgentTargetSituation(StrEnum):
    """Por que o alvo não está disponível: a razão real, conhecida só pelo enforcement.

    Este tipo existe para ser apagado. `target_not_visible` aceita qualquer uma das três e
    produz a mesma recusa, então a indistinguibilidade deixa de ser convenção que cada
    callsite reescreve à mão — e a primeira divergência entre callsites é exatamente o que
    transformaria a recusa num oráculo de existência.
    """

    ABSENT = "absent"
    SIBLING_PROJECT = "sibling_project"
    OTHER_WORKSPACE = "other_workspace"


def target_not_visible(
    situation: LabAgentTargetSituation,
    *,
    field_path: tuple[str, ...] = (),
    tool_name: str | None = None,
) -> LabAgentError:
    """A recusa de alvo não visível, idêntica nas três situações.

    `situation` é exigida e descartada: nenhum campo da recusa deriva dela. A assinatura a
    pede para que o callsite prove ter classificado o alvo, e o descarte concentra num
    único ponto a decisão de não revelar. Ramificar aqui por `situation` é a regressão que
    o contrato proíbe.

    A remediação instrui a **listar**, não a pedir acesso: sugerir acesso confirmaria que
    existe algo a acessar, e tentar outro id gastaria budget numa sequência de recusas.
    """

    del situation
    return LabAgentError(
        stage=LabAgentStage.SCOPE,
        code=LabAgentErrorCode.SCOPE_TARGET_NOT_VISIBLE,
        message="A referência solicitada não está disponível nesta sessão.",
        remediation="Liste os alvos deste Project antes de referenciar um id.",
        field_path=field_path,
        tool_name=tool_name,
    )
