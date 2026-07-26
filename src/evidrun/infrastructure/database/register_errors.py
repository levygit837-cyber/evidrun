"""Stable register-phase refusals at the persistence seam."""

from __future__ import annotations

from evidrun.contracts.triage import TriageError, TriageErrorCode, TriagePhase


class RegisterRejected(Exception):
    """A register request that persistence refused with a public safe error."""

    def __init__(self, error: TriageError) -> None:
        super().__init__(error.code.value)
        self.error = error


class RegisterStorageUnavailable(Exception):
    """A storage failure whose infrastructure detail must remain private."""

    def __init__(self) -> None:
        self.error = TriageError(
            phase=TriagePhase.REGISTER,
            code=TriageErrorCode.REGISTER_STORAGE_UNAVAILABLE,
            message="O storage de registro está temporariamente indisponível.",
            remediation="Tente registrar a revision novamente mais tarde.",
        )
        super().__init__(self.error.code.value)


def project_not_found() -> RegisterRejected:
    return RegisterRejected(
        TriageError(
            phase=TriagePhase.REGISTER,
            code=TriageErrorCode.REGISTER_PROJECT_NOT_FOUND,
            message="O Project informado não existe.",
            field_path=("project_id",),
            remediation="Crie o Project antes de registrar a revision.",
        )
    )


def revision_not_monotonic(*, expected: int, received: int) -> RegisterRejected:
    return RegisterRejected(
        TriageError(
            phase=TriagePhase.REGISTER,
            code=TriageErrorCode.REGISTER_REVISION_NOT_MONOTONIC,
            message=(
                "A revision não segue a sequência monotônica: "
                f"esperada {expected}, recebida {received}."
            ),
            field_path=("revision",),
            remediation=f"Registre a revision {expected} antes da revision {received}.",
        )
    )


def immutability_conflict() -> RegisterRejected:
    return RegisterRejected(
        TriageError(
            phase=TriagePhase.REGISTER,
            code=TriageErrorCode.REGISTER_IMMUTABILITY_CONFLICT,
            message="A identidade da revision já existe com conteúdo diferente.",
            remediation="Use uma nova revision para registrar conteúdo diferente.",
        )
    )


def initial_status_invalid() -> RegisterRejected:
    return RegisterRejected(
        TriageError(
            phase=TriagePhase.REGISTER,
            code=TriageErrorCode.REGISTER_INITIAL_STATUS_INVALID,
            message="O status inicial da revision é inválido.",
            field_path=("status",),
            remediation="Use draft ou proposed como status inicial.",
        )
    )
