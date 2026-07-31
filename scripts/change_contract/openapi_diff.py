"""OpenAPI surface adapter for the semantic contract diff."""

from __future__ import annotations

from typing import cast

from .schema_diff import (
    Compatibility,
    ContractChange,
    ContractDiffReport,
    ContractSurface,
    SchemaDiffError,
    compare_schema_fragment,
)

type JsonObject = dict[str, object]

HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}


def compare_openapi(
    baseline: object,
    candidate: object,
    *,
    path: str,
) -> ContractDiffReport:
    """Compare stable OpenAPI paths, operations, responses and component schemas."""

    before = _object(baseline, f"{path} baseline")
    after = _object(candidate, f"{path} candidate")
    changes: list[ContractChange] = []
    _compare_paths(before, after, changes)
    _compare_components(before, after, changes)
    return ContractDiffReport(path, ContractSurface.OPENAPI, tuple(changes))


def _compare_paths(
    before: JsonObject,
    after: JsonObject,
    changes: list[ContractChange],
) -> None:
    old_paths = _object_or_empty(before.get("paths"), "/paths")
    new_paths = _object_or_empty(after.get("paths"), "/paths")
    for path in sorted(old_paths.keys() - new_paths.keys()):
        changes.append(
            ContractChange(
                "path-removed",
                Compatibility.BREAKING,
                _join("/paths", path),
                f"O path OpenAPI {path!r} foi removido.",
            )
        )
    for path in sorted(new_paths.keys() - old_paths.keys()):
        changes.append(
            ContractChange(
                "path-added",
                Compatibility.ADDITIVE,
                _join("/paths", path),
                f"O path OpenAPI {path!r} foi adicionado.",
            )
        )
    for path in sorted(old_paths.keys() & new_paths.keys()):
        _compare_operations(
            _object(old_paths[path], f"OpenAPI path {path} baseline"),
            _object(new_paths[path], f"OpenAPI path {path} candidate"),
            _join("/paths", path),
            changes,
        )


def _compare_operations(
    before: JsonObject,
    after: JsonObject,
    pointer: str,
    changes: list[ContractChange],
) -> None:
    old_methods = HTTP_METHODS & before.keys()
    new_methods = HTTP_METHODS & after.keys()
    for method in sorted(old_methods - new_methods):
        changes.append(
            ContractChange(
                "operation-removed",
                Compatibility.BREAKING,
                _join(pointer, method),
                f"A operacao HTTP {method.upper()} foi removida.",
            )
        )
    for method in sorted(new_methods - old_methods):
        changes.append(
            ContractChange(
                "operation-added",
                Compatibility.ADDITIVE,
                _join(pointer, method),
                f"A operacao HTTP {method.upper()} foi adicionada.",
            )
        )
    for method in sorted(old_methods & new_methods):
        old_operation = _object(before[method], f"{pointer}/{method} baseline")
        new_operation = _object(after[method], f"{pointer}/{method} candidate")
        operation_pointer = _join(pointer, method)
        if old_operation.get("operationId") != new_operation.get("operationId"):
            changes.append(
                ContractChange(
                    "operation-id-changed",
                    Compatibility.BREAKING,
                    _join(operation_pointer, "operationId"),
                    "O operationId publico mudou.",
                )
            )
        _compare_response_codes(old_operation, new_operation, operation_pointer, changes)


def _compare_response_codes(
    before: JsonObject,
    after: JsonObject,
    pointer: str,
    changes: list[ContractChange],
) -> None:
    old_responses = _object_or_empty(before.get("responses"), _join(pointer, "responses"))
    new_responses = _object_or_empty(after.get("responses"), _join(pointer, "responses"))
    for status in sorted(old_responses.keys() - new_responses.keys()):
        changes.append(
            ContractChange(
                "response-removed",
                Compatibility.BREAKING,
                _join(pointer, "responses", status),
                f"A resposta OpenAPI {status!r} foi removida.",
            )
        )
    for status in sorted(new_responses.keys() - old_responses.keys()):
        changes.append(
            ContractChange(
                "response-added",
                Compatibility.ADDITIVE,
                _join(pointer, "responses", status),
                f"A resposta OpenAPI {status!r} foi adicionada.",
            )
        )


def _compare_components(
    before: JsonObject,
    after: JsonObject,
    changes: list[ContractChange],
) -> None:
    old_components = _object_or_empty(before.get("components"), "/components")
    new_components = _object_or_empty(after.get("components"), "/components")
    old_schemas = _schema_map(old_components.get("schemas"), "/components/schemas")
    new_schemas = _schema_map(new_components.get("schemas"), "/components/schemas")
    for name in sorted(old_schemas.keys() - new_schemas.keys()):
        changes.append(
            ContractChange(
                "schema-removed",
                Compatibility.BREAKING,
                _join("/components/schemas", name),
                f"O schema nomeado {name!r} foi removido.",
            )
        )
    for name in sorted(new_schemas.keys() - old_schemas.keys()):
        changes.append(
            ContractChange(
                "schema-added",
                Compatibility.ADDITIVE,
                _join("/components/schemas", name),
                f"O schema nomeado {name!r} foi adicionado.",
            )
        )
    for name in sorted(old_schemas.keys() & new_schemas.keys()):
        changes.extend(
            compare_schema_fragment(
                old_schemas[name],
                new_schemas[name],
                pointer=_join("/components/schemas", name),
            )
        )


def _object(value: object, label: str) -> JsonObject:
    if not isinstance(value, dict):
        raise SchemaDiffError(f"{label} deve ser um objeto JSON")
    raw = cast(dict[object, object], value)
    if any(not isinstance(key, str) for key in raw):
        raise SchemaDiffError(f"{label} deve possuir apenas chaves de texto")
    return cast(JsonObject, raw)


def _object_or_empty(value: object, label: str) -> JsonObject:
    if value is None:
        return {}
    return _object(value, label)


def _schema_map(value: object, label: str) -> dict[str, JsonObject]:
    table = _object_or_empty(value, label)
    return {name: _object(schema, f"{label}/{name}") for name, schema in table.items()}


def _join(pointer: str, *tokens: str) -> str:
    suffix = "/".join(token.replace("~", "~0").replace("/", "~1") for token in tokens)
    return f"{pointer}/{suffix}" if pointer else f"/{suffix}"
