"""Named refusals for the decide phase.

The persistence seam owns these translations because it is the layer that knows *why* a
decision cannot be recorded: the revision does not exist, no trusted verifier is
installed, a previous decision conflicts, or the fixture path was used outside the
dedicated legacy import.

Naming a refusal promotes no capability. A decision claiming human authority is still
verified in the same transaction that persists it, and none of these four refusals
writes anything.
"""

from __future__ import annotations

from evidrun.contracts.triage import (
    TriageError,
    TriageErrorCode,
    TriagePhase,
    TriageRejected,
)

__all__ = [
    "decide_decision_conflict",
    "decide_human_authority_unavailable",
    "decide_repository_fixture_forbidden",
    "decide_revision_not_found",
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
            phase=TriagePhase.DECIDE,
            code=code,
            message=message,
            field_path=field_path,
            remediation=remediation,
        )
    )


def decide_human_authority_unavailable() -> TriageRejected:
    return _rejected(
        TriageErrorCode.DECIDE_HUMAN_AUTHORITY_UNAVAILABLE,
        "Não existe autenticador humano confiável instalado para concluir esta decisão.",
        remediation="Instale um verificador confiável; nada foi persistido.",
    )


def decide_revision_not_found() -> TriageRejected:
    return _rejected(
        TriageErrorCode.DECIDE_REVISION_NOT_FOUND,
        "A revision informada não existe ou não corresponde ao digest referenciado.",
        field_path=("revision_ref",),
        remediation="Registre a revision exata antes de decidir sobre ela.",
    )


def decide_decision_conflict() -> TriageRejected:
    return _rejected(
        TriageErrorCode.DECIDE_DECISION_CONFLICT,
        "A revision já possui uma decisão anterior conflitante.",
        field_path=("decision",),
        remediation="Decisões são append-only; somente accepted pode virar superseded.",
    )


def decide_repository_fixture_forbidden() -> TriageRejected:
    return _rejected(
        TriageErrorCode.DECIDE_REPOSITORY_FIXTURE_FORBIDDEN,
        "A aceitação por fixture de repositório não é autoridade humana.",
        field_path=("authority",),
        remediation="Use o import dedicado do pacote legado; fixture nunca aceita por API ou CLI.",
    )
