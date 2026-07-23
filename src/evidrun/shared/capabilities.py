from __future__ import annotations

from evidrun.contracts.base import CapabilityDescriptorRef
from evidrun.shared.types import sha256_json


def capability_ref(
    namespace: str, name: str, version: str = "1"
) -> CapabilityDescriptorRef:
    """Build the canonical descriptor identity used by built-in adapters."""

    return CapabilityDescriptorRef(
        namespace=namespace,
        name=name,
        version=version,
        digest=sha256_json(
            {"namespace": namespace, "name": name, "version": version}
        ),
    )
