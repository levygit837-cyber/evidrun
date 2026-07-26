"""Política de checkpoint: gatilhos, captura e definições."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator

from evidrun.contracts.base import (
    CapabilityDescriptorRef,
    ContractModel,
    ContractType,
    NonEmptyStr,
    RevisionEnvelope,
)


class ManualCheckpointTrigger(ContractModel):
    kind: Literal["manual"] = "manual"


class CheckpointEventTrigger(ContractModel):
    kind: Literal["event"] = "event"
    event_type: NonEmptyStr


class ProtocolNodeCheckpointTrigger(ContractModel):
    kind: Literal["protocol_node"] = "protocol_node"
    node_id: NonEmptyStr


class PredicateCheckpointTrigger(ContractModel):
    kind: Literal["predicate"] = "predicate"
    predicate_ref: CapabilityDescriptorRef


CheckpointTrigger = Annotated[
    ManualCheckpointTrigger
    | CheckpointEventTrigger
    | ProtocolNodeCheckpointTrigger
    | PredicateCheckpointTrigger,
    Field(discriminator="kind"),
]


class CheckpointCaptureSpec(ContractModel):
    context_snapshot: bool = False
    protocol_state: bool = False
    artifact_manifest: bool = False
    workspace_snapshot: bool = False
    provider_resolution: bool = False
    agent_inventory: bool = False
    evaluation_records: bool = False


class CheckpointDefinition(ContractModel):
    id: NonEmptyStr
    label: NonEmptyStr
    order: int = Field(gt=0)
    trigger: CheckpointTrigger
    validator_refs: tuple[CapabilityDescriptorRef, ...] = ()
    capture: CheckpointCaptureSpec
    required: bool = False
    compatibility_tags: tuple[NonEmptyStr, ...] = ()


class CheckpointPolicySpec(ContractModel):
    definitions: tuple[CheckpointDefinition, ...]

    @model_validator(mode="after")
    def validate_definitions(self) -> CheckpointPolicySpec:
        ids = [item.id for item in self.definitions]
        orders = [item.order for item in self.definitions]
        if not ids:
            raise ValueError("checkpoint policy requires at least one definition")
        if len(ids) != len(set(ids)):
            raise ValueError("checkpoint definition ids must be unique")
        if len(orders) != len(set(orders)):
            raise ValueError("checkpoint definition order must be unique")
        return self


class CheckpointPolicyRevision(RevisionEnvelope):
    contract_type: Literal[ContractType.CHECKPOINT_POLICY] = ContractType.CHECKPOINT_POLICY
    payload: CheckpointPolicySpec
