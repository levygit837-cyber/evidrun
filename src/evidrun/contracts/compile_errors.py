"""Named refusals for the compile phase.

The compiler and the execution-preparation seam own these translations because they
are the layers that know *why* a reference failed: absent, digest drift, or a
dependency without human acceptance. Borders never re-derive a cause from a message.
"""

from __future__ import annotations

from evidrun.contracts.base import ContractRef
from evidrun.contracts.triage import (
    TriageError,
    TriageErrorCode,
    TriagePhase,
    TriageRejected,
)


def _rejected(
    code: TriageErrorCode,
    message: str,
    *,
    field_path: tuple[str, ...] = (),
    remediation: str | None = None,
) -> TriageRejected:
    return TriageRejected(
        TriageError(
            phase=TriagePhase.COMPILE,
            code=code,
            message=message,
            field_path=field_path,
            remediation=remediation,
        )
    )


def _identity(reference: ContractRef) -> str:
    return f"{reference.logical_id}@{reference.revision}"


def compile_revision_not_found(identity: str) -> TriageRejected:
    return _rejected(
        TriageErrorCode.COMPILE_REVISION_NOT_FOUND,
        f"A revision informada não existe: {identity}.",
        remediation="Registre a revision antes de compilar.",
    )


def compile_reference_not_found(reference: ContractRef) -> TriageRejected:
    return _rejected(
        TriageErrorCode.COMPILE_REVISION_NOT_FOUND,
        f"Uma dependência da Study não existe: {_identity(reference)}.",
        remediation="Registre a revision referenciada antes de compilar.",
    )


def compile_revision_not_study(found: str) -> TriageRejected:
    return _rejected(
        TriageErrorCode.COMPILE_REVISION_NOT_STUDY,
        f"A revision informada não é uma Study; o tipo encontrado foi {found}.",
        remediation="Compile a revision de uma Study.",
    )


def compile_dependency_not_accepted(reference: ContractRef) -> TriageRejected:
    return _rejected(
        TriageErrorCode.COMPILE_DEPENDENCY_NOT_ACCEPTED,
        f"A dependência {_identity(reference)} não possui aceitação humana.",
        remediation="Aceite a revision referenciada ou compile pelo caminho não verificado.",
    )


def compile_digest_mismatch(reference: ContractRef) -> TriageRejected:
    return _rejected(
        TriageErrorCode.COMPILE_DIGEST_MISMATCH,
        f"A dependência {_identity(reference)} tem digest divergente do referenciado.",
        remediation="Referencie o digest exato da revision registrada.",
    )


def compile_controlled_slots_mismatch(
    expected: str, observed: tuple[str, ...]
) -> TriageRejected:
    rendered = ", ".join(observed) or "nenhum"
    return _rejected(
        TriageErrorCode.COMPILE_CONTROLLED_SLOTS_MISMATCH,
        "Uma comparação controlada deve alterar exatamente sua variável primária; "
        f"esperado {expected}, observados {rendered}.",
        remediation="Isole a variável primária ou declare a comparação como exploratória.",
    )


def compile_confounder_missing(slots: tuple[str, ...]) -> TriageRejected:
    rendered = ", ".join(slots)
    return _rejected(
        TriageErrorCode.COMPILE_CONFOUNDER_MISSING,
        "Um estudo exploratório deve declarar confounders para as diferenças "
        f"adicionais: {rendered}.",
        remediation="Declare um confounder para cada slot adicional alterado.",
    )
