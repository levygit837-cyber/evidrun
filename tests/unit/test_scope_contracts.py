from __future__ import annotations

import pytest

from evidrun.contracts.scope import (
    CATEGORY_BY_CODE,
    CLI_EXIT_BY_CODE,
    HTTP_STATUS_BY_CODE,
    ScopeError,
    ScopeErrorCategory,
    ScopeErrorCode,
    normalize_scope_name,
    validate_scope_error_tables,
)


def test_scope_name_normalization_preserves_display_and_canonicalizes_identity() -> None:
    normalized = normalize_scope_name(" \t\uff30esquisa\u00a0  Avançada \n")

    assert normalized.name == "Pesquisa Avançada"
    assert normalized.name_key == "pesquisa avançada"
    assert normalize_scope_name("Cafe\u0301").name == "Café"
    assert normalize_scope_name("CAFÉ").name_key == "café"


@pytest.mark.parametrize("value", ["", "   ", "\t\n", "\u00a0"])
def test_scope_name_normalization_rejects_empty_forms(value: str) -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        normalize_scope_name(value)


def test_scope_error_catalog_is_complete_and_separate_from_triage() -> None:
    expected = {
        "workspace.name_invalid",
        "workspace.name_conflict",
        "project.name_invalid",
        "project.name_conflict",
        "project.workspace_not_found",
        "scope.storage_unavailable",
    }
    assert {code.value for code in ScopeErrorCode} == expected
    assert set(CATEGORY_BY_CODE) == set(ScopeErrorCode)
    assert set(HTTP_STATUS_BY_CODE) == set(ScopeErrorCode)
    assert set(CLI_EXIT_BY_CODE) == set(ScopeErrorCode)


def test_scope_error_serializes_stable_category_and_safe_fields() -> None:
    error = ScopeError(
        code=ScopeErrorCode.WORKSPACE_NAME_CONFLICT,
        message="Nome equivalente já existe.",
        field_path=("name",),
        remediation="Escolha outro nome.",
    )

    assert error.category is ScopeErrorCategory.CONFLICT
    assert error.model_dump(mode="json") == {
        "code": "workspace.name_conflict",
        "message": "Nome equivalente já existe.",
        "field_path": ["name"],
        "remediation": "Escolha outro nome.",
        "category": "conflict",
    }


def test_scope_error_tables_fail_closed_when_a_mapping_drifts() -> None:
    incomplete = dict(HTTP_STATUS_BY_CODE)
    incomplete.pop(ScopeErrorCode.WORKSPACE_NAME_INVALID)

    with pytest.raises(ValueError, match="HTTP status table"):
        validate_scope_error_tables(http_status_by_code=incomplete)
