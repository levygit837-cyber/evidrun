"""Agent inventory: declared capability and runtime requirements."""

from __future__ import annotations

from typing import Literal

from pydantic import model_validator

from evidrun.contracts.base import (
    ArtifactRef,
    CapabilityDescriptorRef,
    ContractModel,
    ContractType,
    NonEmptyStr,
    RevisionEnvelope,
)


class CapabilityRequirement(ContractModel):
    kind: Literal["tool", "skill"]
    capability_ref: CapabilityDescriptorRef
    required: bool = True
    minimum_interface_version: NonEmptyStr
    requested_permissions: tuple[NonEmptyStr, ...] = ()
    exposure: Literal["schema_only", "instructions", "instructions_and_schema"]
    instruction_refs: tuple[ArtifactRef, ...] = ()
    authority_constraints: tuple[NonEmptyStr, ...] = ()


class RuntimeRequirement(ContractModel):
    capability: NonEmptyStr
    required: bool = True


class AgentInventorySpec(ContractModel):
    subject_id: NonEmptyStr
    runner_ref: CapabilityDescriptorRef
    provider_profile_id: NonEmptyStr | None = None
    capability_requirements: tuple[CapabilityRequirement, ...] = ()
    runtime_requirements: tuple[RuntimeRequirement, ...] = ()

    @model_validator(mode="after")
    def validate_capability_keys(self) -> AgentInventorySpec:
        keys = [
            (item.kind, item.capability_ref.namespace, item.capability_ref.name)
            for item in self.capability_requirements
        ]
        if len(keys) != len(set(keys)):
            raise ValueError("capability requirements must be unique")
        return self


class AgentInventoryRevision(RevisionEnvelope):
    contract_type: Literal[ContractType.AGENT_INVENTORY] = ContractType.AGENT_INVENTORY
    payload: AgentInventorySpec
