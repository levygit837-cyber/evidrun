"""What the active runtime declares it can execute.

The envelope is the single declared truth admission decides against. It is built
by `runs/adapters` from the adapters that are actually wired, so a capability
cannot be announced here without an adapter behind it.

`declare()` is the only way in. The indexes are keyed by the descriptor itself,
never by a caller-supplied key, and are exposed as read-only mappings: a holder of
`service.envelope` cannot add a runner after composition and change a decision
without rebuilding the catalog.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from evidrun.contracts.base import CapabilityDescriptorRef

CapabilityKey = tuple[str, str, str]

_EMPTY_RUNNERS: Mapping[CapabilityKey, CapabilityDescriptorRef] = MappingProxyType({})


@dataclass(frozen=True)
class CapabilityCatalogEntry:
    ref: CapabilityDescriptorRef
    adapter: str
    allowed_permissions: frozenset[str]
    compatible_interface_versions: frozenset[str] = frozenset()
    satisfied_authority_constraints: frozenset[str] = frozenset()


@dataclass(frozen=True)
class ProviderCatalogEntry:
    profile_id: str
    profile_digest: str
    model: str
    reasoning_effort: str
    adapter: str


def capability_key(reference: CapabilityDescriptorRef) -> CapabilityKey:
    """Identity used to look a descriptor up, ignoring digest on purpose.

    Digest equality is a separate decision: a registered-but-stale descriptor must
    reject with `unsupported`, not silently read as unregistered.
    """

    return (reference.namespace, reference.name, reference.version)


@dataclass(frozen=True, slots=True)
class RuntimeCapabilityEnvelope:
    """The declared execution surface, resolved once per admission service.

    Construct through `declare()`; the mapping fields are read-only proxies, so
    the declared surface cannot drift after the catalog built it.
    """

    runners: Mapping[CapabilityKey, CapabilityDescriptorRef] = _EMPTY_RUNNERS
    capabilities: Mapping[CapabilityKey, CapabilityCatalogEntry] = MappingProxyType({})
    providers: Mapping[str, ProviderCatalogEntry] = MappingProxyType({})
    workspace_runtime_kinds: frozenset[str] = frozenset({"in_process"})
    interaction_modes: frozenset[str] = frozenset({"single_turn"})
    runtime_capabilities: frozenset[str] = frozenset()
    network_modes: frozenset[str] = frozenset({"disabled"})
    external_effect_modes: frozenset[str] = frozenset({"denied"})
    supported_budget_fields: frozenset[str] = frozenset()
    supports_raw_encrypted_capture: bool = False

    @classmethod
    def declare(
        cls,
        *,
        runners: Iterable[CapabilityDescriptorRef],
        capabilities: Iterable[CapabilityCatalogEntry] = (),
        providers: Iterable[ProviderCatalogEntry] = (),
        workspace_runtime_kinds: Iterable[str] = ("in_process",),
        interaction_modes: Iterable[str] = ("single_turn",),
        runtime_capabilities: Iterable[str] = (),
        network_modes: Iterable[str] = ("disabled",),
        external_effect_modes: Iterable[str] = ("denied",),
        supported_budget_fields: Iterable[str] = (),
        supports_raw_encrypted_capture: bool = False,
    ) -> RuntimeCapabilityEnvelope:
        """Index the declared surface for lookup, keeping defaults in one place."""

        return cls(
            runners=MappingProxyType(
                {capability_key(item): item for item in runners}
            ),
            capabilities=MappingProxyType(
                {capability_key(item.ref): item for item in capabilities}
            ),
            providers=MappingProxyType(
                {item.profile_id: item for item in providers}
            ),
            workspace_runtime_kinds=frozenset(workspace_runtime_kinds),
            interaction_modes=frozenset(interaction_modes),
            runtime_capabilities=frozenset(runtime_capabilities),
            network_modes=frozenset(network_modes),
            external_effect_modes=frozenset(external_effect_modes),
            supported_budget_fields=frozenset(supported_budget_fields),
            supports_raw_encrypted_capture=supports_raw_encrypted_capture,
        )
