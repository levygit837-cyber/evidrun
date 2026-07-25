"""What the offline scripted adapter pair cannot execute.

This layer owns the concrete side of the four overlapping axes: the declared
envelope says which network modes, capture modes, and budget fields the runtime
claims; these checks say what the resolved scripted pair actually runs.
"""

from __future__ import annotations

from evidrun.contracts.runtime import AdmissionIssue, RunSpec
from evidrun.runs.admission.catalog_checks import SpecSupport, issue


def check_scripted_spec(
    spec: RunSpec, *, evaluator: SpecSupport
) -> list[AdmissionIssue]:
    """Every way a RunSpec can exceed the scripted compatibility adapter."""

    issues: list[AdmissionIssue] = []
    if not evaluator.supports(spec):
        issues.append(
            issue(
                "scripted_evaluator",
                "the scripted runner requires the exact legacy deterministic evaluator",
            )
        )
    if spec.agent_inventory.provider_profile_id is not None:
        issues.append(
            issue("offline_provider", "the scripted adapter does not invoke a provider")
        )
    if spec.agent_inventory.capability_requirements:
        issues.append(
            issue(
                "offline_capabilities",
                "the scripted adapter does not execute tools or skills",
            )
        )
    if spec.workspace.network_policy.mode != "disabled":
        issues.append(
            issue("offline_network", "the scripted adapter requires disabled network")
        )
    if spec.budgets.max_tool_calls is not None:
        issues.append(
            issue(
                "offline_tool_budget",
                "the scripted adapter cannot consume a tool-call budget",
            )
        )
    if spec.capture_policy.default_mode == "raw_encrypted":
        issues.append(
            issue(
                "offline_raw_capture",
                "the scripted compatibility adapter does not use raw encrypted capture",
            )
        )
    return issues
