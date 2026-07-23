from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Literal, cast

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    computed_field,
    field_validator,
    model_validator,
)

from evidrun.shared.types import Classification, sha256_json

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Digest = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


def _require_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("timestamp must be timezone-aware UTC")
    return value


UtcDateTime = Annotated[datetime, AfterValidator(_require_utc)]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def semantic_model_dump(model: BaseModel) -> dict[str, object]:
    """Return JSON-ready contract content without computed, null, or empty modules."""
    document = cast(
        dict[str, object],
        model.model_dump(mode="json", exclude_computed_fields=True, exclude_none=True),
    )

    def normalize(value: object) -> object:
        if isinstance(value, Mapping):
            mapping = cast(Mapping[object, object], value)
            normalized = {
                str(key): normalize(item)
                for key, item in mapping.items()
                if item is not None
            }
            return {
                key: item
                for key, item in normalized.items()
                if item != [] and item != {}
            }
        if isinstance(value, list):
            return [normalize(item) for item in cast(list[object], value)]
        return value

    normalized = normalize(document)
    if not isinstance(normalized, dict):
        raise TypeError("contract serialization must produce an object")
    return cast(dict[str, object], normalized)


class ContractType(StrEnum):
    STUDY = "study"
    GOAL = "goal"
    SCENARIO = "scenario"
    AGENT_INVENTORY = "agent_inventory"
    WORKSPACE_TEMPLATE = "workspace_template"
    INTERACTION_PROTOCOL = "interaction_protocol"
    EVALUATION_PLAN = "evaluation_plan"
    CHECKPOINT_POLICY = "checkpoint_policy"


class RevisionStatus(StrEnum):
    DRAFT = "draft"
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class ContractRef(ContractModel):
    contract_type: ContractType
    logical_id: NonEmptyStr
    revision: int = Field(gt=0)
    digest: Digest


class ArtifactRef(ContractModel):
    artifact_id: NonEmptyStr
    digest: Digest
    media_type: NonEmptyStr
    classification: Classification = Classification.INTERNAL
    locator: NonEmptyStr | None = None


class CapabilityDescriptorRef(ContractModel):
    namespace: NonEmptyStr
    name: NonEmptyStr
    version: NonEmptyStr
    digest: Digest


class ExtensionRef(ContractModel):
    namespace: NonEmptyStr
    slot: NonEmptyStr
    schema_ref: ArtifactRef
    schema_version: NonEmptyStr
    payload_ref: ArtifactRef
    digest: Digest
    classification: Classification
    required: bool = True

    @model_validator(mode="after")
    def validate_payload_identity(self) -> ExtensionRef:
        if self.digest != self.payload_ref.digest:
            raise ValueError("extension digest must match its payload artifact")
        if self.classification != self.payload_ref.classification:
            raise ValueError("extension classification must match its payload artifact")
        return self


class EvidenceRef(ContractModel):
    ref: NonEmptyStr

    @field_validator("ref")
    @classmethod
    def validate_scheme(cls, value: str) -> str:
        if not value.startswith(("run:", "event:", "artifact:")):
            raise ValueError("evidence refs must use run:, event:, or artifact:")
        return value


class RevisionEnvelope(ContractModel):
    """Common semantic fields for immutable authoring revisions."""

    schema_version: Literal["1"] = "1"
    logical_id: NonEmptyStr
    revision: int = Field(gt=0)
    project_id: NonEmptyStr
    title: NonEmptyStr

    def semantic_document(self) -> dict[str, object]:
        return semantic_model_dump(self)

    def digest_document(self) -> dict[str, object]:
        document = self.semantic_document()
        return {
            key: document[key]
            for key in (
                "schema_version",
                "contract_type",
                "logical_id",
                "revision",
                "payload",
            )
        }

    @computed_field
    @property
    def digest(self) -> str:
        return sha256_json(self.digest_document())

    @property
    def ref(self) -> ContractRef:
        raw_contract_type = self.model_dump(mode="json").get("contract_type")
        contract_type = ContractType(str(raw_contract_type))
        return ContractRef(
            contract_type=contract_type,
            logical_id=self.logical_id,
            revision=self.revision,
            digest=self.digest,
        )


class RevisionDecisionRecord(ContractModel):
    schema_version: Literal["1"] = "1"
    revision_ref: ContractRef
    decision: Literal["accepted", "rejected", "superseded"]
    actor_type: Literal["human"] = "human"
    actor_id: NonEmptyStr
    rationale: NonEmptyStr
    decided_at_utc: UtcDateTime

    @computed_field
    @property
    def digest(self) -> str:
        return sha256_json(semantic_model_dump(self))


class KeyValue(ContractModel):
    key: NonEmptyStr
    value: str | int | float | bool
