"""Named refusals for the enqueue phase.

The persistence seam owns these translations because it is the layer that knows *why*
a request cannot become a Run: absent identity, an admission that does not admit this
exact RunSpec, digest drift, a reused idempotency key, or one of the four retry rules.

Borders never re-derive a cause from a message. Before this module the API chose 409
versus 422 by searching for phrases such as `"idempotency key"` inside the exception
text, so rewording a message silently changed an observable status.
"""

from __future__ import annotations

from evidrun.contracts.triage import (
    TriageError,
    TriageErrorCode,
    TriagePhase,
    TriageRejected,
)

__all__ = [
    "enqueue_admission_not_admitted",
    "enqueue_admission_not_found",
    "enqueue_admission_run_spec_mismatch",
    "enqueue_digest_mismatch",
    "enqueue_idempotency_conflict",
    "enqueue_idempotency_key_empty",
    "enqueue_retry_admission_not_newer",
    "enqueue_retry_admission_reused",
    "enqueue_retry_legacy_run",
    "enqueue_retry_source_succeeded",
    "enqueue_run_spec_not_found",
]


def _rejected(
    code: TriageErrorCode,
    message: str,
    *,
    field_path: tuple[str, ...] = (),
    remediation: str | None = None,
) -> TriageRejected:
    return TriageRejected(
        TriageError(
            phase=TriagePhase.ENQUEUE,
            code=code,
            message=message,
            field_path=field_path,
            remediation=remediation,
        )
    )


def enqueue_run_spec_not_found() -> TriageRejected:
    return _rejected(
        TriageErrorCode.ENQUEUE_RUN_SPEC_NOT_FOUND,
        "O RunSpec informado não existe.",
        field_path=("run_spec_id",),
        remediation="Compile a Study para obter um RunSpec válido.",
    )


def enqueue_admission_not_found() -> TriageRejected:
    return _rejected(
        TriageErrorCode.ENQUEUE_ADMISSION_NOT_FOUND,
        "O AdmissionRecord informado não existe.",
        field_path=("admission_id",),
        remediation="Solicite a admissão do RunSpec antes de enfileirar.",
    )


def enqueue_admission_not_admitted() -> TriageRejected:
    return _rejected(
        TriageErrorCode.ENQUEUE_ADMISSION_NOT_ADMITTED,
        "O AdmissionRecord informado não admitiu a execução.",
        field_path=("admission_id",),
        remediation="Corrija os achados e solicite uma nova admissão.",
    )


def enqueue_admission_run_spec_mismatch() -> TriageRejected:
    return _rejected(
        TriageErrorCode.ENQUEUE_ADMISSION_RUN_SPEC_MISMATCH,
        "O AdmissionRecord informado pertence a outro RunSpec.",
        field_path=("admission_id",),
        remediation="Use a admissão emitida para este RunSpec exato.",
    )


def enqueue_digest_mismatch() -> TriageRejected:
    return _rejected(
        TriageErrorCode.ENQUEUE_DIGEST_MISMATCH,
        "Os contratos persistidos não reproduzem seus digests declarados.",
        remediation="Recompile o RunSpec; não reutilize registros divergentes.",
    )


def enqueue_idempotency_key_empty() -> TriageRejected:
    return _rejected(
        TriageErrorCode.ENQUEUE_IDEMPOTENCY_KEY_EMPTY,
        "A chave de idempotência não pode ser vazia.",
        field_path=("idempotency_key",),
        remediation="Informe uma chave estável para este pedido.",
    )


def enqueue_idempotency_conflict() -> TriageRejected:
    return _rejected(
        TriageErrorCode.ENQUEUE_IDEMPOTENCY_CONFLICT,
        "A chave de idempotência já foi usada para outro pedido.",
        field_path=("idempotency_key",),
        remediation="Use uma chave nova para um pedido diferente.",
    )


def enqueue_retry_source_succeeded() -> TriageRejected:
    return _rejected(
        TriageErrorCode.ENQUEUE_RETRY_SOURCE_SUCCEEDED,
        "Somente uma Run terminal sem sucesso pode ser repetida.",
        field_path=("retry_of",),
        remediation="Repita apenas Runs failed, cancelled, budget_exhausted ou guardrail_stopped.",
    )


def enqueue_retry_admission_reused() -> TriageRejected:
    return _rejected(
        TriageErrorCode.ENQUEUE_RETRY_ADMISSION_REUSED,
        "Um retry exige um AdmissionRecord novo, não o da Run de origem.",
        field_path=("admission_id",),
        remediation="Solicite uma nova admissão antes de repetir a Run.",
    )


def enqueue_retry_admission_not_newer() -> TriageRejected:
    return _rejected(
        TriageErrorCode.ENQUEUE_RETRY_ADMISSION_NOT_NEWER,
        "O AdmissionRecord do retry precisa ser criado após o terminal da Run de origem.",
        field_path=("admission_id",),
        remediation="Solicite a admissão depois que a Run de origem terminar.",
    )


def enqueue_retry_legacy_run() -> TriageRejected:
    return _rejected(
        TriageErrorCode.ENQUEUE_RETRY_LEGACY_RUN,
        "Uma Run legada sem RunSpec não é elegível para retry do Runtime Kernel.",
        field_path=("retry_of",),
        remediation="Compile e admita um RunSpec para executar esta investigação novamente.",
    )
