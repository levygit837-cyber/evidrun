"""Stable refusals for Workspace and Project persistence operations."""

from __future__ import annotations

from evidrun.contracts.scope import ScopeError, ScopeErrorCode


class ScopeRejected(Exception):
    def __init__(self, error: ScopeError) -> None:
        super().__init__(error.code.value)
        self.error = error


class ScopeStorageUnavailable(Exception):
    def __init__(self) -> None:
        self.error = ScopeError(
            code=ScopeErrorCode.STORAGE_UNAVAILABLE,
            message="O storage de Workspace e Project está temporariamente indisponível.",
            remediation="Tente a operação novamente mais tarde.",
        )
        super().__init__(self.error.code.value)


def workspace_name_invalid() -> ScopeRejected:
    return ScopeRejected(
        ScopeError(
            code=ScopeErrorCode.WORKSPACE_NAME_INVALID,
            message="O nome do Workspace precisa conter algum caractere significativo.",
            field_path=("name",),
            remediation="Informe um nome não vazio.",
        )
    )


def workspace_name_conflict() -> ScopeRejected:
    return ScopeRejected(
        ScopeError(
            code=ScopeErrorCode.WORKSPACE_NAME_CONFLICT,
            message="Já existe um Workspace com nome equivalente.",
            field_path=("name",),
            remediation="Escolha um nome diferente.",
        )
    )


def project_name_invalid() -> ScopeRejected:
    return ScopeRejected(
        ScopeError(
            code=ScopeErrorCode.PROJECT_NAME_INVALID,
            message="O nome do Project precisa conter algum caractere significativo.",
            field_path=("name",),
            remediation="Informe um nome não vazio.",
        )
    )


def project_name_conflict() -> ScopeRejected:
    return ScopeRejected(
        ScopeError(
            code=ScopeErrorCode.PROJECT_NAME_CONFLICT,
            message="Já existe um Project com nome equivalente neste Workspace.",
            field_path=("name",),
            remediation="Escolha um nome diferente neste Workspace.",
        )
    )


def project_workspace_not_found() -> ScopeRejected:
    return ScopeRejected(
        ScopeError(
            code=ScopeErrorCode.PROJECT_WORKSPACE_NOT_FOUND,
            message="O Workspace informado não existe.",
            field_path=("workspace_id",),
            remediation="Crie ou selecione um Workspace existente.",
        )
    )
