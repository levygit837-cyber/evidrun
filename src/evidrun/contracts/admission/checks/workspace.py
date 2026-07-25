"""Workspace and workspace-scoped policy decisions.

The seven branches below are a single ordered decision, not seven independent
checks: the first one that matches sets `workspace_status` and stops. Splitting
them into independent checkers would change `AdmissionRecord.issues` for a spec
that violates two branches at once, so the chain stays intact and the ownership
of the network and external-effect axes stays here, with the workspace.
"""

from __future__ import annotations

from evidrun.contracts.admission.envelope import RuntimeCapabilityEnvelope
from evidrun.contracts.admission.issues import (
    CheckResult,
    FindingsBuilder,
    WorkspaceStatus,
)
from evidrun.contracts.runtime import RunSpec


def check_workspace(
    spec: RunSpec, envelope: RuntimeCapabilityEnvelope
) -> CheckResult[WorkspaceStatus]:
    """Resolve the workspace, returning the first blocking status in order."""

    found = FindingsBuilder()
    status = _resolve(spec, envelope, found)
    return CheckResult(value=status, findings=found.freeze())


def _resolve(
    spec: RunSpec, envelope: RuntimeCapabilityEnvelope, found: FindingsBuilder
) -> WorkspaceStatus:
    disallowed_input_classifications = {
        item.source.classification
        for item in spec.scenario.input_bindings
        if item.source.classification.value in {"sensitive", "restricted"}
    }
    if disallowed_input_classifications:
        for classification in sorted(
            disallowed_input_classifications, key=lambda item: item.value
        ):
            found.deny(f"classification:{classification.value}")
        found.reject(
            "policy",
            "input_classification",
            "the active runtime has no classified materialization boundary "
            "for sensitive or restricted inputs",
            code="denied",
        )
        return "denied"
    if spec.workspace.runtime_kind not in envelope.workspace_runtime_kinds:
        found.reject(
            "workspace",
            spec.workspace.runtime_kind,
            "workspace runtime is not implemented",
        )
        return "unsupported"
    if _has_unauthorized_mount(spec):
        found.reject(
            "workspace",
            "mount_authority",
            "workspace mount is not an exact Subject-visible scenario input",
            code="denied",
        )
        return "denied"
    if any(item.access != "read_only" for item in spec.workspace.mounts):
        found.reject(
            "workspace",
            "read_write_mount",
            "the active workspace adapter only supports read-only inputs",
        )
        return "unsupported"
    if _requests_unimplemented_workspace_features(spec):
        found.reject(
            "workspace",
            spec.workspace.runtime_kind,
            "workspace requests write, secret, snapshot, or retention "
            "features that the active adapter does not implement",
        )
        return "unsupported"
    if spec.workspace.network_policy.mode not in envelope.network_modes:
        found.deny(f"network:{spec.workspace.network_policy.mode}")
        found.reject(
            "policy",
            f"network:{spec.workspace.network_policy.mode}",
            "network policy is not allowed by this runtime",
            code="denied",
        )
        return "denied"
    if spec.workspace.external_effect_policy.mode not in envelope.external_effect_modes:
        found.deny(f"external_effect:{spec.workspace.external_effect_policy.mode}")
        found.reject(
            "policy",
            f"external_effect:{spec.workspace.external_effect_policy.mode}",
            "external effect policy is not allowed by this runtime",
            code="denied",
        )
        return "denied"
    return "resolved"


def _has_unauthorized_mount(spec: RunSpec) -> bool:
    """A mount must match one Subject-visible scenario input exactly."""

    return any(
        not any(
            binding.visibility in {"subject", "subject_and_evaluator"}
            and binding.mount_name == mount.name
            and binding.source == mount.source
            and binding.mount_access == mount.access
            for binding in spec.scenario.input_bindings
        )
        for mount in spec.workspace.mounts
    )


def _requests_unimplemented_workspace_features(spec: RunSpec) -> bool:
    return bool(
        spec.workspace.write_zones
        or spec.workspace.secret_binding_refs
        or spec.workspace.snapshot_policy.capture_workspace
        or spec.workspace.snapshot_policy.include_zones
        or spec.workspace.cleanup_policy.mode != "discard"
    )
