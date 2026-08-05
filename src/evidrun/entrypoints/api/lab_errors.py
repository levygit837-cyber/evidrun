"""Tradução das recusas de persistência do Lab Agent para o catálogo estável.

Vive fora dos routers porque duas rotas famílias distintas — sessão e turno — recusam pelos
mesmos códigos de store, e uma tabela copiada em dois arquivos divergiria no primeiro código
novo. A divergência apareceria como o mesmo alvo produzindo status diferente em duas rotas,
que é exatamente o que o `lab-agent-errors-v1` chama de oráculo de existência.

A tradução lê apenas o código. Nenhuma borda deriva causa do texto da mensagem.
"""

from __future__ import annotations

from fastapi import HTTPException

from evidrun.contracts.lab_agent.errors import (
    HTTP_STATUS_BY_CODE,
    LabAgentError,
    LabAgentErrorCode,
    LabAgentStage,
    LabAgentTargetSituation,
    target_not_visible,
)
from evidrun.contracts.scope import HTTP_STATUS_BY_CODE as SCOPE_HTTP_STATUS_BY_CODE
from evidrun.infrastructure.database.lab_errors import LabStoreRejected
from evidrun.infrastructure.database.scope_errors import ScopeStorageUnavailable

__all__ = [
    "invalid_session_scope",
    "lab_http_error",
    "lab_store_error",
    "storage_http_error",
]

#: Os quatro códigos que `infrastructure/database/lab_errors.py` sabe levantar.
_CODE_BY_STORE_CODE = {
    "lab.target_not_visible": LabAgentErrorCode.SCOPE_TARGET_NOT_VISIBLE,
    "lab.scope_invalid": LabAgentErrorCode.SCHEMA_ARGUMENT_SET_INVALID,
    "lab.message_role_invalid": LabAgentErrorCode.SCHEMA_ARGUMENT_TYPE_INVALID,
    "lab.tool_trace_invalid": LabAgentErrorCode.SCHEMA_ARGUMENT_SET_INVALID,
}

_EDGE_MESSAGES = {
    LabAgentErrorCode.SCHEMA_ARGUMENT_SET_INVALID: (
        "O documento enviado não corresponde a uma das três formas válidas de sessão.",
        "Declare focus_kind e focus_id juntos, e project_id junto com foco.",
    ),
    LabAgentErrorCode.SCHEMA_ARGUMENT_TYPE_INVALID: (
        "Um campo enviado está fora do vocabulário fechado.",
        "Use apenas um valor pertencente ao vocabulário declarado do campo.",
    ),
}


def lab_store_error(rejection: LabStoreRejected) -> LabAgentError:
    """Converte a recusa do store no erro do catálogo, sem inventar código."""

    code = _CODE_BY_STORE_CODE.get(rejection.error.code)
    if code is None:
        # Sem fallback: um código novo do store viraria 500 silencioso, e a borda passaria a
        # esconder recusa que o consumidor poderia corrigir. Falhar nomeando o código deixa o
        # defeito legível no log em vez de virar erro genérico de servidor.
        raise ValueError(
            f"store refusal code without a declared translation: {rejection.error.code}"
        )
    field_path = () if rejection.error.field is None else (rejection.error.field,)
    if code is LabAgentErrorCode.SCOPE_TARGET_NOT_VISIBLE:
        # `situation` é exigida para provar classificação e descartada pelo construtor. O store
        # já colapsou as três situações de propósito, e a borda não pode reclassificar sem
        # consultar existência — que é a consulta que o contrato proíbe.
        return target_not_visible(LabAgentTargetSituation.ABSENT, field_path=field_path)
    return _edge_error(code, field_path=field_path)


def invalid_session_scope() -> LabAgentError:
    """A recusa de combinação impossível de scope, antes de qualquer linha ser lida.

    Não é `scope.focus_mismatch`: aquele código é categoria `not_found` para preservar a
    indistinguibilidade de alvo, e devolveria 404 para um corpo malformado. Combinação
    inválida é defeito estrutural do documento, que o cliente corrige.
    """

    return _edge_error(LabAgentErrorCode.SCHEMA_ARGUMENT_SET_INVALID)


def lab_http_error(error: LabAgentError) -> HTTPException:
    """O status vem da tabela por categoria; o corpo é o próprio erro serializado."""

    return HTTPException(
        status_code=HTTP_STATUS_BY_CODE[error.code],
        detail=error.model_dump(mode="json"),
    )


def storage_http_error(exc: ScopeStorageUnavailable) -> HTTPException:
    """Indisponibilidade de storage não é recusa do Lab Agent.

    Ela pertence ao catálogo de escopo e traduz por `ScopeErrorCode`, com `503`. Mapeá-la para
    um código do Lab Agent afirmaria que a chamada foi recusada por escopo, budget ou schema —
    e o caller pararia de tentar uma operação que só está temporariamente indisponível.
    """

    return HTTPException(
        status_code=SCOPE_HTTP_STATUS_BY_CODE[exc.error.code],
        detail=exc.error.model_dump(mode="json"),
    )


def _edge_error(
    code: LabAgentErrorCode, *, field_path: tuple[str, ...] = ()
) -> LabAgentError:
    """Texto próprio da borda HTTP.

    `lab.turn.refusal_error` não serve aqui: as mensagens dele são endereçadas ao modelo e
    falam de tool e de schema de tool. Na borda HTTP o leitor é o cliente, e mencionar tool
    numa criação de sessão descreveria uma causa que não existe.
    """

    message, remediation = _EDGE_MESSAGES[code]
    return LabAgentError(
        stage=LabAgentStage.SCHEMA,
        code=code,
        message=message,
        remediation=remediation,
        field_path=field_path,
    )
