"""Cenário e input bindings: o que existe, e para quem é visível."""

from __future__ import annotations

from typing import Literal

from pydantic import model_validator

from evidrun.contracts.base import (
    ArtifactRef,
    ContractModel,
    ContractType,
    NonEmptyStr,
    RevisionEnvelope,
)


class InputBinding(ContractModel):
    id: NonEmptyStr
    role: NonEmptyStr
    source: ArtifactRef
    visibility: Literal["subject", "evaluator", "laboratory", "subject_and_evaluator"]
    mount_access: Literal["read_only", "read_write"] = "read_only"
    mount_name: NonEmptyStr | None = None


class ScenarioSpec(ContractModel):
    description: NonEmptyStr
    input_bindings: tuple[InputBinding, ...]
    observable_conditions: tuple[NonEmptyStr, ...] = ()
    limitations: tuple[NonEmptyStr, ...] = ()
    provenance: tuple[NonEmptyStr, ...] = ()

    @model_validator(mode="after")
    def validate_binding_ids(self) -> ScenarioSpec:
        ids = [item.id for item in self.input_bindings]
        if not ids:
            raise ValueError("scenario requires at least one input binding")
        if len(ids) != len(set(ids)):
            raise ValueError("scenario input binding ids must be unique")
        return self


class ScenarioRevision(RevisionEnvelope):
    contract_type: Literal[ContractType.SCENARIO] = ContractType.SCENARIO
    payload: ScenarioSpec
