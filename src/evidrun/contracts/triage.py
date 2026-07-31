from __future__ import annotations

from collections.abc import Mapping
from enum import IntEnum, StrEnum
from types import MappingProxyType
from typing import Any

from pydantic import Field, computed_field, model_validator

from evidrun.contracts.base import CapabilityDescriptorRef, ContractModel, NonEmptyStr
from evidrun.contracts.runtime.spec import AdmissionIssue


class TriagePhase(StrEnum):
    PARSE = "parse"
    REGISTER = "register"
    DECIDE = "decide"
    COMPILE = "compile"
    ADMIT = "admit"
    ENQUEUE = "enqueue"


class TriageErrorCode(StrEnum):
    PARSE_DOCUMENT_NOT_OBJECT = "parse.document_not_object"
    PARSE_CONTRACT_TYPE_MISSING = "parse.contract_type_missing"
    PARSE_CONTRACT_TYPE_UNKNOWN = "parse.contract_type_unknown"
    PARSE_FIELD_UNDECLARED = "parse.field_undeclared"
    PARSE_REVISION_INVALID = "parse.revision_invalid"
    PARSE_IDENTIFIER_EMPTY = "parse.identifier_empty"
    PARSE_PAYLOAD_TYPE_INVALID = "parse.payload_type_invalid"
    PARSE_SCHEMA_INVALID = "parse.schema_invalid"

    REGISTER_PROJECT_NOT_FOUND = "register.project_not_found"
    REGISTER_REVISION_NOT_MONOTONIC = "register.revision_not_monotonic"
    REGISTER_IMMUTABILITY_CONFLICT = "register.immutability_conflict"
    REGISTER_INITIAL_STATUS_INVALID = "register.initial_status_invalid"
    REGISTER_STORAGE_UNAVAILABLE = "register.storage_unavailable"

    DECIDE_HUMAN_AUTHORITY_UNAVAILABLE = "decide.human_authority_unavailable"
    DECIDE_REVISION_NOT_FOUND = "decide.revision_not_found"
    DECIDE_DECISION_CONFLICT = "decide.decision_conflict"
    DECIDE_REPOSITORY_FIXTURE_FORBIDDEN = "decide.repository_fixture_forbidden"

    COMPILE_REVISION_NOT_FOUND = "compile.revision_not_found"
    COMPILE_REVISION_NOT_STUDY = "compile.revision_not_study"
    COMPILE_DEPENDENCY_NOT_ACCEPTED = "compile.dependency_not_accepted"
    COMPILE_DIGEST_MISMATCH = "compile.digest_mismatch"
    COMPILE_CONTROLLED_SLOTS_MISMATCH = "compile.controlled_slots_mismatch"
    COMPILE_CONFOUNDER_MISSING = "compile.confounder_missing"

    ADMIT_RUN_SPEC_NOT_FOUND = "admit.run_spec_not_found"
    ADMIT_REJECTED = "admit.rejected"
    ADMIT_INVENTORY_NOT_PERSISTIBLE = "admit.inventory_not_persistible"

    ENQUEUE_RUN_SPEC_NOT_FOUND = "enqueue.run_spec_not_found"
    ENQUEUE_ADMISSION_NOT_FOUND = "enqueue.admission_not_found"
    ENQUEUE_ADMISSION_NOT_ADMITTED = "enqueue.admission_not_admitted"
    ENQUEUE_ADMISSION_RUN_SPEC_MISMATCH = "enqueue.admission_run_spec_mismatch"
    ENQUEUE_DIGEST_MISMATCH = "enqueue.digest_mismatch"
    ENQUEUE_IDEMPOTENCY_KEY_EMPTY = "enqueue.idempotency_key_empty"
    ENQUEUE_IDEMPOTENCY_CONFLICT = "enqueue.idempotency_conflict"
    ENQUEUE_RETRY_SOURCE_SUCCEEDED = "enqueue.retry_source_succeeded"
    ENQUEUE_RETRY_ADMISSION_NOT_NEWER = "enqueue.retry_admission_not_newer"
    ENQUEUE_RETRY_ADMISSION_REUSED = "enqueue.retry_admission_reused"
    ENQUEUE_RETRY_LEGACY_RUN = "enqueue.retry_legacy_run"

    @property
    def phase(self) -> TriagePhase:
        prefix, _separator, _name = self.value.partition(".")
        return TriagePhase(prefix)


