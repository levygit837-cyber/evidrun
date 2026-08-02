from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from evidrun.contracts.lab_agent.envelope import (
    LabAgentEnvelope,
    LabAgentMessage,
    LabAgentMessageRole,
    LabAgentTurnLimits,
)
from evidrun.contracts.lab_agent.errors import (
    CATEGORY_BY_CODE,
    CLI_EXIT_BY_CODE,
    HTTP_STATUS_BY_CODE,
    LabAgentCliExitCode,
    LabAgentError,
    LabAgentErrorCategory,
    LabAgentErrorCode,
    LabAgentStage,
    validate_lab_agent_error_tables,
)
from evidrun.contracts.lab_agent.scope import (
    LabAgentFocusKind,
    LabAgentSessionForm,
    LabAgentSessionScope,
)
from evidrun.contracts.scope import ScopeErrorCode
from evidrun.contracts.triage import TriageErrorCode

ROOT = Path(__file__).resolve().parents[2]

#: Os 21 códigos de docs/contracts/lab-agent-errors-v1.md, literalmente.
EXPECTED_CODES = {
    "catalog.tool_unknown",
    "catalog.tool_not_offered",
    "budget.tool_calls_exhausted",
    "budget.round_trips_exhausted",
    "budget.wall_time_exhausted",
    "budget.refusals_exhausted",
    "budget.refusal_repeated",
    "schema.argument_set_invalid",
    "schema.argument_type_invalid",
    "schema.argument_limit_exceeded",
    "schema.scope_argument_forbidden",
    "scope.target_not_visible",
    "scope.focus_mismatch",
    "scope.project_required",
    "classification.grant_required",
    "authority.human_decision_required",
    "authority.ledger_write_forbidden",
    "authority.persisted_effect_forbidden",
    "draft.validation_failed",
    "draft.not_validated",
    "draft.scope_override_forbidden",
}

LIMITS = LabAgentTurnLimits(
    max_tool_calls_per_turn=8,
    max_provider_round_trips_per_turn=10,
    max_wall_seconds_per_turn=120,
    max_refusals_per_turn=3,
    max_output_tokens_per_round_trip=2048,
)


def envelope(scope: LabAgentSessionScope, **overrides: object) -> LabAgentEnvelope:
    document: dict[str, object] = {
        "session_id": "session-1",
        "scope": scope,
        "limits": LIMITS,
        **overrides,
    }
    return LabAgentEnvelope.model_validate(document)


# --- LabAgentSessionScope: as três formas válidas e as combinações recusadas -------------


def test_general_chat_carries_only_the_workspace_boundary() -> None:
    scope = LabAgentSessionScope(workspace_id="ws-1")

    assert scope.form is LabAgentSessionForm.GENERAL
    assert scope.project_id is None
    assert scope.focus_kind is None


def test_project_chat_adds_the_project_without_a_focus() -> None:
    scope = LabAgentSessionScope(workspace_id="ws-1", project_id="pr-1")

    assert scope.form is LabAgentSessionForm.PROJECT
    assert scope.focus_id is None


@pytest.mark.parametrize("kind", list(LabAgentFocusKind))
def test_focused_chat_narrows_a_project_chat_by_one_declared_focus(kind: LabAgentFocusKind) -> None:
    scope = LabAgentSessionScope(
        workspace_id="ws-1", project_id="pr-1", focus_kind=kind, focus_id="target-1"
    )

    assert scope.form is LabAgentSessionForm.FOCUSED
    assert scope.focus_kind is kind


def test_focus_vocabulary_is_exactly_the_normative_set() -> None:
    assert {kind.value for kind in LabAgentFocusKind} == {"study", "run", "comparison"}


def test_session_without_workspace_is_refused() -> None:
    with pytest.raises(ValidationError):
        LabAgentSessionScope.model_validate({"project_id": "pr-1"})


