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
    PROGRESS_ARTIFACT_POLICY = "progress_artifact_policy"


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


#: Os papéis que uma entrada de manifest pode declarar. Nomeado aqui porque é a fonte
#: de verdade: quem monta entrada (evidence/archive.py) importa em vez de redeclarar.
ArtifactRole = Literal[
    "scenario_input",
    "subject_input_materialized",
    "agent_instruction",
    "interaction_prompt",
    "hidden_calibration",
    "extension_schema",
    "extension_payload",
    "evaluation_evidence",
    "tool_arguments",
    "tool_result",
    "run_output",
    "progress_summary",
    "workspace_snapshot",
    "checkpoint_capture",
    "report_attachment",
]


class ArtifactManifestEntry(ContractModel):
    """One intentionally materialized artifact; never a file-access activity log."""

    run_id: NonEmptyStr
    role: ArtifactRole
    artifact_ref: ArtifactRef
    source_label: NonEmptyStr
    content_included: bool = False
    omission_reason: NonEmptyStr | None = None
    required_for_portability: bool = False

    @model_validator(mode="after")
    def validate_content_claim(self) -> ArtifactManifestEntry:
        if self.content_included and self.omission_reason is not None:
            raise ValueError("included artifact content cannot declare an omission reason")
        if not self.content_included and self.omission_reason is None:
            raise ValueError("omitted artifact content requires an explicit reason")
        return self


class ArtifactManifest(ContractModel):
    schema_version: Literal["1"] = "1"
    profile: Literal["audit"] = "audit"
    entries: tuple[ArtifactManifestEntry, ...] = ()
    portable: Literal[False] = False
    replayable: Literal[False] = False

    @model_validator(mode="after")
    def validate_unique_entries(self) -> ArtifactManifest:
        keys = [
            (item.run_id, item.role, item.artifact_ref.artifact_id)
            for item in self.entries
        ]
        if len(keys) != len(set(keys)):
            raise ValueError("artifact manifest entries must be unique per Run, role, and artifact")
        return self

    @computed_field
    @property
    def digest(self) -> str:
        return sha256_json(semantic_model_dump(self))


class CapabilityDescriptorRef(ContractModel):
    namespace: NonEmptyStr
    name: NonEmptyStr
    version: NonEmptyStr
    digest: Digest


def capability_ref(
    namespace: str, name: str, version: str = "1"
) -> CapabilityDescriptorRef:
    """Build the canonical descriptor identity used by built-in adapters."""

    return CapabilityDescriptorRef(
        namespace=namespace,
        name=name,
        version=version,
        digest=sha256_json({"namespace": namespace, "name": name, "version": version}),
    )


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


class HumanAttestationRef(ContractModel):
    attestation_id: NonEmptyStr
    digest: Digest


class HumanAttestationRecord(ContractModel):
    """Evidence produced by a trusted human-verification adapter, not by API input."""

    schema_version: Literal["1"] = "1"
    attestation_id: NonEmptyStr
    principal_id: NonEmptyStr
    verification_method: Literal["webauthn"] = "webauthn"
    credential_id: NonEmptyStr
    action: Literal[
        "revision.accepted",
        "revision.rejected",
        "revision.superseded",
        "evaluation.adjudicated",
        "evaluation.reviewed",
    ]
    target_digest: Digest
    subject_digest: Digest
    challenge_digest: Digest
    assertion_ref: ArtifactRef
    user_verification: Literal["required_verified"] = "required_verified"
    relying_party_id: NonEmptyStr
    origin: NonEmptyStr
    verifier_ref: CapabilityDescriptorRef
    verified_at_utc: UtcDateTime

    @computed_field
    @property
    def digest(self) -> str:
        return sha256_json(semantic_model_dump(self))

    @property
    def ref(self) -> HumanAttestationRef:
        return HumanAttestationRef(attestation_id=self.attestation_id, digest=self.digest)


class VerifiedHumanDecisionAuthority(ContractModel):
    kind: Literal["verified_human"] = "verified_human"
    principal_id: NonEmptyStr
    attestation: HumanAttestationRecord

    @model_validator(mode="after")
    def validate_principal(self) -> VerifiedHumanDecisionAuthority:
        if self.principal_id != self.attestation.principal_id:
            raise ValueError("human authority principal must match the attestation principal")
        return self


class RepositoryFixtureDecisionAuthority(ContractModel):
    kind: Literal["repository_fixture"] = "repository_fixture"
    fixture_id: Literal["experiment-manifest-v1:crl-ctx-002"] = (
        "experiment-manifest-v1:crl-ctx-002"
    )
    fixture_digest: Digest

    @field_validator("fixture_digest")
    @classmethod
    def reject_placeholder_digest(cls, value: str) -> str:
        if value == "0" * 64:
            raise ValueError("repository fixture digest cannot be a placeholder")
        return value


DecisionAuthority = Annotated[
    VerifiedHumanDecisionAuthority | RepositoryFixtureDecisionAuthority,
    Field(discriminator="kind"),
]


class RevisionDecisionRecord(ContractModel):
    schema_version: Literal["1"] = "1"
    revision_ref: ContractRef
    decision: Literal["accepted", "rejected", "superseded"]
    authority: DecisionAuthority
    rationale: NonEmptyStr
    decided_at_utc: UtcDateTime

    @model_validator(mode="after")
    def validate_authority(self) -> RevisionDecisionRecord:
        if self.authority.kind == "repository_fixture":
            if self.decision != "accepted":
                raise ValueError("repository fixtures can only import accepted revisions")
            return self
        attestation = self.authority.attestation
        expected_subject = self.human_subject_digest()
        if attestation.action != f"revision.{self.decision}":
            raise ValueError("human attestation action does not match the revision decision")
        if attestation.target_digest != self.revision_ref.digest:
            raise ValueError("human attestation target does not match the revision digest")
        if attestation.subject_digest != expected_subject:
            raise ValueError("human attestation does not cover the revision decision content")
        if self.decided_at_utc != attestation.verified_at_utc:
            raise ValueError("human decision timestamp must be the verified attestation timestamp")
        return self

    def human_subject_digest(self) -> str:
        return sha256_json(
            {
                "revision_ref": self.revision_ref.model_dump(mode="json"),
                "decision": self.decision,
                "rationale": self.rationale,
            }
        )

    @computed_field
    @property
    def digest(self) -> str:
        return sha256_json(semantic_model_dump(self))


class KeyValue(ContractModel):
    key: NonEmptyStr
    value: str | int | float | bool