class TriageErrorCategory(StrEnum):
    INVALID = "invalid"
    REJECTED = "rejected"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    UNAVAILABLE = "unavailable"


class CliExitCode(IntEnum):
    INVALID = 2
    REJECTED = 3
    NOT_FOUND = 4
    CONFLICT = 5


class TriageError(ContractModel):
    phase: TriagePhase
    code: TriageErrorCode
    message: NonEmptyStr
    field_path: tuple[NonEmptyStr, ...] = ()
    remediation: NonEmptyStr | None = None
    issues: tuple[AdmissionIssue, ...] = ()
    missing_requirements: tuple[NonEmptyStr, ...] = ()
    denied_policies: tuple[NonEmptyStr, ...] = ()
    unresolved_required_capabilities: tuple[CapabilityDescriptorRef, ...] = Field(
        default=(), exclude_if=lambda capabilities: not capabilities
    )

    @computed_field
    @property
    def category(self) -> TriageErrorCategory:
        return CATEGORY_BY_CODE[self.code]

    @model_validator(mode="after")
    def validate_code_phase(self) -> TriageError:
        if self.code.phase != self.phase:
            raise ValueError("code prefix must match phase")
        return self


class TriageRejected(ValueError):
    """A named refusal produced by a triage phase before a Run exists."""

    def __init__(self, error: TriageError) -> None:
        super().__init__(error.message)
        self.error = error


CATEGORY_BY_CODE: Mapping[TriageErrorCode, TriageErrorCategory] = MappingProxyType(
    {
        TriageErrorCode.PARSE_DOCUMENT_NOT_OBJECT: TriageErrorCategory.INVALID,
        TriageErrorCode.PARSE_CONTRACT_TYPE_MISSING: TriageErrorCategory.INVALID,
        TriageErrorCode.PARSE_CONTRACT_TYPE_UNKNOWN: TriageErrorCategory.INVALID,
        TriageErrorCode.PARSE_FIELD_UNDECLARED: TriageErrorCategory.INVALID,
        TriageErrorCode.PARSE_REVISION_INVALID: TriageErrorCategory.INVALID,
        TriageErrorCode.PARSE_IDENTIFIER_EMPTY: TriageErrorCategory.INVALID,
        TriageErrorCode.PARSE_PAYLOAD_TYPE_INVALID: TriageErrorCategory.INVALID,
        TriageErrorCode.PARSE_SCHEMA_INVALID: TriageErrorCategory.INVALID,
        TriageErrorCode.REGISTER_PROJECT_NOT_FOUND: TriageErrorCategory.NOT_FOUND,
        TriageErrorCode.REGISTER_REVISION_NOT_MONOTONIC: TriageErrorCategory.CONFLICT,
        TriageErrorCode.REGISTER_IMMUTABILITY_CONFLICT: TriageErrorCategory.CONFLICT,
        TriageErrorCode.REGISTER_INITIAL_STATUS_INVALID: TriageErrorCategory.INVALID,
        TriageErrorCode.REGISTER_STORAGE_UNAVAILABLE: TriageErrorCategory.UNAVAILABLE,
        TriageErrorCode.DECIDE_HUMAN_AUTHORITY_UNAVAILABLE: TriageErrorCategory.UNAVAILABLE,
        TriageErrorCode.DECIDE_REVISION_NOT_FOUND: TriageErrorCategory.NOT_FOUND,
        TriageErrorCode.DECIDE_DECISION_CONFLICT: TriageErrorCategory.CONFLICT,
        TriageErrorCode.DECIDE_REPOSITORY_FIXTURE_FORBIDDEN: TriageErrorCategory.REJECTED,
        TriageErrorCode.COMPILE_REVISION_NOT_FOUND: TriageErrorCategory.NOT_FOUND,
        TriageErrorCode.COMPILE_REVISION_NOT_STUDY: TriageErrorCategory.INVALID,
        TriageErrorCode.COMPILE_DEPENDENCY_NOT_ACCEPTED: TriageErrorCategory.REJECTED,
        TriageErrorCode.COMPILE_DIGEST_MISMATCH: TriageErrorCategory.CONFLICT,
        TriageErrorCode.COMPILE_CONTROLLED_SLOTS_MISMATCH: TriageErrorCategory.INVALID,
        TriageErrorCode.COMPILE_CONFOUNDER_MISSING: TriageErrorCategory.INVALID,
        TriageErrorCode.ADMIT_RUN_SPEC_NOT_FOUND: TriageErrorCategory.NOT_FOUND,
        TriageErrorCode.ADMIT_REJECTED: TriageErrorCategory.REJECTED,
        TriageErrorCode.ADMIT_INVENTORY_NOT_PERSISTIBLE: TriageErrorCategory.UNAVAILABLE,
        TriageErrorCode.ENQUEUE_RUN_SPEC_NOT_FOUND: TriageErrorCategory.NOT_FOUND,
        TriageErrorCode.ENQUEUE_ADMISSION_NOT_FOUND: TriageErrorCategory.NOT_FOUND,
        TriageErrorCode.ENQUEUE_ADMISSION_NOT_ADMITTED: TriageErrorCategory.REJECTED,
        TriageErrorCode.ENQUEUE_ADMISSION_RUN_SPEC_MISMATCH: TriageErrorCategory.REJECTED,
        TriageErrorCode.ENQUEUE_DIGEST_MISMATCH: TriageErrorCategory.CONFLICT,
        TriageErrorCode.ENQUEUE_IDEMPOTENCY_KEY_EMPTY: TriageErrorCategory.INVALID,
        TriageErrorCode.ENQUEUE_IDEMPOTENCY_CONFLICT: TriageErrorCategory.CONFLICT,
        TriageErrorCode.ENQUEUE_RETRY_SOURCE_SUCCEEDED: TriageErrorCategory.CONFLICT,
        TriageErrorCode.ENQUEUE_RETRY_ADMISSION_NOT_NEWER: TriageErrorCategory.CONFLICT,
        TriageErrorCode.ENQUEUE_RETRY_ADMISSION_REUSED: TriageErrorCategory.CONFLICT,
        TriageErrorCode.ENQUEUE_RETRY_LEGACY_RUN: TriageErrorCategory.CONFLICT,
    }
)

