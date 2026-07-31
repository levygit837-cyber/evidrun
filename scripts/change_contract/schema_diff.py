"""Deterministic semantic diffs for JSON Schema and OpenAPI documents."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, cast

type JsonObject = dict[str, object]


class SchemaDiffError(ValueError):
    """A contract document cannot be compared safely."""


class Compatibility(StrEnum):
    COMPATIBLE = "compatible"
    ADDITIVE = "additive"
    BREAKING = "breaking"


class ContractSurface(StrEnum):
    JSON_SCHEMA = "json-schema"
    OPENAPI = "openapi"
    PERSISTED_MODEL = "persisted-model"
    EVENT = "event"
    CLI = "cli"
    EXPORT = "export"


@dataclass(frozen=True)
class ContractChange:
    kind: str
    compatibility: Compatibility
    pointer: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {
            "kind": self.kind,
            "compatibility": self.compatibility.value,
            "pointer": self.pointer,
            "message": self.message,
        }


@dataclass(frozen=True)
class ContractDiffReport:
    path: str
    surface: ContractSurface
    changes: tuple[ContractChange, ...]

    @property
    def highest_compatibility(self) -> Compatibility:
        if any(item.compatibility is Compatibility.BREAKING for item in self.changes):
            return Compatibility.BREAKING
        if self.changes:
            return Compatibility.ADDITIVE
        return Compatibility.COMPATIBLE

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "surface": self.surface.value,
            "compatibility": self.highest_compatibility.value,
            "changes": [item.as_dict() for item in self.changes],
        }


def compare_json_schema(
    baseline: object,
    candidate: object,
    *,
    path: str,
) -> ContractDiffReport:
    """Compare two JSON Schema roots using conservative compatibility rules."""

    changes = compare_schema_fragment(baseline, candidate)
    return ContractDiffReport(path, ContractSurface.JSON_SCHEMA, changes)


def compare_schema_fragment(
    baseline: object,
    candidate: object,
    *,
    pointer: str = "",
) -> tuple[ContractChange, ...]:
    """Compare one JSON Schema fragment for composition by surface adapters."""

    before = _object(baseline, f"{pointer or '/'} baseline")
    after = _object(candidate, f"{pointer or '/'} candidate")
    changes: list[ContractChange] = []
    _compare_schema(before, after, pointer, changes)
    return tuple(changes)


def _compare_schema(
    before: JsonObject,
    after: JsonObject,
    pointer: str,
    changes: list[ContractChange],
) -> None:
    _compare_type(before, after, pointer, changes)
    _compare_enum(before, after, pointer, changes)
    _compare_properties(before, after, pointer, changes)
    _compare_definitions(before, after, pointer, changes)
    _compare_additional_properties(before, after, pointer, changes)
    _compare_constraints(before, after, pointer, changes)
    _compare_exact_keywords(before, after, pointer, changes)
    if "items" in before or "items" in after:
        _compare_nested_schema(before.get("items"), after.get("items"), pointer, "items", changes)


def _compare_type(
    before: JsonObject,
    after: JsonObject,
    pointer: str,
    changes: list[ContractChange],
) -> None:
    old_types = _types(before.get("type"), _join(pointer, "type"))
    new_types = _types(after.get("type"), _join(pointer, "type"))
    if old_types == new_types:
        return
    if old_types is not None and new_types is not None and old_types < new_types:
        compatibility = Compatibility.BREAKING
        kind = "types-added"
        message = "O schema passou a aceitar ou produzir tipos adicionais."
    else:
        compatibility = Compatibility.BREAKING
        kind = "type-changed"
        message = "O tipo aceito ou garantido pelo schema mudou."
    changes.append(ContractChange(kind, compatibility, _join(pointer, "type"), message))


def _compare_enum(
    before: JsonObject,
    after: JsonObject,
    pointer: str,
    changes: list[ContractChange],
) -> None:
    old_values = _enum_values(before.get("enum"), _join(pointer, "enum"))
    new_values = _enum_values(after.get("enum"), _join(pointer, "enum"))
    if old_values == new_values:
        return
    location = _join(pointer, "enum")
    if old_values is None or new_values is None:
        compatibility = Compatibility.BREAKING
        kind = "enum-removed" if new_values is None else "enum-added"
        message = (
            "A restricao enum foi removida."
            if new_values is None
            else "Uma restricao enum foi adicionada."
        )
        changes.append(ContractChange(kind, compatibility, location, message))
        return
    removed = old_values - new_values
    added = new_values - old_values
    if removed:
        changes.append(
            ContractChange(
                "enum-values-removed",
                Compatibility.BREAKING,
                location,
                f"O enum deixou de aceitar {len(removed)} valor(es).",
            )
        )
    if added:
        changes.append(
            ContractChange(
                "enum-values-added",
                Compatibility.BREAKING,
                location,
                f"O enum passou a aceitar {len(added)} valor(es).",
            )
        )


def _compare_properties(
    before: JsonObject,
    after: JsonObject,
    pointer: str,
    changes: list[ContractChange],
) -> None:
    old_properties = _schema_map(before.get("properties"), _join(pointer, "properties"))
    new_properties = _schema_map(after.get("properties"), _join(pointer, "properties"))
    old_required = _required(before.get("required"), _join(pointer, "required"))
    new_required = _required(after.get("required"), _join(pointer, "required"))
    for name in sorted(old_properties.keys() - new_properties.keys()):
        changes.append(
            ContractChange(
                "property-removed",
                Compatibility.BREAKING,
                _join(pointer, "properties", name),
                f"A propriedade {name!r} foi removida.",
            )
        )
    for name in sorted(new_properties.keys() - old_properties.keys()):
        required = name in new_required
        changes.append(
            ContractChange(
                "required-property-added" if required else "optional-property-added",
                Compatibility.BREAKING if required else Compatibility.ADDITIVE,
                _join(pointer, "properties", name),
                (
                    f"A propriedade obrigatoria {name!r} foi adicionada."
                    if required
                    else f"A propriedade opcional {name!r} foi adicionada."
                ),
            )
        )
    for name in sorted(old_properties.keys() & new_properties.keys()):
        property_pointer = _join(pointer, "properties", name)
        if name not in old_required and name in new_required:
            changes.append(
                ContractChange(
                    "property-became-required",
                    Compatibility.BREAKING,
                    _join(pointer, "required"),
                    f"A propriedade {name!r} passou a ser obrigatoria.",
                )
            )
        elif name in old_required and name not in new_required:
            changes.append(
                ContractChange(
                    "property-became-optional",
                    Compatibility.BREAKING,
                    _join(pointer, "required"),
                    f"A propriedade {name!r} deixou de ser garantida como obrigatoria.",
                )
            )
        _compare_schema(old_properties[name], new_properties[name], property_pointer, changes)


def _compare_definitions(
    before: JsonObject,
    after: JsonObject,
    pointer: str,
    changes: list[ContractChange],
) -> None:
    for keyword in ("$defs", "definitions"):
        old_definitions = _schema_map(before.get(keyword), _join(pointer, keyword))
        new_definitions = _schema_map(after.get(keyword), _join(pointer, keyword))
        _compare_named_schemas(old_definitions, new_definitions, _join(pointer, keyword), changes)


def _compare_named_schemas(
    before: dict[str, JsonObject],
    after: dict[str, JsonObject],
    pointer: str,
    changes: list[ContractChange],
) -> None:
    for name in sorted(before.keys() - after.keys()):
        changes.append(
            ContractChange(
                "schema-removed",
                Compatibility.BREAKING,
                _join(pointer, name),
                f"O schema nomeado {name!r} foi removido.",
            )
        )
    for name in sorted(after.keys() - before.keys()):
        changes.append(
            ContractChange(
                "schema-added",
                Compatibility.BREAKING,
                _join(pointer, name),
                f"O schema nomeado {name!r} foi adicionado.",
            )
        )
    for name in sorted(before.keys() & after.keys()):
        _compare_schema(before[name], after[name], _join(pointer, name), changes)


def _compare_additional_properties(
    before: JsonObject,
    after: JsonObject,
    pointer: str,
    changes: list[ContractChange],
) -> None:
    old = before.get("additionalProperties", True)
    new = after.get("additionalProperties", True)
    if old == new:
        if isinstance(old, dict) and isinstance(new, dict):
            _compare_schema(
                cast(JsonObject, old),
                cast(JsonObject, new),
                _join(pointer, "additionalProperties"),
                changes,
            )
        return
    location = _join(pointer, "additionalProperties")
    if old is False and new is True:
        changes.append(
            ContractChange(
                "additional-properties-allowed",
                Compatibility.ADDITIVE,
                location,
                "O schema passou a aceitar propriedades adicionais.",
            )
        )
        return
    changes.append(
        ContractChange(
            "additional-properties-changed",
            Compatibility.BREAKING,
            location,
            "A politica de propriedades adicionais mudou.",
        )
    )


def _compare_constraints(
    before: JsonObject,
    after: JsonObject,
    pointer: str,
    changes: list[ContractChange],
) -> None:
    increasing_is_stricter = ("minimum", "exclusiveMinimum", "minLength", "minItems")
    decreasing_is_stricter = ("maximum", "exclusiveMaximum", "maxLength", "maxItems")
    for keyword in (*increasing_is_stricter, *decreasing_is_stricter):
        _compare_ordered_constraint(before, after, pointer, keyword, changes)


def _compare_ordered_constraint(
    before: JsonObject,
    after: JsonObject,
    pointer: str,
    keyword: str,
    changes: list[ContractChange],
) -> None:
    old = before.get(keyword)
    new = after.get(keyword)
    if old == new:
        return
    location = _join(pointer, keyword)
    if old is not None and new is not None and not (
        isinstance(old, int | float) and isinstance(new, int | float)
    ):
        raise SchemaDiffError(f"{location} deve usar restricoes numericas comparaveis")
    changes.append(
        ContractChange(
            "constraint-changed",
            Compatibility.BREAKING,
            location,
            f"A restricao {keyword!r} mudou.",
        )
    )


def _compare_exact_keywords(
    before: JsonObject,
    after: JsonObject,
    pointer: str,
    changes: list[ContractChange],
) -> None:
    for keyword in ("$ref", "const", "pattern", "format", "oneOf", "anyOf", "allOf", "not"):
        if before.get(keyword) == after.get(keyword):
            continue
        changes.append(
            ContractChange(
                f"{keyword.lstrip('$').lower()}-changed",
                Compatibility.BREAKING,
                _join(pointer, keyword),
                f"A palavra-chave contratual {keyword!r} mudou.",
            )
        )


def _compare_nested_schema(
    before: object,
    after: object,
    pointer: str,
    keyword: str,
    changes: list[ContractChange],
) -> None:
    location = _join(pointer, keyword)
    if before is None or after is None:
        changes.append(
            ContractChange(
                f"{keyword}-changed",
                Compatibility.ADDITIVE if after is None else Compatibility.BREAKING,
                location,
                f"A definicao de {keyword!r} mudou.",
            )
        )
        return
    _compare_schema(
        _object(before, f"{location} baseline"),
        _object(after, f"{location} candidate"),
        location,
        changes,
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


def _types(value: object, label: str) -> frozenset[str] | None:
    if value is None:
        return None
    if isinstance(value, str):
        return frozenset((value,))
    if isinstance(value, list):
        items = cast(list[object], value)
        if all(isinstance(item, str) for item in items):
            return frozenset(cast(list[str], items))
    raise SchemaDiffError(f"{label} deve ser texto ou lista de textos")


def _enum_values(value: object, label: str) -> frozenset[str] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise SchemaDiffError(f"{label} deve ser uma lista")
    return frozenset(repr(item) for item in cast(list[object], value))


def _required(value: object, label: str) -> frozenset[str]:
    if value is None:
        return frozenset()
    if not isinstance(value, list):
        raise SchemaDiffError(f"{label} deve ser uma lista de textos")
    items = cast(list[object], value)
    if not all(isinstance(item, str) for item in items):
        raise SchemaDiffError(f"{label} deve ser uma lista de textos")
    return frozenset(cast(list[str], items))


def _join(pointer: str, *tokens: str) -> str:
    suffix = "/".join(token.replace("~", "~0").replace("/", "~1") for token in tokens)
    return f"{pointer}/{suffix}" if pointer else f"/{suffix}"
