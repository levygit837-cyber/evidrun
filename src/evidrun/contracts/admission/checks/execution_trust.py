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
    if network == "provider_only":
        profile_id = spec.agent_inventory.provider_profile_id
        if profile_id is None or profile_id not in envelope.providers:
            found.require("provider_only:resolved_provider")
            found.reject(
                "provider",
                profile_id or "missing",
                "provider_only requires a provider backed by the active runtime",
                code="unavailable",
            )
    return found.freeze()
