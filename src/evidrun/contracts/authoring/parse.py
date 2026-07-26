"""Despacho de revision por `contract_type`."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Annotated, cast

from pydantic import Field

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


def parse_revision(document: object) -> RevisionEnvelope:
    if not isinstance(document, Mapping):
        raise ValueError("contract revision must be an object")
    typed_document = cast(Mapping[str, object], document)
    raw_type = typed_document.get("contract_type")
    try:
        contract_type = ContractType(str(raw_type))
    except ValueError as exc:
        raise ValueError(f"unknown contract type: {raw_type}") from exc
    return REVISION_MODELS[contract_type].model_validate(typed_document)
