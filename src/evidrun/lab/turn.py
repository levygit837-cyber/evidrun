"""Estado e terminais de um turno do Lab Agent."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, cast

from evidrun.contracts.lab_agent.errors import LabAgentError, LabAgentErrorCode
from evidrun.lab.protocol import LabToolContext, declared_argument_keys

_FORBIDDEN_SCOPE_KEYS = frozenset(
    {"workspace_id", "project_id", "scope", "session_id", "actor", "authority"}
)


def _empty_usage() -> dict[str, int]:
    return {}


class LabTurnTerminalName(StrEnum):
    ANSWERED = "answered"
    PROPOSED = "proposed"
    BUDGET_EXHAUSTED = "budget_exhausted"
    REPEATED_REFUSAL = "repeated_refusal"
    PROVIDER_FAILED = "provider_failed"
    CANCELLED = "cancelled"


class TurnBudget(StrEnum):
    """O teto que encerrou o turno.

    Enum e não texto livre porque o valor atravessa a fronteira de stream até a UI, que
    precisa distinguir qual teto foi alcançado para dizer ao humano o que aconteceu. Os
    valores são os nomes declarados no contrato de loop v1.
    """

    TOOL_CALLS = "max_tool_calls_per_turn"
    ROUND_TRIPS = "max_provider_round_trips_per_turn"
    WALL_SECONDS = "max_wall_seconds_per_turn"
    REFUSALS = "max_refusals_per_turn"


@dataclass(frozen=True, slots=True)
class LabTurnTerminal:
    """Resultado nomeado; `complete` impede apresentar interrupção como resposta completa."""

    name: LabTurnTerminalName
    content: str = ""
    complete: bool = True
    error: LabAgentError | None = None
    budget: TurnBudget | None = None
    returned_refs: tuple[str, ...] = ()
    provider_round_trips: int = 0
    tool_calls: int = 0
    refusals: int = 0
    usage: Mapping[str, int] = field(default_factory=_empty_usage)


@dataclass(slots=True)
class LabTurnState:
    transcript: list[dict[str, Any]]
    provider_round_trips: int = 0
    tool_calls: int = 0
    refusals: int = 0
    proposed: bool = False
    returned_refs: list[str] = field(default_factory=list[str])
    refusal_digests: set[str] = field(default_factory=set[str])
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    def usage(self) -> dict[str, int]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
        }


def workspace_id(context: LabToolContext) -> str:
    return context.scope.workspace_id


def parse_arguments(raw: str, tool_name: str) -> tuple[Mapping[str, Any], LabAgentError | None]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {"$raw": raw}, refusal_error(
            LabAgentErrorCode.SCHEMA_ARGUMENT_TYPE_INVALID, tool_name=tool_name
        )
    if not isinstance(value, Mapping):
        return {"$value": value}, refusal_error(
            LabAgentErrorCode.SCHEMA_ARGUMENT_TYPE_INVALID, tool_name=tool_name
        )
    return cast(Mapping[str, Any], value), None


def validate_schema(
    schema: Mapping[str, Any], arguments: Mapping[str, Any], tool_name: str
) -> LabAgentError | None:
    forbidden = set(arguments) & _FORBIDDEN_SCOPE_KEYS
    if forbidden:
        field = sorted(forbidden)[0]
        return refusal_error(
            LabAgentErrorCode.SCHEMA_SCOPE_ARGUMENT_FORBIDDEN,
            tool_name=tool_name,
            field_path=(field,),
        )
    declared = declared_argument_keys(schema)
    if set(arguments) != set(declared):
        return refusal_error(LabAgentErrorCode.SCHEMA_ARGUMENT_SET_INVALID, tool_name=tool_name)
    properties_value: object = schema.get("properties")
    if not isinstance(properties_value, Mapping):
        return refusal_error(LabAgentErrorCode.SCHEMA_ARGUMENT_SET_INVALID, tool_name=tool_name)
    properties = cast(Mapping[str, object], properties_value)
    for key, value in arguments.items():
        rule_value = properties.get(key)
        if not isinstance(rule_value, Mapping):
            return refusal_error(
                LabAgentErrorCode.SCHEMA_ARGUMENT_TYPE_INVALID,
                tool_name=tool_name,
                field_path=(key,),
            )
        rule = cast(Mapping[str, Any], rule_value)
        error = _validate_value(value, rule, tool_name, (key,))
        if error is not None:
            return error
    return None


def _validate_value(
    value: Any, rule: Mapping[str, Any], tool_name: str, path: tuple[str, ...]
) -> LabAgentError | None:
    expected = cast(str | None, rule.get("type"))
    validators: dict[str, bool] = {
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, int | float) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "array": isinstance(value, list),
        "object": isinstance(value, Mapping),
        "null": value is None,
    }
    valid = validators.get(expected, False) if expected is not None else False
    if not valid:
        return refusal_error(
            LabAgentErrorCode.SCHEMA_ARGUMENT_TYPE_INVALID, tool_name=tool_name, field_path=path
        )
    if isinstance(value, str):
        if (limit := rule.get("maxLength")) is not None and len(value) > limit:
            return refusal_error(
                LabAgentErrorCode.SCHEMA_ARGUMENT_LIMIT_EXCEEDED,
                tool_name=tool_name,
                field_path=path,
            )
        if (minimum := rule.get("minLength")) is not None and len(value) < minimum:
            return refusal_error(
                LabAgentErrorCode.SCHEMA_ARGUMENT_LIMIT_EXCEEDED,
                tool_name=tool_name,
                field_path=path,
            )
        if (choices := rule.get("enum")) is not None and value not in choices:
            return refusal_error(
                LabAgentErrorCode.SCHEMA_ARGUMENT_TYPE_INVALID, tool_name=tool_name, field_path=path
            )
    if isinstance(value, int | float) and not isinstance(value, bool):
        if (maximum := rule.get("maximum")) is not None and value > maximum:
            return refusal_error(
                LabAgentErrorCode.SCHEMA_ARGUMENT_LIMIT_EXCEEDED,
                tool_name=tool_name,
                field_path=path,
            )
        if (minimum := rule.get("minimum")) is not None and value < minimum:
            return refusal_error(
                LabAgentErrorCode.SCHEMA_ARGUMENT_LIMIT_EXCEEDED,
                tool_name=tool_name,
                field_path=path,
            )
    if isinstance(value, list):
        maximum_items = cast(int | None, rule.get("maxItems"))
        items = cast(list[Any], value)
        if maximum_items is not None and len(items) > maximum_items:
            return refusal_error(
                LabAgentErrorCode.SCHEMA_ARGUMENT_LIMIT_EXCEEDED,
                tool_name=tool_name,
                field_path=path,
            )
        item_rule = rule.get("items")
        if isinstance(item_rule, Mapping):
            typed_item_rule = cast(Mapping[str, Any], item_rule)
            for index, item in enumerate(items):
                error = _validate_value(item, typed_item_rule, tool_name, (*path, str(index)))
                if error is not None:
                    return error
    return None


def refusal_error(
    code: LabAgentErrorCode,
    *,
    tool_name: str | None = None,
    field_path: tuple[str, ...] = (),
) -> LabAgentError:
    messages: dict[LabAgentErrorCode, tuple[str, str]] = {
        LabAgentErrorCode.CATALOG_TOOL_UNKNOWN: (
            "A tool solicitada não existe no catálogo efetivo.",
            "Use somente uma tool anunciada nesta sessão.",
        ),
        LabAgentErrorCode.CATALOG_TOOL_NOT_OFFERED: (
            "A tool solicitada não é oferecida nesta forma de sessão.",
            "Use uma tool anunciada ou abra a forma de sessão necessária.",
        ),
        LabAgentErrorCode.BUDGET_TOOL_CALLS_EXHAUSTED: (
            "O teto de tool calls deste turno foi alcançado.",
            "Responda com o trabalho já concluído; não solicite outra tool.",
        ),
        LabAgentErrorCode.BUDGET_WALL_TIME_EXHAUSTED: (
            "O teto de tempo deste turno foi alcançado.",
            "Responda com o trabalho já concluído.",
        ),
        LabAgentErrorCode.SCHEMA_ARGUMENT_SET_INVALID: (
            "O conjunto de argumentos não corresponde ao schema da tool.",
            "Use exatamente as chaves declaradas pela tool.",
        ),
        LabAgentErrorCode.SCHEMA_ARGUMENT_TYPE_INVALID: (
            "Um argumento não corresponde ao tipo declarado.",
            "Corrija o tipo do campo indicado antes de tentar novamente.",
        ),
        LabAgentErrorCode.SCHEMA_ARGUMENT_LIMIT_EXCEEDED: (
            "Um argumento excede o limite declarado.",
            "Reduza o valor ao teto declarado antes de tentar novamente.",
        ),
        LabAgentErrorCode.SCHEMA_SCOPE_ARGUMENT_FORBIDDEN: (
            "Scope, sessão e autoridade não podem ser argumentos de tool.",
            "Remova o campo; o runtime deriva o scope da sessão validada.",
        ),
    }
    entry = messages.get(code)
    if entry is None:
        # Sem fallback genérico de propósito. "A chamada foi recusada" é exatamente a
        # remediação que o errors-v1 classifica como causadora de laço: ela nega sem nomear
        # a próxima ação válida, então o modelo tenta variações até esgotar budget. Um código
        # novo sem texto próprio é defeito de programação e falha alto, no import do teste,
        # em vez de degradar silenciosamente dentro do laço.
        raise ValueError(
            f"refusal code without a declared message and remediation: {code.value}"
        )
    message, remediation = entry
    return LabAgentError(
        stage=code.stage,
        code=code,
        message=message,
        remediation=remediation,
        field_path=field_path,
        tool_name=tool_name,
    )


def error_payload(error: LabAgentError) -> dict[str, object]:
    return {
        "stage": error.stage.value,
        "code": error.code.value,
        "category": error.category.value,
        "message": error.message,
        "remediation": error.remediation,
        "field_path": list(error.field_path),
        "tool_name": error.tool_name,
    }
