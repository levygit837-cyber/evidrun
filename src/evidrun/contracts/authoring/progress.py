"""Progress Artifact policy: triggers and the derived summary definition."""

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


class CheckpointReachedProgressTrigger(ContractModel):
    kind: Literal["checkpoint_reached"] = "checkpoint_reached"
    checkpoint_definition_id: NonEmptyStr


class SubjectTurnIntervalProgressTrigger(ContractModel):
    kind: Literal["subject_turn_interval"] = "subject_turn_interval"
    counted_event_type: Literal["subject.responded"] = "subject.responded"
    every_n_turns: int = Field(gt=0)


ProgressArtifactTrigger = Annotated[
    CheckpointReachedProgressTrigger | SubjectTurnIntervalProgressTrigger,
    Field(discriminator="kind"),
]


class ProgressArtifactDefinition(ContractModel):
    id: NonEmptyStr
    label: NonEmptyStr
    trigger: ProgressArtifactTrigger
    summarizer_ref: CapabilityDescriptorRef
    minimum_interface_version: NonEmptyStr = "1"
    authority_constraints: tuple[
        Literal["read_current_run_ledger_prefix"],
        Literal["write_progress_artifact_only"],
        Literal["no_subject_feedback"],
    ] = (
        "read_current_run_ledger_prefix",
        "write_progress_artifact_only",
        "no_subject_feedback",
    )
    input_scope: Literal["complete_run_ledger_prefix"] = "complete_run_ledger_prefix"
    max_output_characters: int = Field(default=12_000, gt=0)
    audience: Literal["laboratory_human"] = "laboratory_human"


class ProgressArtifactPolicySpec(ContractModel):
    definitions: tuple[ProgressArtifactDefinition, ...]
    limitations: tuple[NonEmptyStr, ...] = ()

    @model_validator(mode="after")
    def validate_definitions(self) -> ProgressArtifactPolicySpec:
        ids = [item.id for item in self.definitions]
        if not ids:
            raise ValueError("progress artifact policy requires at least one definition")
        if len(ids) != len(set(ids)):
            raise ValueError("progress artifact definition ids must be unique")
        return self


class ProgressArtifactPolicyRevision(RevisionEnvelope):
    contract_type: Literal[ContractType.PROGRESS_ARTIFACT_POLICY] = (
        ContractType.PROGRESS_ARTIFACT_POLICY
    )
    payload: ProgressArtifactPolicySpec
