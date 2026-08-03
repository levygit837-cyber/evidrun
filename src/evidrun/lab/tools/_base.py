"""Validação estrita comum das tools de leitura."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from evidrun.contracts.lab_agent.errors import LabAgentError, LabAgentErrorCode, LabAgentStage
from evidrun.lab.protocol import declared_argument_keys
from evidrun.lab.tools.read_port import LabToolRejected

FORBIDDEN_SCOPE_KEYS = frozenset(
    {"workspace_id", "project_id", "scope", "session_id", "actor", "authority"}
)


def strict_schema(
    properties: Mapping[str, Mapping[str, object]], *, required: tuple[str, ...]
) -> Mapping[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": dict(properties),
        "required": list(required),
    }


def validate_arguments(
    tool_name: str, schema: Mapping[str, Any], arguments: Mapping[str, Any]
) -> None:
    declared = declared_argument_keys(schema)
    actual = frozenset(arguments)
    forbidden = actual & FORBIDDEN_SCOPE_KEYS
    if forbidden:
        field = sorted(forbidden)[0]
        raise LabToolRejected(
            _error(
                LabAgentErrorCode.SCHEMA_SCOPE_ARGUMENT_FORBIDDEN,
                "Argumentos não podem declarar scope, sessão, ator ou autoridade.",
                "Remova campos de scope; eles vêm da sessão validada.",
                tool_name,
                field,
            )
        )
    if actual != declared:
        raise LabToolRejected(
            _error(
                LabAgentErrorCode.SCHEMA_ARGUMENT_SET_INVALID,
                "O conjunto de argumentos não corresponde ao schema da tool.",
                f"Use exatamente estas chaves: {', '.join(sorted(declared)) or '(nenhuma)' }.",
                tool_name,
            )
        )
    raw_properties = schema["properties"]
    assert isinstance(raw_properties, Mapping)
    properties = cast(Mapping[str, object], raw_properties)
    for key in sorted(declared):
        definition = properties[key]
        assert isinstance(definition, Mapping)
        typed_definition = cast(Mapping[str, object], definition)
        value = arguments[key]
        expected = typed_definition.get("type")
        nullable = typed_definition.get("nullable") is True
        if not _matches_type(value, expected, nullable=nullable):
            raise LabToolRejected(
                _error(
                    LabAgentErrorCode.SCHEMA_ARGUMENT_TYPE_INVALID,
                    "Um argumento tem tipo divergente do schema.",
                    f"Use o tipo declarado para {key}.",
                    tool_name,
                    key,
                )
            )
        if isinstance(value, int) and not isinstance(value, bool):
            minimum = typed_definition.get("minimum")
            maximum = typed_definition.get("maximum")
            if (isinstance(minimum, int) and value < minimum) or (
                isinstance(maximum, int) and value > maximum
            ):
                raise LabToolRejected(
                    _error(
                        LabAgentErrorCode.SCHEMA_ARGUMENT_LIMIT_EXCEEDED,
                        "Um argumento excede os limites declarados.",
                        f"Use {key} dentro dos limites do schema.",
                        tool_name,
                        key,
                    )
                )
        if isinstance(value, list):
            items = cast(list[object], value)
            max_items = typed_definition.get("maxItems")
            if isinstance(max_items, int) and len(items) > max_items:
                raise LabToolRejected(
                    _error(
                        LabAgentErrorCode.SCHEMA_ARGUMENT_LIMIT_EXCEEDED,
                        "Um argumento excede os limites declarados.",
                        f"Reduza {key} ao máximo declarado.",
                        tool_name,
                        key,
                    )
                )
            item_type = typed_definition.get("items")
            if isinstance(item_type, Mapping):
                item_definition = cast(Mapping[str, object], item_type)
                invalid_item = any(
                    not _matches_type(item, item_definition.get("type")) for item in items
                )
            else:
                invalid_item = False
            if invalid_item:
                raise LabToolRejected(
                    _error(
                        LabAgentErrorCode.SCHEMA_ARGUMENT_TYPE_INVALID,
                        "Um item de lista tem tipo divergente do schema.",
                        f"Use itens do tipo declarado para {key}.",
                        tool_name,
                        key,
                    )
                )
        enum = typed_definition.get("enum")
        if isinstance(enum, list) and value not in cast(list[object], enum):
            raise LabToolRejected(
                _error(
                    LabAgentErrorCode.SCHEMA_ARGUMENT_TYPE_INVALID,
                    "Um argumento está fora da allowlist declarada.",
                    f"Use um valor declarado pelo schema para {key}.",
                    tool_name,
                    key,
                )
            )


def _matches_type(value: object, expected: object, *, nullable: bool = False) -> bool:
    if value is None:
        return nullable
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "array":
        return isinstance(value, list)
    return False


def _error(
    code: LabAgentErrorCode,
    message: str,
    remediation: str,
    tool_name: str,
    field: str | None = None,
) -> LabAgentError:
    return LabAgentError(
        stage=LabAgentStage.SCHEMA,
        code=code,
        message=message,
        remediation=remediation,
        field_path=(field,) if field else (),
        tool_name=tool_name,
    )
