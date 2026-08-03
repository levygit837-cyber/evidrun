from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields
from typing import Any

import pytest

from evidrun.contracts import GoalRevision, GoalSpec
from evidrun.contracts.authoring.goal import GoalOutcome
from evidrun.contracts.lab_agent.errors import LabAgentErrorCode
from evidrun.contracts.lab_agent.scope import LabAgentSessionScope
from evidrun.contracts.triage import TriageErrorCode, TriageRejected
from evidrun.infrastructure.database import Repository
from evidrun.infrastructure.database.decide_errors import decide_human_authority_unavailable
from evidrun.infrastructure.database.models import ContractDecisionRow, ContractRevisionRow
from evidrun.lab.protocol import LabToolContext, declared_argument_keys
from evidrun.lab.tools import build_proposal_tools
from evidrun.lab.tools.draft_store import DatabaseDraftStore
from evidrun.lab.tools.propose_draft import DraftRevisionStore, ProposeDraftTool
from evidrun.lab.tools.request_human_approval import RequestHumanApprovalTool
from evidrun.lab.tools.validate_draft import DraftToolRejected, ValidateDraftTool


def _document(project_id: str | None = None) -> dict[str, object]:
    document = GoalRevision(
        logical_id="lab-goal",
        revision=1,
        project_id=project_id or "project-from-model",
        title="Objetivo do Lab Agent",
        payload=GoalSpec(
            mode="goal_state",
            instruction="Produza uma resposta auditável.",
            outcomes=(GoalOutcome(id="answer", description="A resposta existe."),),
        ),
    ).semantic_document()
    document.pop("project_id")
    return document


def _context(
    workspace_id: str,
    project_id: str,
    *,
    session_id: str = "session_draft",
) -> LabToolContext:
    return LabToolContext(
        scope=LabAgentSessionScope(workspace_id=workspace_id, project_id=project_id),
        session_id=session_id,
        turn_sequence=1,
    )


def test_validate_draft_is_pure_and_uses_the_session_project(repository: Repository) -> None:
    workspace = repository.catalog.create_workspace("Validação")
    project = repository.catalog.create_project(workspace.id, "Projeto")
    context = _context(workspace.id, project.id)

    validate, _, _ = build_proposal_tools(repository)
    result = validate.execute({"contract_type": "goal", "document": _document()}, context)

    assert result.content["valid"] is True
    assert result.content["normalized"]["project_id"] == project.id
    with repository.unit_of_work.session() as session:
        assert session.query(ContractRevisionRow).count() == 0
        assert session.query(ContractDecisionRow).count() == 0


def test_propose_requires_validation_and_accepts_empty_informed_by(
    repository: Repository,
) -> None:
    workspace = repository.catalog.create_workspace("Proposta")
    project = repository.catalog.create_project(workspace.id, "Projeto")
    context = _context(workspace.id, project.id)
    store = DatabaseDraftStore(repository.registry, repository.read_model)
    validate = ValidateDraftTool(store)
    tool = ProposeDraftTool(store)
    arguments: Mapping[str, Any] = {
        "contract_type": "goal",
        "document": _document(),
        "informed_by": [],
    }

    with pytest.raises(DraftToolRejected) as missing:
        tool.execute(arguments, context)
    assert missing.value.error.code == LabAgentErrorCode.DRAFT_NOT_VALIDATED

    validate.execute(
        {"contract_type": arguments["contract_type"], "document": arguments["document"]},
        context,
    )
    result = tool.execute(arguments, context)
    stored = repository.read_model.list_contract_revisions(project.id)

    assert result.content["informed_by"] == ()
    assert len(stored) == 1
    assert stored[0]["project_id"] == project.id
    assert stored[0]["status"] == "draft"
    assert stored[0]["decision"] is None


