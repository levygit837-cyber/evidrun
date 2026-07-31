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
        _compare_parameters(old_operation, new_operation, operation_pointer, changes)
        _compare_request_body(old_operation, new_operation, operation_pointer, changes)
        _compare_response_codes(old_operation, new_operation, operation_pointer, changes)


def _compare_parameters(
    before: JsonObject,
    after: JsonObject,
    pointer: str,
    changes: list[ContractChange],
) -> None:
    old_parameters = _parameters(before.get("parameters"), _join(pointer, "parameters"))
    new_parameters = _parameters(after.get("parameters"), _join(pointer, "parameters"))
    for key in sorted(old_parameters.keys() - new_parameters.keys()):
        changes.append(
            ContractChange(
                "parameter-removed",
                Compatibility.BREAKING,
                _join(pointer, "parameters", f"{key[0]}:{key[1]}"),
                f"O parametro OpenAPI {key[0]}:{key[1]} foi removido.",
            )
        )
    for key in sorted(new_parameters.keys() - old_parameters.keys()):
        parameter = new_parameters[key]
        required = parameter.get("required") is True
        changes.append(
            ContractChange(
                "required-parameter-added" if required else "optional-parameter-added",
                Compatibility.BREAKING if required else Compatibility.ADDITIVE,
                _join(pointer, "parameters", f"{key[0]}:{key[1]}"),
                f"O parametro OpenAPI {key[0]}:{key[1]} foi adicionado.",
            )
        )
    for key in sorted(old_parameters.keys() & new_parameters.keys()):
        old = old_parameters[key]
        new = new_parameters[key]
        location = _join(pointer, "parameters", f"{key[0]}:{key[1]}")
        if old.get("required") != new.get("required"):
            changes.append(
                ContractChange(
                    "parameter-required-changed",
                    (
                        Compatibility.BREAKING
                        if new.get("required") is True
                        else Compatibility.ADDITIVE
                    ),
                    _join(location, "required"),
                    f"A obrigatoriedade do parametro {key[0]}:{key[1]} mudou.",
                )
            )
        _compare_optional_schema(old.get("schema"), new.get("schema"), location, changes)


def _compare_request_body(
    before: JsonObject,
    after: JsonObject,
    pointer: str,
    changes: list[ContractChange],
) -> None:
    old_value = before.get("requestBody")
    new_value = after.get("requestBody")
    location = _join(pointer, "requestBody")
    if old_value is None and new_value is None:
        return
    if old_value is None:
        new = _object(new_value, f"{location} candidate")
        required = new.get("required") is True
        changes.append(
            ContractChange(
                "required-request-body-added" if required else "optional-request-body-added",
                Compatibility.BREAKING if required else Compatibility.ADDITIVE,
                location,
                "Um request body foi adicionado.",
            )
        )
        return
    if new_value is None:
        changes.append(
            ContractChange(
                "request-body-removed",
                Compatibility.BREAKING,
                location,
                "O request body foi removido.",
            )
        )
        return
    old = _object(old_value, f"{location} baseline")
    new = _object(new_value, f"{location} candidate")
    _compare_reference(old, new, location, changes)
    if old.get("required") != new.get("required"):
        changes.append(
            ContractChange(
                "request-body-required-changed",
                (Compatibility.BREAKING if new.get("required") is True else Compatibility.ADDITIVE),
                _join(location, "required"),
                "A obrigatoriedade do request body mudou.",
            )
        )
    _compare_content(old, new, location, changes)


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
    for status in sorted(old_responses.keys() & new_responses.keys()):
        old = _object(old_responses[status], f"response {status} baseline")
        new = _object(new_responses[status], f"response {status} candidate")
        _compare_reference(old, new, _join(pointer, "responses", status), changes)
        _compare_content(old, new, _join(pointer, "responses", status), changes)


def _compare_content(
    before: JsonObject,
    after: JsonObject,
    pointer: str,
    changes: list[ContractChange],
) -> None:
    old_content = _object_or_empty(before.get("content"), _join(pointer, "content"))
    new_content = _object_or_empty(after.get("content"), _join(pointer, "content"))
    for media_type in sorted(old_content.keys() - new_content.keys()):
        changes.append(
            ContractChange(
                "media-type-removed",
                Compatibility.BREAKING,
                _join(pointer, "content", media_type),
                f"O media type {media_type!r} foi removido.",
            )
        )
    for media_type in sorted(new_content.keys() - old_content.keys()):
        changes.append(
            ContractChange(
                "media-type-added",
                Compatibility.ADDITIVE,
                _join(pointer, "content", media_type),
                f"O media type {media_type!r} foi adicionado.",
            )
        )
    for media_type in sorted(old_content.keys() & new_content.keys()):
        old = _object(old_content[media_type], f"content {media_type} baseline")
        new = _object(new_content[media_type], f"content {media_type} candidate")
        _compare_optional_schema(
            old.get("schema"),
            new.get("schema"),
            _join(pointer, "content", media_type),
            changes,
        )


def _compare_optional_schema(
    before: object,
    after: object,
    pointer: str,
    changes: list[ContractChange],
) -> None:
    location = _join(pointer, "schema")
    if before is None and after is None:
        return
    if before is None or after is None:
        changes.append(
            ContractChange(
                "schema-added" if before is None else "schema-removed",
                Compatibility.BREAKING,
                location,
                "O schema inline foi adicionado ou removido.",
            )
        )
        return
    changes.extend(compare_schema_fragment(before, after, pointer=location))


def _compare_reference(
    before: JsonObject,
    after: JsonObject,
    pointer: str,
    changes: list[ContractChange],
) -> None:
    if before.get("$ref") != after.get("$ref"):
        changes.append(
            ContractChange(
                "reference-changed",
                Compatibility.BREAKING,
                _join(pointer, "$ref"),
                "A referencia OpenAPI mudou.",
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


def _parameters(value: object, label: str) -> dict[tuple[str, str], JsonObject]:
    if value is None:
        return {}
    if not isinstance(value, list):
        raise SchemaDiffError(f"{label} deve ser uma lista")
    parameters: dict[tuple[str, str], JsonObject] = {}
    for index, raw in enumerate(cast(list[object], value)):
        parameter = _object(raw, f"{label}/{index}")
        reference = parameter.get("$ref")
        if isinstance(reference, str):
            parameters[("$ref", reference)] = parameter
            continue
        name = parameter.get("name")
        location = parameter.get("in")
        if not isinstance(name, str) or not isinstance(location, str):
            raise SchemaDiffError(f"{label}/{index} exige name e in textuais")
        parameters[(location, name)] = parameter
    return parameters


def _join(pointer: str, *tokens: str) -> str:
    suffix = "/".join(token.replace("~", "~0").replace("/", "~1") for token in tokens)
    return f"{pointer}/{suffix}" if pointer else f"/{suffix}"
