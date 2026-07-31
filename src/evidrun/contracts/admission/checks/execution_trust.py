"""Fail-closed policy for executing an explicitly recorded revision set."""

from __future__ import annotations

from evidrun.contracts.admission.envelope import RuntimeCapabilityEnvelope
from evidrun.contracts.admission.issues import AdmissionFindings, FindingsBuilder
from evidrun.contracts.execution_trust import ExecutionTrustRecord
from evidrun.contracts.runtime.spec import RunSpec


def check_execution_trust_policy(
    spec: RunSpec,
    trust: ExecutionTrustRecord,
    envelope: RuntimeCapabilityEnvelope,
) -> AdmissionFindings:
    """Validate the binding and add the narrow non-human policy when applicable."""

    found = check_execution_trust_invariants(spec, trust)
    if trust.kind == "verified_revision_set":
        return found
    if spec.workspace.network_policy.mode != "provider_only":
        return found
    profile_id = spec.agent_inventory.provider_profile_id
    if profile_id is None or profile_id not in envelope.providers:
        runtime = FindingsBuilder()
        runtime.require("provider_only:resolved_provider")
        runtime.reject(
            "provider",
            profile_id or "missing",
            "provider_only requires a provider backed by the active runtime",
            code="unavailable",
        )
        return found.merge(runtime.freeze())
    return found


def check_execution_trust_invariants(
    spec: RunSpec,
    trust: ExecutionTrustRecord,
) -> AdmissionFindings:
    """Project refusals determined only by the immutable RunSpec and trust record."""

    if trust.run_spec_digest != spec.digest or trust.study_ref != spec.study_ref:
        raise ValueError("execution trust does not bind the exact RunSpec and Study")

    found = FindingsBuilder()
    if trust.kind == "verified_revision_set":
        return found.freeze()
    for classification in sorted(
        {
            item.source.classification.value
            for item in spec.scenario.input_bindings
            if item.source.classification.value not in {"public", "internal"}
        }
    ):
        found.deny(f"unverified_classification:{classification}")
        found.reject(
            "policy",
            f"classification:{classification}",
            "unverified execution permits only public or internal inputs",
            code="denied",
        )
    if spec.workspace.external_effect_policy.mode != "denied":
        found.deny(
            f"unverified_external_effect:{spec.workspace.external_effect_policy.mode}"
        )
        found.reject(
            "policy",
            "unverified_external_effect",
            "unverified execution requires external effects to be denied",
            code="denied",
        )
    network = spec.workspace.network_policy.mode
    if network not in {"disabled", "provider_only"}:
        found.deny(f"unverified_network:{network}")
        found.reject(
            "policy",
            f"network:{network}",
            "unverified execution permits only disabled or provider_only network",
            code="denied",
        )
    return found.freeze()
