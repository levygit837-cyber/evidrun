"""Runner, provider, and capability resolution against the declared envelope."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from evidrun.contracts.admission.envelope import (
    RuntimeCapabilityEnvelope,
    capability_key,
)
from evidrun.contracts.admission.issues import CheckResult, FindingsBuilder
from evidrun.contracts.authoring import CapabilityRequirement
from evidrun.contracts.base import CapabilityDescriptorRef
from evidrun.contracts.runtime import (
    ResolutionReason,
    ResolvedCapability,
    RunSpec,
)


@dataclass(frozen=True, slots=True)
class ResolvedProvider:
    """The provider block of the resolved inventory, empty when unresolved."""

    profile_id: str | None = None
    profile_digest: str | None = None
    model: str | None = None
    reasoning_effort: str | None = None
    adapter: str | None = None


def check_runner(
    spec: RunSpec, envelope: RuntimeCapabilityEnvelope
) -> CheckResult[CapabilityDescriptorRef | None]:
    """Resolve the runner, requiring the exact registered digest."""

    requested = spec.agent_inventory.runner_ref
    runner = envelope.runners.get(capability_key(requested))
    if runner is not None and runner.digest == requested.digest:
        return CheckResult(value=runner)
    found = FindingsBuilder()
    found.require(f"runner:{requested.name}")
    found.reject(
        "runner",
        requested.name,
        "runner is not registered with the required digest",
    )
    return CheckResult(value=None, findings=found.freeze())


def check_provider(
    spec: RunSpec, envelope: RuntimeCapabilityEnvelope
) -> CheckResult[ResolvedProvider]:
    """Resolve the declared provider profile, or reject it as unavailable.

    An unresolved profile yields an empty provider block: a resolved inventory that
    names a profile must also carry its digest, model, reasoning, and adapter, so a
    rejection can never claim a provider the runtime could not resolve.
    """

    declared = spec.agent_inventory.provider_profile_id
    if declared is None:
        return CheckResult(value=ResolvedProvider())
    provider = envelope.providers.get(declared)
    if provider is None:
        found = FindingsBuilder()
        found.require(f"provider:{declared}")
        found.reject(
            "provider",
            declared,
            "provider profile is not available in the active runtime",
            code="unavailable",
        )
        return CheckResult(value=ResolvedProvider(), findings=found.freeze())
    return CheckResult(
        value=ResolvedProvider(
            profile_id=declared,
            profile_digest=provider.profile_digest,
            model=provider.model,
            reasoning_effort=provider.reasoning_effort,
            adapter=provider.adapter,
        )
    )


def check_capabilities(
    spec: RunSpec, envelope: RuntimeCapabilityEnvelope
) -> CheckResult[tuple[ResolvedCapability, ...]]:
    """Resolve every declared capability requirement in declaration order.

    An unsatisfied optional requirement warns and still yields a non-resolved
    entry; the record stays honest about what the Subject will not receive.
    """

    found = FindingsBuilder()
    resolved: list[ResolvedCapability] = []
    for requirement in spec.agent_inventory.capability_requirements:
        entry = envelope.capabilities.get(capability_key(requirement.capability_ref))
        if entry is None or entry.ref.digest != requirement.capability_ref.digest:
            resolved.append(
                _unresolved(
                    requirement,
                    status="unsupported",
                    code="unsupported",
                    detail="capability is not registered in the active runtime",
                )
            )
            if not requirement.required:
                found.warn(
                    "optional capability unavailable: "
                    f"{requirement.capability_ref.name}"
                )
            continue
        if requirement.minimum_interface_version not in entry.compatible_interface_versions:
            resolved.append(
                _unresolved(
                    requirement,
                    status="unsupported",
                    code="unsupported",
                    detail=(
                        "capability adapter does not support the required "
                        "interface version"
                    ),
                )
            )
            if not requirement.required:
                found.warn(
                    "optional capability interface unavailable: "
                    f"{requirement.capability_ref.name}"
                )
            continue
        requested_permissions = frozenset(requirement.requested_permissions)
        if not requested_permissions.issubset(entry.allowed_permissions):
            resolved.append(
                _unresolved(
                    requirement,
                    status="denied",
                    code="denied",
                    detail="requested permissions exceed the catalog allowlist",
                )
            )
            if not requirement.required:
                found.warn(
                    "optional capability permission denied: "
                    f"{requirement.capability_ref.name}"
                )
            continue
        requested_constraints = frozenset(requirement.authority_constraints)
        if not requested_constraints.issubset(entry.satisfied_authority_constraints):
            resolved.append(
                _unresolved(
                    requirement,
                    status="denied",
                    code="denied",
                    detail=(
                        "capability adapter cannot prove all requested "
                        "authority constraints"
                    ),
                )
            )
            if not requirement.required:
                found.warn(
                    "optional capability authority constraint denied: "
                    f"{requirement.capability_ref.name}"
                )
            continue
        resolved.append(
            ResolvedCapability(
                kind=requirement.kind,
                requested_ref=requirement.capability_ref,
                required=requirement.required,
                exposure=requirement.exposure,
                status="resolved",
                resolved_ref=entry.ref,
                adapter=entry.adapter,
                effective_interface_version=requirement.minimum_interface_version,
                effective_permissions=tuple(sorted(requested_permissions)),
                satisfied_authority_constraints=tuple(sorted(requested_constraints)),
                context_refs=(
                    requirement.instruction_refs
                    if requirement.exposure
                    in {"instructions", "instructions_and_schema"}
                    else ()
                ),
            )
        )
    return CheckResult(value=tuple(resolved), findings=found.freeze())


def check_runtime_capabilities(
    spec: RunSpec, envelope: RuntimeCapabilityEnvelope
) -> CheckResult[tuple[str, ...]]:
    """Reject required runtime capabilities the runtime does not implement."""

    found = FindingsBuilder()
    for requirement in spec.agent_inventory.runtime_requirements:
        if requirement.capability in envelope.runtime_capabilities:
            continue
        if requirement.required:
            found.require(f"runtime:{requirement.capability}")
            found.reject(
                "runtime",
                requirement.capability,
                "runtime capability is not implemented",
            )
        else:
            found.warn(
                f"optional runtime capability unavailable: {requirement.capability}"
            )
    resolved = tuple(
        sorted(
            requirement.capability
            for requirement in spec.agent_inventory.runtime_requirements
            if requirement.capability in envelope.runtime_capabilities
        )
    )
    return CheckResult(value=resolved, findings=found.freeze())


def _unresolved(
    requirement: CapabilityRequirement,
    *,
    status: Literal["unsupported", "denied", "unavailable"],
    code: Literal["unsupported", "denied", "unavailable"],
    detail: str,
) -> ResolvedCapability:
    """Build the non-resolved entry shape shared by all four failure branches."""

    return ResolvedCapability(
        kind=requirement.kind,
        requested_ref=requirement.capability_ref,
        required=requirement.required,
        exposure=requirement.exposure,
        status=status,
        reason=ResolutionReason(code=code, detail=detail),
    )
