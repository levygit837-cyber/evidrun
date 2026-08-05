"""Validação pura de drafts com o parser e o compilador canônicos."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, cast

from evidrun.contracts.authoring.parse import parse_revision
from evidrun.contracts.authoring.study import StudyRevision
from evidrun.contracts.base import ContractRef, NonEmptyStr, RevisionEnvelope
from evidrun.contracts.compiler import StudyCompiler
from evidrun.contracts.lab_agent.errors import LabAgentError, LabAgentErrorCode
from evidrun.contracts.registry import ContractResolver
from evidrun.contracts.triage import TriageRejected
from evidrun.lab.protocol import (
    LabToolContext,
    LabToolRejected,
    LabToolResult,
    ToolAvailability,
)
from evidrun.shared.types import sha256_json

__all__ = [
    "DraftValidationStore",
    "ValidateDraftTool",
    "draft_error",
    "draft_validation_key",
    "validated_revision",
]

_AUTHORITY_FIELDS = frozenset(
    {"acceptance", "attestation", "authority", "decision", "human_review", "status"}
)




class DraftValidationStore(Protocol):
    """Resolver canônico mais recibos efêmeros; validar nunca persiste domínio."""

    def contract_registry(self, project_id: str | None = None) -> ContractResolver: ...

    def record_draft_validation(self, key: tuple[str, int, str, str]) -> None: ...

    def consume_draft_validation(self, key: tuple[str, int, str, str]) -> bool: ...


class _DraftResolver:
    """Sobrepõe somente a Study candidata; dependências continuam exigindo aceitação."""

    def __init__(self, draft: StudyRevision, accepted: ContractResolver) -> None:
        self._draft = draft
        self._accepted = accepted

    def resolve(self, reference: ContractRef) -> RevisionEnvelope:
        if reference == self._draft.ref:
            return self._draft
        return self._accepted.resolve(reference)


def draft_error(
    code: LabAgentErrorCode,
    message: str,
    remediation: str,
    *,
    field_path: tuple[str, ...] = (),
    tool_name: str,
) -> LabToolRejected:
    return LabToolRejected(
        LabAgentError(
            stage=code.stage,
            code=code,
            message=message,
            remediation=remediation,
            field_path=field_path,
            tool_name=tool_name,
        )
    )


def draft_validation_key(
    *,
    contract_type: object,
    document: object,
    context: LabToolContext,
) -> tuple[str, int, str, str]:
    """Identifica exatamente o documento validado dentro do turno e do scope."""

    project_id: NonEmptyStr | None = context.scope.project_id
    if project_id is None:
        raise ValueError("draft validation key requires project scope")
    fingerprint = sha256_json(
        {
            "contract_type": contract_type,
            "document": document,
            "project_id": project_id,
        }
    )
    return (context.session_id, context.turn_sequence, project_id, fingerprint)


def _authority_field(value: object) -> tuple[str, ...] | None:
    if isinstance(value, Mapping):
        mapping = cast(Mapping[object, object], value)
        for key, item in mapping.items():
            path = (str(key),)
            if str(key) in _AUTHORITY_FIELDS:
                return path
            nested = _authority_field(item)
            if nested is not None:
                return (*path, *nested)
    elif isinstance(value, list | tuple):
        sequence = cast(list[object] | tuple[object, ...], value)
        for index, item in enumerate(sequence):
            nested = _authority_field(item)
            if nested is not None:
                return (str(index), *nested)
    return None


def validated_revision(
    *,
    contract_type: str,
    document: object,
    project_id: str,
    store: DraftValidationStore,
    tool_name: str,
) -> RevisionEnvelope:
    """Herda o Project, executa o parser público e compila Studies sem persistir."""

    forbidden = _authority_field(document)
    if forbidden is not None:
        raise draft_error(
            LabAgentErrorCode.AUTHORITY_HUMAN_DECISION_REQUIRED,
            "O draft tenta declarar uma decisão ou autoridade humana.",
            "Remova o campo de decisão e registre um pedido de aprovação.",
            field_path=("document", *forbidden),
            tool_name=tool_name,
        )

    effective_document: object = document
    if isinstance(document, Mapping):
        typed_document = cast(Mapping[str, object], document)
        if "project_id" in typed_document and typed_document["project_id"] != project_id:
            raise draft_error(
                LabAgentErrorCode.DRAFT_SCOPE_OVERRIDE_FORBIDDEN,
                "O draft tenta declarar um Project divergente da sessão.",
                "Use o Project desta sessão ou remova project_id do documento.",
                field_path=("document", "project_id"),
                tool_name=tool_name,
            )
        inherited_document = dict(typed_document)
        inherited_document["project_id"] = project_id
        effective_document = inherited_document

    try:
        revision = parse_revision(effective_document)
    except TriageRejected as exc:
        raise _translated_refusal(exc, tool_name=tool_name) from exc
    if revision.ref.contract_type.value != contract_type:
        raise draft_error(
            LabAgentErrorCode.DRAFT_VALIDATION_FAILED,
            "O contract_type do argumento diverge do documento.",
            "Use o mesmo contract_type no argumento e no documento.",
            field_path=("contract_type",),
            tool_name=tool_name,
        )
    if isinstance(revision, StudyRevision):
        accepted = store.contract_registry(project_id)
        try:
            StudyCompiler(_DraftResolver(revision, accepted)).compile(revision)
        except TriageRejected as exc:
            raise _translated_refusal(exc, tool_name=tool_name) from exc
    return revision


def _translated_refusal(rejected: TriageRejected, *, tool_name: str) -> LabToolRejected:
    """Traduz a recusa canônica para o catálogo fechado do Lab Agent.

    O parser e o compilador recusam com códigos `parse.*` e `compile.*`, que pertencem ao
    catálogo de triage da superfície humana. Deixá-los escapar crus quebraria o catálogo
    fechado do Lab Agent e faria uma entrada inválida atravessar o caminho reservado a
    falhas genuínas de execução. O contrato classifica documento que não satisfaz seu tipo
    como `draft.validation_failed`: recusa que volta ao modelo para correção, não terminal.

    A mensagem e a `field_path` canônicas são preservadas porque são o conteúdo acionável;
    só o código passa a ser o do catálogo que o consumidor do Lab Agent conhece.
    """
    canonical = rejected.error
    return draft_error(
        LabAgentErrorCode.DRAFT_VALIDATION_FAILED,
        canonical.message,
        canonical.remediation or "Corrija o documento para satisfazer o contrato declarado.",
        field_path=("document", *canonical.field_path),
        tool_name=tool_name,
    )


class ValidateDraftTool:
    name = "validate_draft"
    availability = ToolAvailability()

    def __init__(self, store: DraftValidationStore) -> None:
        self._store = store

    def provider_schema(self) -> Mapping[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "contract_type": {"type": "string"},
                "document": {"type": "object"},
            },
            "required": ["contract_type", "document"],
        }

    def execute(self, arguments: Mapping[str, Any], context: LabToolContext) -> LabToolResult:
        project_id: NonEmptyStr | None = context.scope.project_id
        if project_id is None:
            raise draft_error(
                LabAgentErrorCode.SCOPE_PROJECT_REQUIRED,
                "Esta operação exige uma Project chat; a sessão atual é General.",
                "Peça ao humano para abrir uma Project chat antes de validar o draft.",
                tool_name=self.name,
            )
        revision = validated_revision(
            contract_type=str(arguments["contract_type"]),
            document=arguments["document"],
            project_id=project_id,
            store=self._store,
            tool_name=self.name,
        )
        self._store.record_draft_validation(
            draft_validation_key(
                contract_type=arguments["contract_type"],
                document=arguments["document"],
                context=context,
            )
        )
        return LabToolResult(
            content={
                "valid": True,
                "contract_type": revision.ref.contract_type.value,
                "digest": revision.digest,
                "normalized": revision.semantic_document(),
            }
        )
