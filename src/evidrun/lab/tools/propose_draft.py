"""Registro de revision draft somente depois da validação canônica."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from evidrun.contracts.base import NonEmptyStr, RevisionEnvelope
from evidrun.contracts.lab_agent.errors import LabAgentErrorCode
from evidrun.lab.protocol import LabToolContext, LabToolResult, ToolAvailability
from evidrun.lab.tools.validate_draft import (
    DraftValidationStore,
    draft_error,
    draft_validation_key,
    validated_revision,
)

__all__ = ["DraftRevisionRecord", "DraftRevisionStore", "ProposeDraftTool"]


@dataclass(frozen=True, slots=True)
class DraftRevisionRecord:
    id: str
    status: str
    digest: str
    project_id: str
    decision: str | None = None


class DraftRevisionStore(DraftValidationStore, Protocol):
    """A superfície injetada não expõe decisão: apenas validação e registro inicial."""

    def save_contract_revision(
        self, revision: RevisionEnvelope, *, status: str = "draft"
    ) -> DraftRevisionRecord: ...


class ProposeDraftTool:
    name = "propose_draft"
    availability = ToolAvailability()

    def __init__(self, store: DraftRevisionStore) -> None:
        self._store = store

    def provider_schema(self) -> Mapping[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "contract_type": {"type": "string"},
                "document": {"type": "object"},
                "informed_by": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 100,
                },
            },
            "required": ["contract_type", "document", "informed_by"],
        }

    def execute(self, arguments: Mapping[str, Any], context: LabToolContext) -> LabToolResult:
        project_id: NonEmptyStr | None = context.scope.project_id
        if project_id is None:
            raise draft_error(
                LabAgentErrorCode.SCOPE_PROJECT_REQUIRED,
                "Esta operação exige uma Project chat; a sessão atual é General.",
                "Peça ao humano para abrir uma Project chat antes de propor o draft.",
                tool_name=self.name,
            )
        if not self._store.consume_draft_validation(
            draft_validation_key(
                contract_type=arguments["contract_type"],
                document=arguments["document"],
                context=context,
            )
        ):
            raise draft_error(
                LabAgentErrorCode.DRAFT_NOT_VALIDATED,
                "A proposta não passou por validação neste turno antes do registro.",
                "Valide este documento e só então registre a proposta sem alterá-lo.",
                field_path=("document",),
                tool_name=self.name,
            )
        validated = validated_revision(
            contract_type=str(arguments["contract_type"]),
            document=arguments["document"],
            project_id=project_id,
            store=self._store,
            tool_name=self.name,
        )
        row = self._store.save_contract_revision(validated, status="draft")
        informed_by = tuple(str(item) for item in arguments["informed_by"])
        return LabToolResult(
            content={
                "revision_ref": row.id,
                "contract_type": validated.ref.contract_type.value,
                "digest": row.digest,
                "status": row.status,
                "project_id": row.project_id,
                "informed_by": informed_by,
            },
            # `informed_by` NÃO entra em requested_refs. A diferença entre refs pedidas e
            # devolvidas é a evidência de que o enforcement recusou uma leitura; declarar
            # aqui procedência citada pelo modelo como leitura tentada faria o rastro
            # afirmar uma recusa que nunca houve. Esta tool não lê por ref: ela cria uma,
            # e a ref criada é o que ela devolve.
            requested_refs=(),
            returned_refs=(row.id,),
        )
