"""TOML reading primitives shared by the contract model and the merge gate.

Every helper collects into one `errors` list instead of raising, so a malformed contract
reports all of its problems at once rather than one per run. They are the only place that
knows how a value is spelled in TOML; the models above them work with typed data.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import PurePosixPath
from typing import cast

type Table = dict[str, object]

__all__ = [
    "Table",
    "read_enum",
    "read_optional_text",
    "read_patterns",
    "read_positive_int",
    "read_table",
    "read_table_list",
    "read_text",
    "read_text_tuple",
]


def read_table(value: object, name: str, errors: list[str]) -> Table | None:
    if not isinstance(value, dict):
        errors.append(f"[{name}] e obrigatorio")
        return None
    return cast(Table, value)


def read_table_list(value: object, name: str, errors: list[str]) -> list[Table]:
    if not isinstance(value, list):
        errors.append(f"{name} deve ser uma lista de tabelas")
        return []
    items = cast(list[object], value)
    if any(not isinstance(item, dict) for item in items):
        errors.append(f"{name} deve ser uma lista de tabelas")
        return []
    return cast(list[Table], value)


def read_text(source: Table, key: str, errors: list[str], *, prefix: str = "") -> str | None:
    value = source.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{prefix}{key} deve ser texto nao vazio")
        return None
    return value.strip()


def read_optional_text(
    source: Table, key: str, errors: list[str], *, prefix: str = ""
) -> str | None:
    value = source.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{prefix}{key} deve ser texto nao vazio quando presente")
        return None
    return value.strip()


def read_positive_int(source: Table, key: str, errors: list[str]) -> int | None:
    value = source.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        errors.append(f"{key} deve ser inteiro positivo")
        return None
    return value


def read_enum[EnumValue: StrEnum](
    source: Table,
    key: str,
    enum_type: type[EnumValue],
    errors: list[str],
    *,
    prefix: str = "",
) -> EnumValue | None:
    value = source.get(key)
    try:
        return enum_type(value)
    except (ValueError, TypeError):
        choices = ", ".join(item.value for item in enum_type)
        errors.append(f"{prefix}{key} deve ser um de: {choices}")
        return None


def read_text_tuple(
    source: Table,
    key: str,
    errors: list[str],
    *,
    prefix: str = "",
    nonempty: bool = False,
) -> tuple[str, ...]:
    value = source.get(key, [])
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


def read_patterns(
    source: Table,
    key: str,
    errors: list[str],
    *,
    prefix: str = "",
    nonempty: bool = False,
) -> tuple[str, ...]:
    values = read_text_tuple(source, key, errors, prefix=prefix, nonempty=nonempty)
    for pattern in values:
        pure = PurePosixPath(pattern)
        if pure.is_absolute() or ".." in pure.parts or "\\" in pattern:
            errors.append(f"{prefix}{key} contem pattern inseguro: {pattern}")
    return values