def test_scope_override_and_authority_fields_are_rejected_before_persistence(
    repository: Repository,
) -> None:
    workspace = repository.catalog.create_workspace("Fronteiras")
    project = repository.catalog.create_project(workspace.id, "Projeto")
    sibling = repository.catalog.create_project(workspace.id, "Irmão")
    context = _context(workspace.id, project.id)
    store = DatabaseDraftStore(repository.registry, repository.read_model)
    tool = ValidateDraftTool(store)

    override = _document()
    override["project_id"] = sibling.id
    with pytest.raises(DraftToolRejected) as scoped:
        tool.execute({"contract_type": "goal", "document": override}, context)
    assert scoped.value.error.code == LabAgentErrorCode.DRAFT_SCOPE_OVERRIDE_FORBIDDEN

    same_scope = {**_document(), "project_id": project.id}
    same_scope_result = tool.execute({"contract_type": "goal", "document": same_scope}, context)
    assert same_scope_result.content["normalized"]["project_id"] == project.id

    for field, value in (
        ("decision", "accepted"),
        ("status", "draft"),
        ("authority", {"kind": "verified_human"}),
        ("attestation", {"principal_id": "human"}),
    ):
        decision = {**_document(), field: value}
        with pytest.raises(DraftToolRejected) as authority:
            tool.execute({"contract_type": "goal", "document": decision}, context)
        assert authority.value.error.code == LabAgentErrorCode.AUTHORITY_HUMAN_DECISION_REQUIRED
        assert "pedido de aprovação" in authority.value.error.remediation

    nested = {**_document(), "payload": {"decision": "accepted"}}
    with pytest.raises(DraftToolRejected) as nested_authority:
        tool.execute({"contract_type": "goal", "document": nested}, context)
    assert nested_authority.value.error.code == LabAgentErrorCode.AUTHORITY_HUMAN_DECISION_REQUIRED
    assert nested_authority.value.error.field_path == (
        "document",
        "payload",
        "decision",
    )
    assert repository.read_model.list_contract_revisions() == []


def test_lab_decision_attempt_matches_human_authority_refusal(
    repository: Repository,
) -> None:
    workspace = repository.catalog.create_workspace("Autoridade")
    project = repository.catalog.create_project(workspace.id, "Projeto")
    context = _context(workspace.id, project.id)
    tool = ValidateDraftTool(DatabaseDraftStore(repository.registry, repository.read_model))

    with pytest.raises(DraftToolRejected) as lab_attempt:
        tool.execute(
            {
                "contract_type": "goal",
                "document": {**_document(), "decision": "accepted"},
            },
            context,
        )
    with pytest.raises(TriageRejected) as human_attempt:
        raise decide_human_authority_unavailable()

    assert lab_attempt.value.error.code == LabAgentErrorCode.AUTHORITY_HUMAN_DECISION_REQUIRED
    assert human_attempt.value.error.code == TriageErrorCode.DECIDE_HUMAN_AUTHORITY_UNAVAILABLE
    # Os catálogos são costuras separadas: Lab Agent recusa a tentativa antes de ela
    # formar RevisionDecisionRecord; a API humana nomeia a ausência do autenticador.
    assert repository.read_model.list_contract_revisions() == []


def test_approval_request_promotes_without_decision_or_attestation(
    repository: Repository,
) -> None:
    workspace = repository.catalog.create_workspace("Aprovação")
    project = repository.catalog.create_project(workspace.id, "Projeto")
    context = _context(workspace.id, project.id)
    validate, propose, request_approval = build_proposal_tools(repository)
    arguments: Mapping[str, Any] = {
        "contract_type": "goal",
        "document": _document(),
        "informed_by": [],
    }
    validate.execute(
        {"contract_type": arguments["contract_type"], "document": arguments["document"]},
        context,
    )
    proposed = propose.execute(arguments, context)

    result = request_approval.execute(
        {"revision_ref": proposed.content["revision_ref"], "rationale": "Pronto para revisão."},
        context,
    )
    stored = repository.read_model.list_contract_revisions(project.id)[0]

    assert result.content["digest"] == proposed.content["digest"]
    assert result.content["project_id"] == project.id
    assert result.content["status"] == "proposed"
    assert result.content["decision"] is None
    assert stored["status"] == "proposed"
    assert stored["decision"] is None
    assert "attestation" not in result.content
    with repository.unit_of_work.session() as session:
        assert session.query(ContractDecisionRow).count() == 0


def test_approval_request_refuses_a_revision_not_in_draft_status(
    repository: Repository,
) -> None:
    workspace = repository.catalog.create_workspace("Aprovação repetida")
    project = repository.catalog.create_project(workspace.id, "Projeto")
    context = _context(workspace.id, project.id)
    validate, propose, request_approval = build_proposal_tools(repository)
    arguments: Mapping[str, Any] = {
        "contract_type": "goal",
        "document": _document(),
        "informed_by": [],
    }
    validate.execute(
        {"contract_type": arguments["contract_type"], "document": arguments["document"]},
        context,
    )
    proposed = propose.execute(arguments, context)
    call = {"revision_ref": proposed.content["revision_ref"], "rationale": "Revisar."}
    request_approval.execute(call, context)

    with pytest.raises(DraftToolRejected) as repeated:
        request_approval.execute(call, context)

    assert repeated.value.error.code == LabAgentErrorCode.SCOPE_TARGET_NOT_VISIBLE
    stored = repository.read_model.list_contract_revisions(project.id)[0]
    assert stored["status"] == "proposed"
    assert stored["decision"] is None


