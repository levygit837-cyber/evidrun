"""Recusas estáveis na fronteira de persistência do Lab Agent."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LabStoreError:
    code: str
    message: str
    field: str | None = None


class LabStoreRejected(Exception):
    def __init__(self, code: str, message: str, *, field: str | None = None) -> None:
        self.error = LabStoreError(code=code, message=message, field=field)
        super().__init__(code)


class LabSessionMigrationError(RuntimeError):
    """O scope legado exige decisão de operador antes da migração."""


def invalid_scope(message: str, *, field: str | None = None) -> LabStoreRejected:
    return LabStoreRejected("lab.scope_invalid", message, field=field)


def not_visible() -> LabStoreRejected:
    return LabStoreRejected(
        "lab.target_not_visible",
        "O alvo não existe ou não está visível neste escopo.",
    )


def invalid_message_role() -> LabStoreRejected:
    return LabStoreRejected(
        "lab.message_role_invalid",
        "O papel da mensagem não pertence ao vocabulário fechado.",
        field="role",
    )


def invalid_trace(message: str, *, field: str | None = None) -> LabStoreRejected:
    return LabStoreRejected("lab.tool_trace_invalid", message, field=field)