HTTP_STATUS_BY_CATEGORY: Mapping[TriageErrorCategory, int] = MappingProxyType(
    {
        TriageErrorCategory.INVALID: 422,
        TriageErrorCategory.REJECTED: 422,
        TriageErrorCategory.NOT_FOUND: 404,
        TriageErrorCategory.CONFLICT: 409,
        TriageErrorCategory.UNAVAILABLE: 503,
    }
)

HTTP_STATUS_BY_CODE: Mapping[TriageErrorCode, int] = MappingProxyType(
    {code: HTTP_STATUS_BY_CATEGORY[category] for code, category in CATEGORY_BY_CODE.items()}
)
CLI_EXIT_BY_CODE: Mapping[TriageErrorCode, CliExitCode] = MappingProxyType(
    {
        TriageErrorCode.PARSE_DOCUMENT_NOT_OBJECT: CliExitCode.INVALID,
        TriageErrorCode.PARSE_CONTRACT_TYPE_MISSING: CliExitCode.INVALID,
        TriageErrorCode.PARSE_CONTRACT_TYPE_UNKNOWN: CliExitCode.INVALID,
        TriageErrorCode.PARSE_FIELD_UNDECLARED: CliExitCode.INVALID,
        TriageErrorCode.PARSE_REVISION_INVALID: CliExitCode.INVALID,
        TriageErrorCode.PARSE_IDENTIFIER_EMPTY: CliExitCode.INVALID,
        TriageErrorCode.PARSE_PAYLOAD_TYPE_INVALID: CliExitCode.INVALID,
        TriageErrorCode.PARSE_SCHEMA_INVALID: CliExitCode.INVALID,
        TriageErrorCode.REGISTER_PROJECT_NOT_FOUND: CliExitCode.NOT_FOUND,
        TriageErrorCode.REGISTER_REVISION_NOT_MONOTONIC: CliExitCode.CONFLICT,
        TriageErrorCode.REGISTER_IMMUTABILITY_CONFLICT: CliExitCode.CONFLICT,
        TriageErrorCode.REGISTER_INITIAL_STATUS_INVALID: CliExitCode.INVALID,
        TriageErrorCode.REGISTER_STORAGE_UNAVAILABLE: CliExitCode.REJECTED,
        TriageErrorCode.DECIDE_HUMAN_AUTHORITY_UNAVAILABLE: CliExitCode.REJECTED,
        TriageErrorCode.DECIDE_REVISION_NOT_FOUND: CliExitCode.NOT_FOUND,
        TriageErrorCode.DECIDE_DECISION_CONFLICT: CliExitCode.CONFLICT,
        TriageErrorCode.DECIDE_REPOSITORY_FIXTURE_FORBIDDEN: CliExitCode.REJECTED,
        TriageErrorCode.COMPILE_REVISION_NOT_FOUND: CliExitCode.NOT_FOUND,
        TriageErrorCode.COMPILE_REVISION_NOT_STUDY: CliExitCode.INVALID,
        TriageErrorCode.COMPILE_DEPENDENCY_NOT_ACCEPTED: CliExitCode.REJECTED,
        TriageErrorCode.COMPILE_DIGEST_MISMATCH: CliExitCode.CONFLICT,
        TriageErrorCode.COMPILE_CONTROLLED_SLOTS_MISMATCH: CliExitCode.INVALID,
        TriageErrorCode.COMPILE_CONFOUNDER_MISSING: CliExitCode.INVALID,
        TriageErrorCode.ADMIT_RUN_SPEC_NOT_FOUND: CliExitCode.NOT_FOUND,
        TriageErrorCode.ADMIT_REJECTED: CliExitCode.REJECTED,
        TriageErrorCode.ADMIT_INVENTORY_NOT_PERSISTIBLE: CliExitCode.REJECTED,
        TriageErrorCode.ENQUEUE_RUN_SPEC_NOT_FOUND: CliExitCode.NOT_FOUND,
        TriageErrorCode.ENQUEUE_ADMISSION_NOT_FOUND: CliExitCode.NOT_FOUND,
        TriageErrorCode.ENQUEUE_ADMISSION_NOT_ADMITTED: CliExitCode.REJECTED,
        TriageErrorCode.ENQUEUE_ADMISSION_RUN_SPEC_MISMATCH: CliExitCode.REJECTED,
        TriageErrorCode.ENQUEUE_DIGEST_MISMATCH: CliExitCode.CONFLICT,
        TriageErrorCode.ENQUEUE_IDEMPOTENCY_KEY_EMPTY: CliExitCode.INVALID,
        TriageErrorCode.ENQUEUE_IDEMPOTENCY_CONFLICT: CliExitCode.CONFLICT,
        TriageErrorCode.ENQUEUE_RETRY_SOURCE_SUCCEEDED: CliExitCode.CONFLICT,
        TriageErrorCode.ENQUEUE_RETRY_ADMISSION_NOT_NEWER: CliExitCode.CONFLICT,
        TriageErrorCode.ENQUEUE_RETRY_ADMISSION_REUSED: CliExitCode.CONFLICT,
        TriageErrorCode.ENQUEUE_RETRY_LEGACY_RUN: CliExitCode.CONFLICT,
    }
)


def validate_error_tables(
    http_status_by_code: Mapping[Any, Any] = HTTP_STATUS_BY_CODE,
    cli_exit_by_code: Mapping[Any, Any] = CLI_EXIT_BY_CODE,
) -> None:
    declared = set(TriageErrorCode)
    tables = (
        ("category table", set(CATEGORY_BY_CODE)),
        ("HTTP status table", set(http_status_by_code)),
        ("CLI exit table", set(cli_exit_by_code)),
    )
    for name, entries in tables:
        missing = declared - entries
        orphaned = entries - declared
        if missing or orphaned:
            raise ValueError(
                f"{name} must match declared triage codes; "
                f"missing={sorted(str(item) for item in missing)}, "
                f"orphaned={sorted(str(item) for item in orphaned)}"
            )


validate_error_tables()