@pytest.mark.parametrize(
    ("document", "match"),
    [
        (
            {"workspace_id": "ws-1", "focus_kind": "study", "focus_id": "st-1"},
            "focus requires project_id",
        ),
        (
            {"workspace_id": "ws-1", "project_id": "pr-1", "focus_kind": "study"},
            "focus_kind and focus_id together",
        ),
        (
            {"workspace_id": "ws-1", "project_id": "pr-1", "focus_id": "st-1"},
            "focus_kind and focus_id together",
        ),
    ],
)
def test_incoherent_focus_combinations_are_refused(document: dict[str, str], match: str) -> None:
    with pytest.raises(ValidationError, match=match):
        LabAgentSessionScope.model_validate(document)


def test_a_second_focus_has_no_slot_in_the_scope_document() -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        LabAgentSessionScope.model_validate(
            {
                "workspace_id": "ws-1",
                "project_id": "pr-1",
                "focus_kind": "study",
                "focus_id": "st-1",
                "secondary_focus_kind": "run",
                "secondary_focus_id": "run-1",
            }
        )


def test_unknown_generic_scope_is_refused_instead_of_interpreted() -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        LabAgentSessionScope.model_validate(
            {"workspace_id": "ws-1", "scope_type": "portfolio", "scope_id": "pf-1"}
        )


def test_unknown_focus_kind_is_refused() -> None:
    with pytest.raises(ValidationError):
        LabAgentSessionScope.model_validate(
            {
                "workspace_id": "ws-1",
                "project_id": "pr-1",
                "focus_kind": "workspace",
                "focus_id": "ws-2",
            }
        )


def test_scope_is_immutable_after_construction() -> None:
    scope = LabAgentSessionScope(workspace_id="ws-1", project_id="pr-1")

    with pytest.raises(ValidationError):
        scope.project_id = "pr-2"  # type: ignore[misc]


# --- LabAgentEnvelope: allowlist fechada, sem locator ------------------------------------


def test_envelope_discloses_scope_history_refs_and_effective_limits() -> None:
    document = envelope(
        LabAgentSessionScope(workspace_id="ws-1", project_id="pr-1"),
        history=(
            LabAgentMessage(role=LabAgentMessageRole.HUMAN, sequence=1, content="Compare as Runs."),
            LabAgentMessage(role=LabAgentMessageRole.AGENT, sequence=2, content="Vou listar."),
        ),
        contract_refs=(
            {
                "contract_type": "study",
                "logical_id": "study-a",
                "revision": 1,
                "digest": "a" * 64,
            },
        ),
        evidence_refs=({"ref": "run:run-1"},),
        artifact_refs=(
            {"artifact_id": "art-1", "digest": "b" * 64, "media_type": "application/json"},
        ),
        offered_tools=("list_runs", "read_run"),
    ).model_dump(mode="json")

    assert document["scope"]["project_id"] == "pr-1"
    assert [item["sequence"] for item in document["history"]] == [1, 2]
    assert document["limits"]["max_refusals_per_turn"] == 3
    assert document["offered_tools"] == ["list_runs", "read_run"]
    assert set(document["artifact_refs"][0]) == {
        "artifact_id",
        "digest",
        "media_type",
        "classification",
    }


def test_envelope_artifact_ref_has_no_locator_field() -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        envelope(
            LabAgentSessionScope(workspace_id="ws-1", project_id="pr-1"),
            artifact_refs=(
                {
                    "artifact_id": "art-1",
                    "digest": "b" * 64,
                    "media_type": "application/json",
                    "locator": "/var/lib/evidrun/art-1.json",
                },
            ),
        )


@pytest.mark.parametrize(
    "field",
    ["api_key", "credential", "messages_from_other_session", "attestation", "artifact_bytes"],
)
def test_envelope_refuses_fields_outside_the_allowlist(field: str) -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        envelope(LabAgentSessionScope(workspace_id="ws-1"), **{field: "x"})


