"""What the provider/tool adapter pair requires exactly.

Like the scripted layer, this owns the concrete side of the overlapping axes:
the envelope declares `provider_only` network and raw encrypted capture as
supported shapes; these checks require them for this specific pair.
"""

from __future__ import annotations

from dataclasses import dataclass

from evidrun.contracts.base import CapabilityDescriptorRef
from evidrun.contracts.runtime import AdmissionIssue, RunSpec
from evidrun.runs.admission.catalog_checks import SpecSupport, issue


@dataclass(frozen=True, slots=True)
class RealSubjectContract:
    """The exact closed contract the real read agent will accept.

    Held as a narrow value so the checks do not reach into the adapter object,
    and so the requirement can be asserted without constructing a provider.
    """

    profile_id: str
    tool_ref: CapabilityDescriptorRef
    allowed_permission: str
    authority_constraint: str
    credential_available: bool


def check_real_spec(
    spec: RunSpec, *, contract: RealSubjectContract, evaluator: SpecSupport
) -> list[AdmissionIssue]:
    """Every way a RunSpec can fail the resolved provider/tool pair."""

    issues: list[AdmissionIssue] = []
    if not evaluator.supports(spec):
        issues.append(
            issue(
                "real_evaluator",
                "the real read agent requires the strict read-answer evaluator",
            )
        )
    if spec.agent_inventory.provider_profile_id != contract.profile_id:
        issues.append(
            issue(
                "provider_profile",
                "the real adapter requires its exact provider profile",
                category="provider",
            )
        )
    if not contract.credential_available:
        issues.append(
            issue(
                "provider_credential",
                "the provider credential is unavailable to the worker composition",
                category="provider",
                code="unavailable",
            )
        )
    if not _matches_closed_read_tool(spec, contract):
        issues.append(
            issue(
                "read_tool_contract",
                "the real adapter requires the exact closed read-tool capability",
                category="capability",
            )
        )
    if spec.workspace.network_policy.mode != "provider_only":
        issues.append(
            issue(
                "provider_network",
                "the real adapter requires provider_only network",
                category="policy",
                code="denied",
            )
        )
    if spec.budgets.max_tool_calls is None or spec.budgets.max_tool_calls > 8:
        issues.append(
            issue(
                "max_tool_calls",
                "the real adapter requires max_tool_calls between 1 and 8",
            )
        )
    if not (
        spec.capture_policy.default_mode == "raw_encrypted"
        and spec.capture_policy.raw_sensitive == "opt_in"
    ):
        issues.append(
            issue(
                "recoverable_subject_output",
                "the real adapter requires opt-in encrypted raw capture for recovery",
                category="policy",
                code="denied",
            )
        )
    return issues


def _matches_closed_read_tool(spec: RunSpec, contract: RealSubjectContract) -> bool:
    """Exactly one required, schema-only read tool with no materialized instructions."""

    requirements = spec.agent_inventory.capability_requirements
    if len(requirements) != 1:
        return False
    requirement = requirements[0]
    return (
        requirement.kind == "tool"
        and requirement.capability_ref == contract.tool_ref
        and requirement.required
        and requirement.minimum_interface_version == "1"
        and requirement.requested_permissions == (contract.allowed_permission,)
        and requirement.exposure == "schema_only"
        and requirement.authority_constraints == (contract.authority_constraint,)
        and not requirement.instruction_refs
    )
