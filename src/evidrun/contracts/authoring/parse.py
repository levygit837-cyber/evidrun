"""Revision dispatch by `contract_type`, with named refusals for every rejection."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Annotated, cast

from pydantic import Field, ValidationError

from evidrun.contracts.authoring.checkpoint import CheckpointPolicyRevision
from evidrun.contracts.authoring.evaluation import EvaluationPlanRevision
from evidrun.contracts.authoring.goal import GoalRevision
from evidrun.contracts.authoring.inventory import AgentInventoryRevision
from evidrun.contracts.authoring.progress import ProgressArtifactPolicyRevision
from evidrun.contracts.authoring.protocol import InteractionProtocolRevision
from evidrun.contracts.authoring.scenario import ScenarioRevision
from evidrun.contracts.authoring.study import StudyRevision
from evidrun.contracts.authoring.workspace import WorkspaceTemplateRevision
from evidrun.contracts.base import (
    ContractType,
    RevisionEnvelope,
)
from evidrun.contracts.triage import (
    TriageError,
    TriageErrorCode,
    TriagePhase,
    TriageRejected,
)

AuthoringRevision = Annotated[
    StudyRevision
    | GoalRevision
    | ScenarioRevision
    | AgentInventoryRevision
    | WorkspaceTemplateRevision
    | InteractionProtocolRevision
    | EvaluationPlanRevision
    | CheckpointPolicyRevision
    | ProgressArtifactPolicyRevision,
    Field(discriminator="contract_type"),
]


REVISION_MODELS: dict[ContractType, type[RevisionEnvelope]] = {
    ContractType.STUDY: StudyRevision,
    ContractType.GOAL: GoalRevision,
    ContractType.SCENARIO: ScenarioRevision,
    ContractType.AGENT_INVENTORY: AgentInventoryRevision,
    ContractType.WORKSPACE_TEMPLATE: WorkspaceTemplateRevision,
    ContractType.INTERACTION_PROTOCOL: InteractionProtocolRevision,
    ContractType.EVALUATION_PLAN: EvaluationPlanRevision,
    ContractType.CHECKPOINT_POLICY: CheckpointPolicyRevision,
    ContractType.PROGRESS_ARTIFACT_POLICY: ProgressArtifactPolicyRevision,
}


def _rejected(
    code: TriageErrorCode,
    message: str,
    *,
    field_path: tuple[str, ...] = (),
    remediation: str | None = None,
) -> TriageRejected:
    return TriageRejected(
        TriageError(
            phase=TriagePhase.PARSE,
            code=code,
            message=message,
            field_path=field_path,
            remediation=remediation,
        )
    )


#: Pydantic error types that name an undeclared field rather than a bad value.
_UNDECLARED_TYPES = frozenset({"extra_forbidden", "unexpected_keyword_argument"})


def _field_path(location: Sequence[object]) -> tuple[str, ...]:
    return tuple(str(part) for part in location if not isinstance(part, int))


def _classify(error: ValidationError) -> TriageRejected:
    """Name a Pydantic failure by its structure, never by its message.

    An undeclared field is checked across every reported error, not just the first:
    a document can both add an unknown key and omit required ones, and the extra key
    is the more specific cause the caller must remove.
    """

    reported = error.errors()
    undeclared = next(
        (item for item in reported if str(item["type"]) in _UNDECLARED_TYPES), None
    )
    if undeclared is not None:
        return _rejected(
            TriageErrorCode.PARSE_FIELD_UNDECLARED,
            "O documento declara um campo que o contrato não possui.",
            field_path=_field_path(undeclared["loc"]),
            remediation="Remova o campo não declarado.",
        )
    first = reported[0]
    path = _field_path(first["loc"])
    error_type = str(first["type"])
    head = path[0] if path else ""
    if head == "revision":
        return _rejected(
            TriageErrorCode.PARSE_REVISION_INVALID,
            "A revision precisa ser um inteiro maior que zero.",
            field_path=path,
            remediation="Use 1 para a primeira revision de uma identidade.",
        )
    if head in {"logical_id", "project_id", "title"} and error_type.startswith("string_too_short"):
        return _rejected(
            TriageErrorCode.PARSE_IDENTIFIER_EMPTY,
            "Um identificador obrigatório está vazio.",
            field_path=path,
            remediation="Informe um valor legível e não vazio.",
        )
    if head == "payload" and error_type in {
        "model_type",
        "model_attributes_type",
        "dict_type",
        "missing",
    }:
        return _rejected(
            TriageErrorCode.PARSE_PAYLOAD_TYPE_INVALID,
            "O payload do contrato precisa ser um objeto do tipo declarado.",
            field_path=path,
            remediation="Envie o payload correspondente ao contract_type.",
        )
    return _rejected(
        TriageErrorCode.PARSE_SCHEMA_INVALID,
        "O documento não satisfaz o schema do contrato.",
        field_path=path,
    )


def parse_revision(document: object) -> RevisionEnvelope:
    """Return the typed revision, or refuse with a named parse error."""

    if not isinstance(document, Mapping):
        raise _rejected(
            TriageErrorCode.PARSE_DOCUMENT_NOT_OBJECT,
            "O documento de contrato precisa ser um objeto.",
            remediation="Envie um mapeamento com contract_type declarado.",
        )
    typed_document = cast(Mapping[str, object], document)
    raw_type = typed_document.get("contract_type")
    if raw_type is None:
        raise _rejected(
            TriageErrorCode.PARSE_CONTRACT_TYPE_MISSING,
            "O documento não declara contract_type.",
            field_path=("contract_type",),
            remediation="Declare o contract_type do documento.",
        )
    try:
        contract_type = ContractType(str(raw_type))
    except ValueError as exc:
        raise _rejected(
            TriageErrorCode.PARSE_CONTRACT_TYPE_UNKNOWN,
            "O contract_type declarado não existe.",
            field_path=("contract_type",),
            remediation="Use um dos tipos de contrato suportados.",
        ) from exc
    try:
        return REVISION_MODELS[contract_type].model_validate(typed_document)
    except ValidationError as exc:
        raise _classify(exc) from exc
