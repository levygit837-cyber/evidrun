from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from evidrun.contracts.runtime.spec import AdmissionIssue, ResolutionReason
from evidrun.contracts.triage import (
    CATEGORY_BY_CODE,
    CLI_EXIT_BY_CODE,
    HTTP_STATUS_BY_CODE,
    CliExitCode,
    TriageError,
    TriageErrorCode,
    TriagePhase,
    validate_error_tables,
)

ROOT = Path(__file__).resolve().parents[2]

EXPECTED_CODES = {
    "parse.document_not_object",
    "parse.contract_type_missing",
    "parse.contract_type_unknown",
    "parse.field_undeclared",
    "parse.revision_invalid",
    "parse.identifier_empty",
    "parse.payload_type_invalid",
    "parse.schema_invalid",
    "register.project_not_found",
    "register.revision_not_monotonic",
    "register.immutability_conflict",
    "register.initial_status_invalid",
    "decide.human_authority_unavailable",
    "decide.revision_not_found",
    "decide.decision_conflict",
    "decide.repository_fixture_forbidden",
    "compile.revision_not_found",
    "compile.revision_not_study",
    "compile.dependency_not_accepted",
    "compile.digest_mismatch",
    "compile.controlled_slots_mismatch",
    "compile.confounder_missing",
    "admit.run_spec_not_found",
    "admit.rejected",
    "admit.inventory_not_persistible",
    "enqueue.run_spec_not_found",
    "enqueue.admission_not_found",
    "enqueue.admission_not_admitted",
    "enqueue.admission_run_spec_mismatch",
    "enqueue.digest_mismatch",
    "enqueue.idempotency_key_empty",
    "enqueue.idempotency_conflict",
    "enqueue.retry_source_succeeded",
    "enqueue.retry_admission_not_newer",
    "enqueue.retry_admission_reused",
    "enqueue.retry_legacy_run",
}


def admission_issue(subject_ref: str) -> AdmissionIssue:
    return AdmissionIssue(
        category="capability",
        subject_ref=subject_ref,
        reason=ResolutionReason(code="unsupported", detail=f"{subject_ref} is unsupported"),
        blocking=True,
    )


def test_triage_codes_and_status_tables_are_exhaustive() -> None:
    assert {code.value for code in TriageErrorCode} == EXPECTED_CODES
    assert set(HTTP_STATUS_BY_CODE) == set(TriageErrorCode)
    assert set(CLI_EXIT_BY_CODE) == set(TriageErrorCode)
    assert all(code.value.startswith(f"{code.phase.value}.") for code in TriageErrorCode)


def test_contract_tables_are_immutable() -> None:
    assert type(CATEGORY_BY_CODE).__name__ == "mappingproxy"
    assert type(HTTP_STATUS_BY_CODE).__name__ == "mappingproxy"
    assert type(CLI_EXIT_BY_CODE).__name__ == "mappingproxy"


def test_table_validation_rejects_missing_and_orphan_entries() -> None:
    missing_http = dict(HTTP_STATUS_BY_CODE)
    missing_http.pop(TriageErrorCode.PARSE_SCHEMA_INVALID)
    with pytest.raises(ValueError, match="HTTP status table"):
        validate_error_tables(missing_http, CLI_EXIT_BY_CODE)

    orphan_cli: dict[object, CliExitCode] = {
        **CLI_EXIT_BY_CODE,
        "parse.orphan": CliExitCode.INVALID,
    }
    with pytest.raises(ValueError, match="CLI exit table"):
        validate_error_tables(HTTP_STATUS_BY_CODE, orphan_cli)


def test_triage_error_serialization_preserves_admission_finding_order() -> None:
    error = TriageError(
        phase=TriagePhase.ADMIT,
        code=TriageErrorCode.ADMIT_REJECTED,
        message="A admissão recusou o RunSpec.",
        field_path=("agent_inventory", "capabilities"),
        remediation="Declare somente capabilities disponíveis.",
        issues=(admission_issue("capability:first"), admission_issue("capability:second")),
        missing_requirements=("runtime:first", "runtime:second"),
        denied_policies=("classification:first", "classification:second"),
    )

    payload = error.model_dump(mode="json")

    assert payload["category"] == "rejected"
    assert HTTP_STATUS_BY_CODE[error.code] == 422
    assert CLI_EXIT_BY_CODE[error.code] == CliExitCode.REJECTED
    assert [item["subject_ref"] for item in payload["issues"]] == [
        "capability:first",
        "capability:second",
    ]
    assert payload["missing_requirements"] == ["runtime:first", "runtime:second"]
    assert payload["denied_policies"] == ["classification:first", "classification:second"]


def test_triage_error_rejects_a_code_from_another_phase() -> None:
    with pytest.raises(ValidationError, match="code prefix must match phase"):
        TriageError(
            phase=TriagePhase.PARSE,
            code=TriageErrorCode.REGISTER_PROJECT_NOT_FOUND,
            message="Projeto inexistente.",
        )


def test_triage_vocabulary_has_no_framework_or_persistence_imports() -> None:
    source = (ROOT / "src/evidrun/contracts/triage.py").read_text(encoding="utf-8")

    for forbidden in ("fastapi", "typer", "sqlalchemy", "evidrun.infrastructure"):
        assert forbidden not in source
