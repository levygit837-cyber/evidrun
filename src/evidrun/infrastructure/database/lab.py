"""Store tipado de sessão, mensagem e rastro do Lab Agent."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from evidrun.infrastructure.database import clock
from evidrun.infrastructure.database.lab_errors import (
    invalid_message_role,
    invalid_scope,
    invalid_trace,
    not_visible,
)
from evidrun.infrastructure.database.models import (
    ChatMessageRow,
    ChatSessionRow,
    ComparisonRow,
    ContractRevisionRow,
    ExperimentRevisionRow,
    LabToolTraceRow,
    ProjectRow,
    RunRow,
    RunSpecRow,
    WorkspaceRow,
)
from evidrun.infrastructure.database.timestamps import aware_utc
from evidrun.infrastructure.database.unit_of_work import UnitOfWork
from evidrun.shared.types import canonical_json, new_id, sha256_json

__all__ = [
    "LabAgentStore",
    "LabMessage",
    "LabSession",
    "LabToolTrace",
    "ProjectNavigationItem",
]

_FOCUS_KINDS = frozenset({"study", "run", "comparison"})
_MESSAGE_ROLES = frozenset({"human", "agent", "system_note"})
_TRACE_OUTCOMES = frozenset({"completed", "refused", "failed"})


@dataclass(frozen=True, slots=True)
class LabSession:
    id: str
    workspace_id: str
    project_id: str | None
    focus_kind: str | None
    focus_id: str | None
    title: str
    created_at: datetime

    def scope_document(self) -> dict[str, str | None]:
        return {
            "workspace_id": self.workspace_id,
            "project_id": self.project_id,
            "focus_kind": self.focus_kind,
            "focus_id": self.focus_id,
        }


@dataclass(frozen=True, slots=True)
class LabMessage:
    id: str
    session_id: str
    role: str
    content: str
    sequence: int
    created_at: datetime


@dataclass(frozen=True, slots=True)
class LabToolTrace:
    id: str
    session_id: str
    turn_sequence: int
    tool_name: str
    arguments_digest: str
    requested_refs: tuple[Any, ...]
    returned_refs: tuple[Any, ...]
    outcome: str
    refusal_code: str | None
    scope_snapshot: dict[str, str | None]
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ProjectNavigationItem:
    id: str
    name: str
    created_at: datetime


class LabAgentStore:
    """Impõe pertencimento no write e novamente ao hidratar qualquer sessão."""

    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self.unit_of_work = unit_of_work

    def create_session(
        self,
        *,
        workspace_id: str,
        title: str,
        project_id: str | None = None,
        focus_kind: str | None = None,
        focus_id: str | None = None,
    ) -> LabSession:
        with self.unit_of_work.session() as session:
            self._validate_scope(
                session,
                workspace_id=workspace_id,
                project_id=project_id,
                focus_kind=focus_kind,
                focus_id=focus_id,
            )
            row = ChatSessionRow(
                id=new_id("chat"),
                workspace_id=workspace_id,
                project_id=project_id,
                focus_kind=focus_kind,
                focus_id=focus_id,
                scope_type=None,
                scope_id=None,
                title=title,
                created_at=clock.utc_now(),
            )
            session.add(row)
            session.commit()
            return self._session_from_row(session, row, workspace_id=workspace_id)

    def get_session(self, *, session_id: str, workspace_id: str) -> LabSession:
        with self.unit_of_work.session() as session:
            row = session.get(ChatSessionRow, session_id)
            if row is None or row.workspace_id != workspace_id:
                raise not_visible()
            return self._session_from_row(session, row, workspace_id=workspace_id)

    def list_sessions(self, *, workspace_id: str) -> tuple[LabSession, ...]:
        if not workspace_id:
            raise invalid_scope("workspace_id é obrigatório.", field="workspace_id")
        with self.unit_of_work.session() as session:
            if session.get(WorkspaceRow, workspace_id) is None:
                raise not_visible()
            rows = session.scalars(
                select(ChatSessionRow)
                .where(ChatSessionRow.workspace_id == workspace_id)
                .order_by(ChatSessionRow.created_at, ChatSessionRow.id)
            )
            return tuple(
                self._session_from_row(session, row, workspace_id=workspace_id) for row in rows
            )

    def list_navigation_projects(
        self, *, session_id: str, workspace_id: str
    ) -> tuple[ProjectNavigationItem, ...]:
        with self.unit_of_work.session() as session:
            chat = self._load_session(session, session_id, workspace_id)
            if chat.project_id is not None:
                raise invalid_scope("Navegação de Projects exige General chat.")
            rows = session.scalars(
                select(ProjectRow)
                .where(ProjectRow.workspace_id == workspace_id)
                .order_by(ProjectRow.created_at, ProjectRow.id)
            )
            return tuple(
                ProjectNavigationItem(row.id, row.name, aware_utc(row.created_at)) for row in rows
            )

    def require_project(
        self, *, session_id: str, workspace_id: str, project_id: str
    ) -> ProjectNavigationItem:
        with self.unit_of_work.session() as session:
            chat = self._load_session(session, session_id, workspace_id)
            if chat.project_id is None or project_id != chat.project_id:
                raise not_visible()
            row = session.get(ProjectRow, project_id)
            if row is None or row.workspace_id != workspace_id:
                raise not_visible()
            return ProjectNavigationItem(row.id, row.name, aware_utc(row.created_at))

    def append_message(
        self, *, session_id: str, workspace_id: str, role: str, content: str
    ) -> LabMessage:
        if role not in _MESSAGE_ROLES:
            raise invalid_message_role()
        with self.unit_of_work.immediate() as session:
            self._load_session(session, session_id, workspace_id)
            last = session.scalar(
                select(func.max(ChatMessageRow.sequence)).where(
                    ChatMessageRow.session_id == session_id
                )
            )
            row = ChatMessageRow(
                id=new_id("msg"),
                session_id=session_id,
                role=role,
                content=content,
                sequence=1 if last is None else last + 1,
                created_at=clock.utc_now(),
            )
            session.add(row)
            session.commit()
            return self._message_from_row(row)

    def list_messages(self, *, session_id: str, workspace_id: str) -> tuple[LabMessage, ...]:
        with self.unit_of_work.session() as session:
            self._load_session(session, session_id, workspace_id)
            rows = tuple(
                session.scalars(
                    select(ChatMessageRow)
                    .where(ChatMessageRow.session_id == session_id)
                    .order_by(ChatMessageRow.sequence)
                )
            )
            messages = tuple(self._message_from_row(row) for row in rows)
            if tuple(item.sequence for item in messages) != tuple(range(1, len(messages) + 1)):
                raise invalid_trace("A sequência persistida de mensagens contém lacuna.")
            return messages

    def append_tool_trace(
        self,
        *,
        session_id: str,
        workspace_id: str,
        turn_sequence: int,
        tool_name: str,
        arguments: Any,
        requested_refs: tuple[Any, ...] = (),
        returned_refs: tuple[Any, ...] = (),
        outcome: str,
        refusal_code: str | None = None,
    ) -> LabToolTrace:
        self._validate_trace(turn_sequence, tool_name, outcome, refusal_code)
        with self.unit_of_work.immediate() as session:
            chat = self._load_session(session, session_id, workspace_id)
            row = LabToolTraceRow(
                id=new_id("labtrace"),
                session_id=session_id,
                turn_sequence=turn_sequence,
                tool_name=tool_name,
                arguments_digest=sha256_json(arguments),
                requested_refs_json=canonical_json(list(requested_refs)),
                returned_refs_json=canonical_json(list(returned_refs)),
                outcome=outcome,
                refusal_code=refusal_code,
                scope_snapshot_json=canonical_json(chat.scope_document()),
                created_at=clock.utc_now(),
            )
            session.add(row)
            session.commit()
            return self._trace_from_row(row, chat)

    def list_tool_traces(self, *, session_id: str, workspace_id: str) -> tuple[LabToolTrace, ...]:
        with self.unit_of_work.session() as session:
            chat = self._load_session(session, session_id, workspace_id)
            rows = session.scalars(
                select(LabToolTraceRow)
                .where(LabToolTraceRow.session_id == session_id)
                .order_by(LabToolTraceRow.created_at, LabToolTraceRow.id)
            )
            return tuple(self._trace_from_row(row, chat) for row in rows)

    def _load_session(self, session: Session, session_id: str, workspace_id: str) -> LabSession:
        row = session.get(ChatSessionRow, session_id)
        if row is None or row.workspace_id != workspace_id:
            raise not_visible()
        return self._session_from_row(session, row, workspace_id=workspace_id)

    def _session_from_row(
        self, session: Session, row: ChatSessionRow, *, workspace_id: str
    ) -> LabSession:
        if row.workspace_id != workspace_id:
            raise not_visible()
        self._validate_scope(
            session,
            workspace_id=row.workspace_id,
            project_id=row.project_id,
            focus_kind=row.focus_kind,
            focus_id=row.focus_id,
        )
        return LabSession(
            id=row.id,
            workspace_id=row.workspace_id,
            project_id=row.project_id,
            focus_kind=row.focus_kind,
            focus_id=row.focus_id,
            title=row.title,
            created_at=aware_utc(row.created_at),
        )

    def _validate_scope(
        self,
        session: Session,
        *,
        workspace_id: str,
        project_id: str | None,
        focus_kind: str | None,
        focus_id: str | None,
    ) -> None:
        if not workspace_id:
            raise invalid_scope("workspace_id é obrigatório.", field="workspace_id")
        if session.get(WorkspaceRow, workspace_id) is None:
            raise not_visible()
        if (focus_kind is None) != (focus_id is None):
            raise invalid_scope(
                "focus_kind e focus_id precisam estar ambos presentes ou ambos ausentes.",
                field="focus_kind",
            )
        if focus_kind is not None and focus_kind not in _FOCUS_KINDS:
            raise invalid_scope("focus_kind desconhecido.", field="focus_kind")
        if focus_kind is not None and project_id is None:
            raise invalid_scope("Um foco exige project_id.", field="project_id")
        if project_id is None:
            return
        project = session.get(ProjectRow, project_id)
        if project is None or project.workspace_id != workspace_id:
            raise not_visible()
        if (
            focus_kind is not None
            and self._project_for_focus(session, focus_kind, focus_id) != project_id
        ):
            raise not_visible()

    def _project_for_focus(self, session: Session, kind: str, focus_id: str | None) -> str:
        if focus_id is None:
            raise invalid_scope("focus_id é obrigatório.", field="focus_id")
        if kind == "study":
            study = session.get(ContractRevisionRow, focus_id)
            if study is None or study.contract_type != "study":
                raise not_visible()
            return study.project_id
        if kind == "comparison":
            comparison = session.get(ComparisonRow, focus_id)
            revision = (
                None
                if comparison is None
                else session.get(ExperimentRevisionRow, comparison.experiment_revision_id)
            )
            if revision is None:
                raise not_visible()
            return revision.project_id
        run = session.get(RunRow, focus_id)
        if run is None:
            raise not_visible()
        candidates: set[str] = set()
        if run.experiment_revision_id is not None:
            experiment = session.get(ExperimentRevisionRow, run.experiment_revision_id)
            if experiment is not None:
                candidates.add(experiment.project_id)
        if run.run_spec_id is not None:
            spec = session.get(RunSpecRow, run.run_spec_id)
            if spec is not None:
                try:
                    study_ref = json.loads(spec.spec_json)["study_ref"]
                    logical_id = str(study_ref["logical_id"])
                    revision_number = int(study_ref["revision"])
                except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                    raise not_visible() from exc
                study = session.scalar(
                    select(ContractRevisionRow).where(
                        ContractRevisionRow.contract_type == "study",
                        ContractRevisionRow.logical_id == logical_id,
                        ContractRevisionRow.revision == revision_number,
                    )
                )
                if study is not None:
                    candidates.add(study.project_id)
        if len(candidates) != 1:
            raise not_visible()
        return candidates.pop()

    @staticmethod
    def _message_from_row(row: ChatMessageRow) -> LabMessage:
        if row.role not in _MESSAGE_ROLES:
            raise invalid_message_role()
        if row.sequence < 1:
            raise invalid_trace("A sequência persistida da mensagem é inválida.")
        return LabMessage(
            row.id,
            row.session_id,
            row.role,
            row.content,
            row.sequence,
            aware_utc(row.created_at),
        )

    @staticmethod
    def _validate_trace(
        turn_sequence: int, tool_name: str, outcome: str, refusal_code: str | None
    ) -> None:
        if turn_sequence < 1:
            raise invalid_trace("turn_sequence precisa ser positivo.", field="turn_sequence")
        if not tool_name:
            raise invalid_trace("tool_name é obrigatório.", field="tool_name")
        if outcome not in _TRACE_OUTCOMES:
            raise invalid_trace("outcome desconhecido.", field="outcome")
        if outcome == "refused" and not refusal_code:
            raise invalid_trace("Toda recusa exige refusal_code.", field="refusal_code")
        if outcome != "refused" and refusal_code is not None:
            raise invalid_trace("refusal_code só acompanha outcome refused.", field="refusal_code")

    def _trace_from_row(self, row: LabToolTraceRow, chat: LabSession) -> LabToolTrace:
        self._validate_trace(row.turn_sequence, row.tool_name, row.outcome, row.refusal_code)
        try:
            requested_value: object = json.loads(row.requested_refs_json)
            returned_value: object = json.loads(row.returned_refs_json)
            snapshot_value: object = json.loads(row.scope_snapshot_json)
        except json.JSONDecodeError as exc:
            raise invalid_trace("O rastro persistido contém JSON inválido.") from exc
        if not isinstance(requested_value, list) or not isinstance(returned_value, list):
            raise invalid_trace("Refs persistidas precisam ser listas.")
        if not isinstance(snapshot_value, dict):
            raise invalid_trace("O snapshot persistido precisa ser objeto.")
        requested = cast(list[Any], requested_value)
        returned = cast(list[Any], returned_value)
        raw_snapshot = cast(dict[Any, Any], snapshot_value)
        if not all(
            isinstance(key, str) and (value is None or isinstance(value, str))
            for key, value in raw_snapshot.items()
        ):
            raise invalid_trace("O snapshot persistido é inválido.")
        snapshot = cast(dict[str, str | None], raw_snapshot)
        if snapshot != chat.scope_document():
            raise invalid_trace("O snapshot persistido diverge do scope imutável da sessão.")
        if len(row.arguments_digest) != 64 or any(
            c not in "0123456789abcdef" for c in row.arguments_digest
        ):
            raise invalid_trace("arguments_digest persistido é inválido.")
        return LabToolTrace(
            row.id,
            row.session_id,
            row.turn_sequence,
            row.tool_name,
            row.arguments_digest,
            tuple(requested),
            tuple(returned),
            row.outcome,
            row.refusal_code,
            snapshot,
            aware_utc(row.created_at),
        )