def test_general_chat_envelope_cannot_disclose_project_content_refs() -> None:
    with pytest.raises(ValidationError, match="General chat"):
        envelope(
            LabAgentSessionScope(workspace_id="ws-1"),
            evidence_refs=({"ref": "run:run-1"},),
        )


def test_history_out_of_sequence_order_is_refused() -> None:
    with pytest.raises(ValidationError, match="ordered by sequence"):
        envelope(
            LabAgentSessionScope(workspace_id="ws-1"),
            history=(
                LabAgentMessage(role=LabAgentMessageRole.AGENT, sequence=2, content="segunda"),
                LabAgentMessage(role=LabAgentMessageRole.HUMAN, sequence=1, content="primeira"),
            ),
        )


def test_history_with_duplicate_sequence_is_refused() -> None:
    with pytest.raises(ValidationError, match="distinct sequences"):
        envelope(
            LabAgentSessionScope(workspace_id="ws-1"),
            history=(
                LabAgentMessage(role=LabAgentMessageRole.HUMAN, sequence=1, content="a"),
                LabAgentMessage(role=LabAgentMessageRole.AGENT, sequence=1, content="b"),
            ),
        )


def test_message_role_outside_the_closed_enum_is_refused() -> None:
    with pytest.raises(ValidationError):
        LabAgentMessage.model_validate({"role": "tool", "sequence": 1, "content": "x"})


def test_changing_project_produces_another_envelope_digest() -> None:
    first = envelope(LabAgentSessionScope(workspace_id="ws-1", project_id="pr-1"))
    sibling = envelope(LabAgentSessionScope(workspace_id="ws-1", project_id="pr-2"))

    assert first.digest != sibling.digest
    assert first.digest == envelope(first.scope).digest


# --- LabAgentError: catálogo, totalidade e separação de costura ---------------------------


def test_catalog_declares_exactly_the_twenty_one_contract_codes() -> None:
    assert {code.value for code in LabAgentErrorCode} == EXPECTED_CODES
    assert len(EXPECTED_CODES) == 21


def test_catalog_matches_the_normative_contract_table() -> None:
    text = (ROOT / "docs/contracts/lab-agent-errors-v1.md").read_text(encoding="utf-8")
    rows = re.findall(r"^\| `([a-z_]+\.[a-z_]+)` \| `([a-z_]+)` \|", text, flags=re.MULTILINE)

    assert {code for code, _category in rows} == EXPECTED_CODES
    assert {
        LabAgentErrorCode(code): LabAgentErrorCategory(category) for code, category in rows
    } == dict(CATEGORY_BY_CODE)


def test_stages_are_the_seven_declared_verification_steps() -> None:
    assert [stage.value for stage in LabAgentStage] == [
        "catalog",
        "budget",
        "schema",
        "scope",
        "classification",
        "authority",
        "draft",
    ]
    assert {code.stage for code in LabAgentErrorCode} == set(LabAgentStage)


def test_translation_tables_are_total_over_the_enum() -> None:
    assert set(CATEGORY_BY_CODE) == set(LabAgentErrorCode)
    assert set(HTTP_STATUS_BY_CODE) == set(LabAgentErrorCode)
    assert set(CLI_EXIT_BY_CODE) == set(LabAgentErrorCode)


@pytest.mark.parametrize("table_name", ["http_status_by_code", "cli_exit_by_code"])
def test_tables_fail_closed_when_a_code_loses_its_entry(table_name: str) -> None:
    source = HTTP_STATUS_BY_CODE if table_name == "http_status_by_code" else CLI_EXIT_BY_CODE
    incomplete = dict(source)
    incomplete.pop(LabAgentErrorCode.SCOPE_TARGET_NOT_VISIBLE)

    with pytest.raises(ValueError, match="missing="):
        validate_lab_agent_error_tables(**{table_name: incomplete})


