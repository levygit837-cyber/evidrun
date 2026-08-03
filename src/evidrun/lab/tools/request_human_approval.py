"""Pedido de aprovação como transição verificável de draft para proposed."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from evidrun.contracts.base import NonEmptyStr, RevisionEnvelope
from evidrun.contracts.lab_agent.errors import (
    LabAgentErrorCode,
    LabAgentTargetSituation,
    target_not_visible,
)
from evidrun.lab.protocol import LabToolContext, LabToolResult, ToolAvailability
from evidrun.lab.tools.propose_draft import DraftRevisionRecord
from evidrun.lab.tools.validate_draft import DraftToolRejected, draft_error

__all__ = ["ApprovalRequestStore", "RequestHumanApprovalTool"]


class ApprovalRequestStore(Protocol):
    """Somente lê e promove a proposta; nenhuma decisão existe nesta superfície."""

    def get_contract_revision(self, revision_id: str) -> RevisionEnvelope: ...

    def get_contract_revision_record(self, revision_id: str) -> DraftRevisionRecord: ...

    def save_contract_revision(
        self, revision: RevisionEnvelope, *, status: str = "draft"
    ) -> DraftRevisionRecord: ...


class RequestHumanApprovalTool:
    name = "request_human_approval"
    availability = ToolAvailability()

    def __init__(self, store: ApprovalRequestStore) -> None:
        self._store = store

    def provider_schema(self) -> Mapping[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "revision_ref": {"type": "string"},
                "rationale": {"type": "string", "minLength": 1, "maxLength": 4000},
            },
            "required": ["revision_ref", "rationale"],
        }

    def execute(self, arguments: Mapping[str, Any], context: LabToolContext) -> LabToolResult:
        project_id: NonEmptyStr | None = context.scope.project_id
        if project_id is None:
            raise draft_error(
                LabAgentErrorCode.SCOPE_PROJECT_REQUIRED,
                "Esta operação exige uma Project chat; a sessão atual é General.",
                "Peça ao humano para abrir uma Project chat antes de solicitar aprovação.",
                tool_name=self.name,
            )
        revision_ref = str(arguments["revision_ref"])
        try:
            revision = self._store.get_contract_revision(revision_ref)
        except KeyError as exc:
            raise DraftToolRejected(
                target_not_visible(
                    LabAgentTargetSituation.ABSENT,
                    field_path=("revision_ref",),
                    tool_name=self.name,
                )
            ) from exc
        if revision.project_id != project_id:
            raise DraftToolRejected(
                target_not_visible(
                    LabAgentTargetSituation.SIBLING_PROJECT,
                    field_path=("revision_ref",),
                    tool_name=self.name,
                )
            )
        existing = self._store.get_contract_revision_record(revision_ref)
        if existing.status != "draft" or existing.decision is not None:
            raise DraftToolRejected(
                target_not_visible(
                    LabAgentTargetSituation.ABSENT,
                    field_path=("revision_ref",),
                    tool_name=self.name,
                )
            )
        row = self._store.save_contract_revision(revision, status="proposed")
        return LabToolResult(
            content={
                "revision_ref": row.id,
                "digest": row.digest,
                "project_id": row.project_id,
                "status": row.status,
                "rationale": str(arguments["rationale"]),
                "decision": row.decision,
            },
            requested_refs=(revision_ref,),
            returned_refs=(revision_ref,),
        )
