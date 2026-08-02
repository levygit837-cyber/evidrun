from __future__ import annotations

import json
from dataclasses import fields

import pytest
from sqlalchemy import select

from evidrun.infrastructure.database.lab import LabSession, LabToolTrace
from evidrun.infrastructure.database.lab_errors import LabStoreRejected
from evidrun.infrastructure.database.models import (
    ChatMessageRow,
    ChatSessionRow,
    ContractRevisionRow,
    LabToolTraceRow,
    RunEventRow,
)
from evidrun.shared.types import sha256_json


def _scopes(repository):
    workspace = repository.catalog.create_workspace("Laboratório A")
    other_workspace = repository.catalog.create_workspace("Laboratório B")
    project = repository.catalog.create_project(workspace.id, "Projeto A")
    sibling = repository.catalog.create_project(workspace.id, "Projeto irmão")
    foreign = repository.catalog.create_project(other_workspace.id, "Projeto externo")
    return workspace, other_workspace, project, sibling, foreign


def test_session_scope_is_typed_immutable_and_workspace_filtered(repository) -> None:
    workspace, other_workspace, project, _sibling, foreign = _scopes(repository)

    with pytest.raises(LabStoreRejected, match=r"lab\.scope_invalid"):
        repository.lab.create_session(workspace_id="", title="Sem Workspace")
    with pytest.raises(LabStoreRejected, match=r"lab\.target_not_visible"):
        repository.lab.create_session(
            workspace_id=workspace.id, project_id=foreign.id, title="Fora"
        )
    with pytest.raises(LabStoreRejected, match=r"lab\.scope_invalid"):
        repository.lab.create_session(
            workspace_id=workspace.id,
            focus_kind="study",
            focus_id="study_missing",
            title="Sem Project",
        )

    general = repository.lab.create_session(workspace_id=workspace.id, title="Geral")
    project_chat = repository.lab.create_session(
        workspace_id=workspace.id, project_id=project.id, title="Projeto"
    )
    repository.lab.create_session(workspace_id=other_workspace.id, title="Outro")

    assert [item.id for item in repository.lab.list_sessions(workspace_id=workspace.id)] == [
        general.id,
        project_chat.id,
    ]
    navigation = repository.lab.list_navigation_projects(
        session_id=general.id, workspace_id=workspace.id
    )
    assert [item.name for item in navigation] == ["Projeto A", "Projeto irmão"]
    assert {field.name for field in fields(type(navigation[0]))} == {
        "id",
        "name",
        "created_at",
    }
    assert {field.name for field in fields(LabSession)} == {
        "id", "workspace_id", "project_id", "focus_kind", "focus_id", "title", "created_at"
    }
    assert not any(name.startswith("update") for name in dir(repository.lab))

    with pytest.raises(LabStoreRejected, match=r"lab\.target_not_visible"):
        repository.lab.require_project(
            session_id=project_chat.id, workspace_id=workspace.id, project_id=foreign.id
        )


def test_read_revalidates_project_and_focus_membership(repository) -> None:
    workspace, _other_workspace, project, sibling, foreign = _scopes(repository)
    chat = repository.lab.create_session(
        workspace_id=workspace.id, project_id=project.id, title="Projeto"
    )
    with repository.unit_of_work.session() as session:
        row = session.get(ChatSessionRow, chat.id)
        assert row is not None
        row.project_id = foreign.id
        session.commit()
    with pytest.raises(LabStoreRejected, match=r"lab\.target_not_visible"):
        repository.lab.get_session(session_id=chat.id, workspace_id=workspace.id)

    with repository.unit_of_work.session() as session:
        study = ContractRevisionRow(
            id="study_sibling",
            contract_type="study",
            logical_id="sibling-study",
            revision=1,
            project_id=sibling.id,
            title="Study irmão",
            status="draft",
            document_json='{"schema_version":"1"}',
            digest="a" * 64,
            created_at=workspace.created_at,
        )
        session.add(study)
        session.commit()
    with pytest.raises(LabStoreRejected, match=r"lab\.target_not_visible"):
        repository.lab.create_session(
            workspace_id=workspace.id,
            project_id=project.id,
            focus_kind="study",
            focus_id=study.id,
            title="Foco cruzado",
        )


def test_messages_are_closed_ordered_gapless_and_append_only(repository) -> None:
    workspace, *_ = _scopes(repository)
    chat = repository.lab.create_session(workspace_id=workspace.id, title="Geral")
    with pytest.raises(LabStoreRejected, match=r"lab\.message_role_invalid"):
        repository.lab.append_message(
            session_id=chat.id, workspace_id=workspace.id, role="tool", content="x"
        )

    first = repository.lab.append_message(
        session_id=chat.id, workspace_id=workspace.id, role="human", content="Oi"
    )
    second = repository.lab.append_message(
        session_id=chat.id, workspace_id=workspace.id, role="agent", content="Olá"
    )
    assert [item.sequence for item in repository.lab.list_messages(
        session_id=chat.id, workspace_id=workspace.id
    )] == [1, 2]
    assert first.content == "Oi" and second.content == "Olá"
    assert not any(
        name.startswith(("update_message", "delete_message"))
        for name in dir(repository.lab)
    )

    with repository.unit_of_work.session() as session:
        row = session.get(ChatMessageRow, second.id)
        assert row is not None
        row.sequence = 3
        session.commit()
    with pytest.raises(LabStoreRejected, match=r"lab\.tool_trace_invalid"):
        repository.lab.list_messages(session_id=chat.id, workspace_id=workspace.id)


def test_tool_trace_preserves_attempt_and_stays_outside_ledger(repository) -> None:
    workspace, *_ = _scopes(repository)
    chat = repository.lab.create_session(workspace_id=workspace.id, title="Geral")
    with pytest.raises(LabStoreRejected, match=r"lab\.tool_trace_invalid"):
        repository.lab.append_tool_trace(
            session_id=chat.id,
            workspace_id=workspace.id,
            turn_sequence=1,
            tool_name="project.read",
            arguments={},
            outcome="refused",
        )

    requested = ({"kind": "project", "id": "prj_requested"},)
    returned = ()
    trace = repository.lab.append_tool_trace(
        session_id=chat.id,
        workspace_id=workspace.id,
        turn_sequence=1,
        tool_name="project.read",
        arguments={"ref": requested[0]},
        requested_refs=requested,
        returned_refs=returned,
        outcome="refused",
        refusal_code="lab.target_not_visible",
    )
    assert trace.requested_refs == requested
    assert trace.returned_refs == returned
    assert trace.arguments_digest == sha256_json({"ref": requested[0]})
    assert trace.refusal_code == "lab.target_not_visible"
    assert {field.name for field in fields(LabToolTrace)} >= {
        "requested_refs", "returned_refs", "scope_snapshot"
    }
    with repository.unit_of_work.session() as session:
        stored = session.get(LabToolTraceRow, trace.id)
        assert stored is not None
        assert session.scalar(select(RunEventRow).where(RunEventRow.id == trace.id)) is None
        assert json.loads(stored.scope_snapshot_json)["workspace_id"] == workspace.id