@pytest.mark.parametrize("table_name", ["http_status_by_code", "cli_exit_by_code"])
def test_tables_fail_closed_on_an_orphaned_entry(table_name: str) -> None:
    source = HTTP_STATUS_BY_CODE if table_name == "http_status_by_code" else CLI_EXIT_BY_CODE
    orphaned = dict(source) | {"lab.retired_code": 410}

    with pytest.raises(ValueError, match="orphaned="):
        validate_lab_agent_error_tables(**{table_name: orphaned})


def test_lab_agent_codes_never_collide_with_triage_or_scope_seams() -> None:
    lab = {code.value for code in LabAgentErrorCode}

    assert lab.isdisjoint({code.value for code in TriageErrorCode})
    assert lab.isdisjoint({code.value for code in ScopeErrorCode})


def test_category_is_derived_from_the_code_and_not_declarable() -> None:
    error = LabAgentError(
        stage=LabAgentStage.CATALOG,
        code=LabAgentErrorCode.CATALOG_TOOL_NOT_OFFERED,
        message="Esta leitura não existe nesta forma de sessão.",
        remediation="Peça ao humano para abrir uma Project chat.",
        tool_name="list_runs",
    )

    assert error.category is LabAgentErrorCategory.NOT_FOUND
    assert error.model_dump(mode="json") == {
        "stage": "catalog",
        "code": "catalog.tool_not_offered",
        "message": "Esta leitura não existe nesta forma de sessão.",
        "remediation": "Peça ao humano para abrir uma Project chat.",
        "field_path": [],
        "tool_name": "list_runs",
        "category": "not_found",
    }
    with pytest.raises(ValidationError, match="extra_forbidden"):
        LabAgentError.model_validate(
            {
                "stage": "catalog",
                "code": "catalog.tool_unknown",
                "message": "m",
                "remediation": "r",
                "category": "invalid",
            }
        )


def test_code_prefix_must_match_the_declared_stage() -> None:
    with pytest.raises(ValidationError, match="code prefix must match stage"):
        LabAgentError(
            stage=LabAgentStage.SCHEMA,
            code=LabAgentErrorCode.SCOPE_TARGET_NOT_VISIBLE,
            message="m",
            remediation="r",
        )


# --- Indistinguibilidade -----------------------------------------------------------------


def not_visible(target_id: str) -> LabAgentError:
    """A recusa que as três situações de alvo não visível produzem, por construção."""

    return LabAgentError(
        stage=LabAgentStage.SCOPE,
        code=LabAgentErrorCode.SCOPE_TARGET_NOT_VISIBLE,
        message="A referência solicitada não está disponível nesta sessão.",
        remediation="Liste os alvos deste Project antes de referenciar um id.",
        field_path=("revision_ref",),
        tool_name="read_contract_revision",
    )


def test_the_three_not_visible_situations_produce_an_identical_payload() -> None:
    absent = not_visible("st-inexistente")
    sibling_project = not_visible("st-do-projeto-irmao")
    other_workspace = not_visible("st-de-outro-workspace")

    payloads = [
        error.model_dump(mode="json") for error in (absent, sibling_project, other_workspace)
    ]

    assert payloads[0] == payloads[1] == payloads[2]
    assert len({error.category for error in (absent, sibling_project, other_workspace)}) == 1
    assert len({HTTP_STATUS_BY_CODE[error.code] for error in (absent, sibling_project)}) == 1
    assert HTTP_STATUS_BY_CODE[absent.code] == 404
    assert CLI_EXIT_BY_CODE[absent.code] is LabAgentCliExitCode.NOT_FOUND


