"""One operator-facing projection of a persisted admission rejection."""

from __future__ import annotations

from evidrun.contracts.runtime.records import AdmissionRecord
from evidrun.contracts.triage import TriageError, TriageErrorCode, TriagePhase


def admission_rejection_error(record: AdmissionRecord) -> TriageError:
    """Render every blocking source without changing the admission decision.

    The record owns the canonical ordering. Issues, missing requirements, and
    denied policies are copied verbatim into the structured error. The human
    message projects those sequences in that same order, followed by required
    capabilities whose unresolved status is represented only in the inventory.
    """

    if record.decision != "rejected":
        raise ValueError("an admission rejection error requires a rejected record")
    unresolved_required_capabilities = tuple(
        item.requested_ref
        for item in record.resolved_inventory.capabilities
        if item.required and item.status != "resolved"
    )
    causes = tuple(f"issue:{item.subject_ref}" for item in record.issues if item.blocking)
    causes += tuple(f"missing:{item}" for item in record.missing_requirements)
    causes += tuple(f"denied:{item}" for item in record.denied_policies)
    causes += tuple(
        f"capability:{item.name}" for item in unresolved_required_capabilities
    )
    return TriageError(
        phase=TriagePhase.ADMIT,
        code=TriageErrorCode.ADMIT_REJECTED,
        message="RunSpec recusado: " + ", ".join(causes),
        remediation="Corrija os achados e solicite uma nova admissão.",
        issues=record.issues,
        missing_requirements=record.missing_requirements,
        denied_policies=record.denied_policies,
        unresolved_required_capabilities=unresolved_required_capabilities,
    )
