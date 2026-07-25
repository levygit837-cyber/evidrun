"""Admission: decide a RunSpec against the declared runtime capability envelope."""

from evidrun.contracts.admission.envelope import (
    CapabilityCatalogEntry,
    ProviderCatalogEntry,
    RuntimeCapabilityEnvelope,
)
from evidrun.contracts.admission.issues import AdmissionFindings, CheckResult
from evidrun.contracts.admission.service import AdmissionService, RuntimeSpecValidator

__all__ = [
    "AdmissionFindings",
    "AdmissionService",
    "CapabilityCatalogEntry",
    "CheckResult",
    "ProviderCatalogEntry",
    "RuntimeCapabilityEnvelope",
    "RuntimeSpecValidator",
]