def test_not_visible_and_focus_mismatch_share_category_status_and_payload_shape() -> None:
    mismatch = LabAgentError(
        stage=LabAgentStage.SCOPE,
        code=LabAgentErrorCode.SCOPE_FOCUS_MISMATCH,
        message="A referência solicitada não está disponível nesta sessão.",
        remediation="Liste os alvos deste Project antes de referenciar um id.",
        field_path=("run_id",),
        tool_name="read_run",
    )
    target = not_visible("st-1")

    assert mismatch.category is target.category
    assert HTTP_STATUS_BY_CODE[mismatch.code] == HTTP_STATUS_BY_CODE[target.code]
    assert CLI_EXIT_BY_CODE[mismatch.code] is CLI_EXIT_BY_CODE[target.code]
    assert set(mismatch.model_dump(mode="json")) == set(target.model_dump(mode="json"))


EXISTENCE_LEAKS = (
    "existe",
    "encontrad",
    "não pertence",
    "outro project",
    "outro workspace",
    "project irmão",
    "study",
    "comparison",
    "peça acesso",
    "solicite acesso",
    "permissão",
)


@pytest.mark.parametrize(
    "code",
    [LabAgentErrorCode.SCOPE_TARGET_NOT_VISIBLE, LabAgentErrorCode.SCOPE_FOCUS_MISMATCH],
)
def test_target_refusals_never_reveal_existence_type_or_ownership(
    code: LabAgentErrorCode,
) -> None:
    error = LabAgentError(
        stage=LabAgentStage.SCOPE,
        code=code,
        message="A referência solicitada não está disponível nesta sessão.",
        remediation="Liste os alvos deste Project antes de referenciar um id.",
        field_path=("revision_ref",),
    )
    text = f"{error.message} {error.remediation}".casefold()

    assert not [leak for leak in EXISTENCE_LEAKS if leak in text]
    assert "list" in error.remediation.casefold()


def test_project_required_may_be_explicit_because_it_describes_the_session() -> None:
    error = LabAgentError(
        stage=LabAgentStage.SCOPE,
        code=LabAgentErrorCode.SCOPE_PROJECT_REQUIRED,
        message="Esta operação exige uma Project chat; a sessão atual é General.",
        remediation="Peça ao humano para abrir uma Project chat e repita o pedido lá.",
    )

    assert error.category is LabAgentErrorCategory.REJECTED
    assert error.category is not LabAgentErrorCategory.NOT_FOUND
    assert HTTP_STATUS_BY_CODE[error.code] != HTTP_STATUS_BY_CODE[
        LabAgentErrorCode.SCOPE_TARGET_NOT_VISIBLE
    ]


# --- Remediação acionável ----------------------------------------------------------------


@pytest.mark.parametrize("code", list(LabAgentErrorCode))
def test_every_refusal_requires_a_non_empty_remediation(code: LabAgentErrorCode) -> None:
    with pytest.raises(ValidationError, match="remediation"):
        LabAgentError.model_validate(
            {"stage": code.stage.value, "code": code.value, "message": "Recusado."}
        )
    with pytest.raises(ValidationError, match="remediation"):
        LabAgentError.model_validate(
            {
                "stage": code.stage.value,
                "code": code.value,
                "message": "Recusado.",
                "remediation": "   ",
            }
        )


def test_remediation_is_required_here_and_optional_in_triage() -> None:
    lab_required = LabAgentError.model_fields["remediation"].is_required()
    triage_optional = not (
        __import__("evidrun.contracts.triage", fromlist=["TriageError"])
        .TriageError.model_fields["remediation"]
        .is_required()
    )

    assert lab_required
    assert triage_optional


def test_message_and_remediation_are_stripped_and_never_blank() -> None:
    error = LabAgentError(
        stage=LabAgentStage.DRAFT,
        code=LabAgentErrorCode.DRAFT_VALIDATION_FAILED,
        message="  O documento não satisfaz o contrato declarado.  ",
        remediation="  Corrija `variants[0].id` e valide de novo antes de propor.  ",
        field_path=("variants", "0", "id"),
    )

    assert error.message == "O documento não satisfaz o contrato declarado."
    assert error.remediation.startswith("Corrija")
