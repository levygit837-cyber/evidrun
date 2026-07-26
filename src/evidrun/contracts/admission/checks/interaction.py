"""Interaction protocol and capture-mode decisions."""

from __future__ import annotations

from evidrun.contracts.admission.envelope import RuntimeCapabilityEnvelope
from evidrun.contracts.admission.issues import (
    AdmissionFindings,
    CheckResult,
    FindingsBuilder,
    InteractionStatus,
)
from evidrun.contracts.runtime.spec import RunSpec


def check_interaction(
    spec: RunSpec, envelope: RuntimeCapabilityEnvelope
) -> CheckResult[InteractionStatus]:
    """Resolve the interaction protocol against the declared modes.

    An unimplemented mode short-circuits: asking whether a graph protocol is also
    single-turn materializable would emit a second issue the baseline never emits.
    """

    found = FindingsBuilder()
    if spec.interaction_protocol.mode not in envelope.interaction_modes:
        found.reject(
            "interaction",
            spec.interaction_protocol.mode,
            "interaction mode is not implemented",
        )
        return CheckResult(value="unsupported", findings=found.freeze())
    if (
        spec.interaction_protocol.max_turns != 1
        or spec.interaction_protocol.system_prompt_ref is not None
        or spec.interaction_protocol.initial_message_refs
    ):
        found.reject(
            "interaction",
            "single_turn_materialization",
            "the active runner supports one direct turn without "
            "materialized prompt artifacts",
        )
        return CheckResult(value="unsupported", findings=found.freeze())
    return CheckResult(value="resolved")


def check_capture(
    spec: RunSpec, envelope: RuntimeCapabilityEnvelope
) -> AdmissionFindings:
    """Raw encrypted capture needs an encrypted Subject-output artifact sink."""

    found = FindingsBuilder()
    if (
        spec.capture_policy.default_mode == "raw_encrypted"
        and not envelope.supports_raw_encrypted_capture
    ):
        found.deny("capture:raw_encrypted")
        found.reject(
            "policy",
            "capture:raw_encrypted",
            "the active runner has no encrypted Subject-output artifact sink",
            code="denied",
        )
    return found.freeze()
