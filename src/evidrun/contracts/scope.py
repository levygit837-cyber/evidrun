from __future__ import annotations

import unicodedata
from collections.abc import Mapping
from enum import IntEnum, StrEnum
from types import MappingProxyType
from typing import Any, NamedTuple

from pydantic import computed_field

from evidrun.contracts.base import ContractModel, NonEmptyStr


class NormalizedScopeName(NamedTuple):
    name: str
    name_key: str


def normalize_scope_name(value: str) -> NormalizedScopeName:
    """Return the display form and canonical identity used by every scope surface."""

    name = " ".join(unicodedata.normalize("NFKC", value).split())
    if not name:
        raise ValueError("scope name must not be empty after normalization")
    return NormalizedScopeName(name=name, name_key=name.casefold())


class ScopeErrorCode(StrEnum):
    WORKSPACE_NAME_INVALID = "workspace.name_invalid"
    WORKSPACE_NAME_CONFLICT = "workspace.name_conflict"
    PROJECT_NAME_INVALID = "project.name_invalid"
    PROJECT_NAME_CONFLICT = "project.name_conflict"
    PROJECT_WORKSPACE_NOT_FOUND = "project.workspace_not_found"
    STORAGE_UNAVAILABLE = "scope.storage_unavailable"


class ScopeErrorCategory(StrEnum):
    INVALID = "invalid"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    UNAVAILABLE = "unavailable"


class ScopeCliExitCode(IntEnum):
    INVALID = 2
    UNAVAILABLE = 3
    NOT_FOUND = 4
    CONFLICT = 5


class ScopeError(ContractModel):
    code: ScopeErrorCode
    message: NonEmptyStr
    field_path: tuple[NonEmptyStr, ...] = ()
    remediation: NonEmptyStr | None = None

    @computed_field
    @property
    def category(self) -> ScopeErrorCategory:
        return CATEGORY_BY_CODE[self.code]


CATEGORY_BY_CODE: Mapping[ScopeErrorCode, ScopeErrorCategory] = MappingProxyType(
    {
        ScopeErrorCode.WORKSPACE_NAME_INVALID: ScopeErrorCategory.INVALID,
        ScopeErrorCode.WORKSPACE_NAME_CONFLICT: ScopeErrorCategory.CONFLICT,
        ScopeErrorCode.PROJECT_NAME_INVALID: ScopeErrorCategory.INVALID,
        ScopeErrorCode.PROJECT_NAME_CONFLICT: ScopeErrorCategory.CONFLICT,
        ScopeErrorCode.PROJECT_WORKSPACE_NOT_FOUND: ScopeErrorCategory.NOT_FOUND,
        ScopeErrorCode.STORAGE_UNAVAILABLE: ScopeErrorCategory.UNAVAILABLE,
    }
)

HTTP_STATUS_BY_CODE: Mapping[ScopeErrorCode, int] = MappingProxyType(
    {
        ScopeErrorCode.WORKSPACE_NAME_INVALID: 422,
        ScopeErrorCode.WORKSPACE_NAME_CONFLICT: 409,
        ScopeErrorCode.PROJECT_NAME_INVALID: 422,
        ScopeErrorCode.PROJECT_NAME_CONFLICT: 409,
        ScopeErrorCode.PROJECT_WORKSPACE_NOT_FOUND: 404,
        ScopeErrorCode.STORAGE_UNAVAILABLE: 503,
    }
)

CLI_EXIT_BY_CODE: Mapping[ScopeErrorCode, ScopeCliExitCode] = MappingProxyType(
    {
        ScopeErrorCode.WORKSPACE_NAME_INVALID: ScopeCliExitCode.INVALID,
        ScopeErrorCode.WORKSPACE_NAME_CONFLICT: ScopeCliExitCode.CONFLICT,
        ScopeErrorCode.PROJECT_NAME_INVALID: ScopeCliExitCode.INVALID,
        ScopeErrorCode.PROJECT_NAME_CONFLICT: ScopeCliExitCode.CONFLICT,
        ScopeErrorCode.PROJECT_WORKSPACE_NOT_FOUND: ScopeCliExitCode.NOT_FOUND,
        ScopeErrorCode.STORAGE_UNAVAILABLE: ScopeCliExitCode.UNAVAILABLE,
    }
)


def validate_scope_error_tables(
    http_status_by_code: Mapping[Any, Any] = HTTP_STATUS_BY_CODE,
    cli_exit_by_code: Mapping[Any, Any] = CLI_EXIT_BY_CODE,
) -> None:
    declared = set(ScopeErrorCode)
    for name, entries in (
        ("category table", set(CATEGORY_BY_CODE)),
        ("HTTP status table", set(http_status_by_code)),
        ("CLI exit table", set(cli_exit_by_code)),
    ):
        missing = declared - entries
        orphaned = entries - declared
        if missing or orphaned:
            raise ValueError(
                f"{name} must match declared scope codes; "
                f"missing={sorted(str(item) for item in missing)}, "
                f"orphaned={sorted(str(item) for item in orphaned)}"
            )


validate_scope_error_tables()