def test_validation_receipt_is_exact_to_turn_scope_and_document(repository: Repository) -> None:
    workspace = repository.catalog.create_workspace("Recibo")
    project = repository.catalog.create_project(workspace.id, "Projeto")
    context = _context(workspace.id, project.id)
    validate, propose, _ = build_proposal_tools(repository)
    document = _document()
    validate.execute({"contract_type": "goal", "document": document}, context)

    changed = {**document, "title": "Mudou depois da validação"}
    with pytest.raises(DraftToolRejected) as mismatch:
        propose.execute({"contract_type": "goal", "document": changed, "informed_by": []}, context)
    assert mismatch.value.error.code == LabAgentErrorCode.DRAFT_NOT_VALIDATED

    next_turn = LabToolContext(
        scope=context.scope,
        session_id=context.session_id,
        turn_sequence=context.turn_sequence + 1,
    )
    with pytest.raises(DraftToolRejected) as stale:
        propose.execute(
            {"contract_type": "goal", "document": document, "informed_by": []}, next_turn
        )
    assert stale.value.error.code == LabAgentErrorCode.DRAFT_NOT_VALIDATED
    assert repository.read_model.list_contract_revisions() == []


def test_validation_receipt_is_private_to_composed_store(repository: Repository) -> None:
    workspace = repository.catalog.create_workspace("Recibo recomposto")
    project = repository.catalog.create_project(workspace.id, "Projeto")
    context = _context(workspace.id, project.id)
    document = _document()
    ValidateDraftTool(DatabaseDraftStore(repository.registry, repository.read_model)).execute(
        {"contract_type": "goal", "document": document}, context
    )

    with pytest.raises(DraftToolRejected) as recomposed:
        ProposeDraftTool(DatabaseDraftStore(repository.registry, repository.read_model)).execute(
            {"contract_type": "goal", "document": document, "informed_by": []},
            context,
        )

    assert recomposed.value.error.code == LabAgentErrorCode.DRAFT_NOT_VALIDATED
    assert repository.read_model.list_contract_revisions() == []


def test_approval_request_cannot_cross_project(repository: Repository) -> None:
    workspace = repository.catalog.create_workspace("Escopo da aprovação")
    project = repository.catalog.create_project(workspace.id, "Projeto")
    sibling = repository.catalog.create_project(workspace.id, "Irmão")
    context = _context(workspace.id, project.id)
    revision = GoalRevision.model_validate({**_document(), "project_id": sibling.id})
    row = repository.registry.save_contract_revision(revision)

    with pytest.raises(DraftToolRejected) as refused:
        store = DatabaseDraftStore(repository.registry, repository.read_model)
        RequestHumanApprovalTool(store).execute(
            {"revision_ref": row.id, "rationale": "Não deveria atravessar Project."}, context
        )

    assert refused.value.error.code == LabAgentErrorCode.SCOPE_TARGET_NOT_VISIBLE
    assert repository.read_model.list_contract_revisions(sibling.id)[0]["status"] == "draft"


def test_proposal_store_protocol_has_no_decision_method() -> None:
    assert {field.name for field in fields(LabToolContext)} == {
        "scope",
        "session_id",
        "turn_sequence",
    }
    assert hasattr(DraftRevisionStore, "contract_registry")
    assert hasattr(DraftRevisionStore, "save_contract_revision")
    assert not hasattr(DatabaseDraftStore, "decide_contract_revision")


def test_proposal_schemas_expose_exact_contract_fields(repository: Repository) -> None:
    store = DatabaseDraftStore(repository.registry, repository.read_model)
    assert declared_argument_keys(ProposeDraftTool(store).provider_schema()) == {
        "contract_type",
        "document",
        "informed_by",
    }
    assert declared_argument_keys(RequestHumanApprovalTool(store).provider_schema()) == {
        "revision_ref",
        "rationale",
    }
