"""Template de workspace: mount, rede, efeito externo, snapshot e cleanup."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, StringConstraints, model_validator

from evidrun.contracts.base import (
    ArtifactRef,
    ContractModel,
    ContractType,
    NonEmptyStr,
    RevisionEnvelope,
)


class WorkspaceMount(ContractModel):
    name: NonEmptyStr
    source: ArtifactRef
    access: Literal["read_only", "read_write"]
    target: NonEmptyStr


class NetworkPolicy(ContractModel):
    mode: Literal["disabled", "provider_only", "allowlist"]
    allowed_endpoint_refs: tuple[NonEmptyStr, ...] = ()

    @model_validator(mode="after")
    def validate_allowlist(self) -> NetworkPolicy:
        if self.mode == "allowlist" and not self.allowed_endpoint_refs:
            raise ValueError("allowlist network policy requires endpoint refs")
        if self.mode != "allowlist" and self.allowed_endpoint_refs:
            raise ValueError("endpoint refs are only valid for allowlist network policy")
        return self


class ExternalEffectPolicy(ContractModel):
    mode: Literal["denied", "approval_required", "allowlist"]
    allowed_effects: tuple[NonEmptyStr, ...] = ()

    @model_validator(mode="after")
    def validate_allowlist(self) -> ExternalEffectPolicy:
        if self.mode == "allowlist" and not self.allowed_effects:
            raise ValueError("external effect allowlist requires effects")
        if self.mode != "allowlist" and self.allowed_effects:
            raise ValueError("allowed effects are only valid for allowlist policy")
        return self


class SnapshotPolicy(ContractModel):
    capture_workspace: bool = False
    include_zones: tuple[NonEmptyStr, ...] = ()


class SecretBindingRef(ContractModel):
    binding_id: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            min_length=1,
            max_length=64,
            pattern=r"^[a-z][a-z0-9.-]*$",
        ),
    ]
    source: Literal["keychain", "environment"]


class CleanupPolicy(ContractModel):
    mode: Literal["discard", "retain_until_ttl", "retain"] = "discard"
    ttl_seconds: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_ttl(self) -> CleanupPolicy:
        if self.mode == "retain_until_ttl" and self.ttl_seconds is None:
            raise ValueError("retain_until_ttl cleanup requires ttl_seconds")
        if self.mode != "retain_until_ttl" and self.ttl_seconds is not None:
            raise ValueError("ttl_seconds is only valid with retain_until_ttl")
        return self


class WorkspaceTemplateSpec(ContractModel):
    runtime_kind: NonEmptyStr
    lifecycle: Literal["ephemeral_per_run"] = "ephemeral_per_run"
    mounts: tuple[WorkspaceMount, ...] = ()
    write_zones: tuple[NonEmptyStr, ...] = ()
    network_policy: NetworkPolicy
    external_effect_policy: ExternalEffectPolicy
    secret_binding_refs: tuple[SecretBindingRef, ...] = ()
    snapshot_policy: SnapshotPolicy = SnapshotPolicy()
    cleanup_policy: CleanupPolicy = CleanupPolicy()

    @model_validator(mode="after")
    def validate_workspace_names(self) -> WorkspaceTemplateSpec:
        mount_names = [item.name for item in self.mounts]
        if len(mount_names) != len(set(mount_names)):
            raise ValueError("workspace mount names must be unique")
        if len(self.write_zones) != len(set(self.write_zones)):
            raise ValueError("workspace write zones must be unique")
        return self


class WorkspaceTemplateRevision(RevisionEnvelope):
    contract_type: Literal[ContractType.WORKSPACE_TEMPLATE] = ContractType.WORKSPACE_TEMPLATE
    payload: WorkspaceTemplateSpec
