"""Admission orchestration: run the checkers, then assemble the record.

`admit` owns no decision of its own. It runs one checker per family against the
declared `RuntimeCapabilityEnvelope`, then the concrete adapter validators, and
folds the returned findings into an `AdmissionRecord`.

Each checker is pure: it receives `(spec, envelope)` and returns what it found.
The service is the only place that concatenates, which makes the accumulation
order a single readable sequence.

That order is not cosmetic. `missing_requirements`, `denied_policies`, and
`issues` are persisted tuples that the ledger and the evidence bundle read back,
so reordering the fold below changes observable output for any spec that violates
more than one family.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from evidrun.contracts.admission.checks.execution_trust import (
    check_unverified_execution_policy,
)
from evidrun.contracts.admission.checks.interaction import (
    check_capture,
    check_interaction,
)
from evidrun.contracts.admission.checks.inventory import (
    check_capabilities,
    check_provider,
    check_runner,
    check_runtime_capabilities,
)
from evidrun.contracts.admission.checks.unsupported import (
    check_budgets,
    check_checkpoint_coordinator,
    check_evaluation_pipeline,
    check_goal_mode,
    check_human_adjudication,
    check_progress_observer,
    check_stop_conditions,
    check_subject_disclosure,
)
from evidrun.contracts.admission.checks.workspace import check_workspace
from evidrun.contracts.admission.envelope import RuntimeCapabilityEnvelope
from evidrun.contracts.admission.issues import AdmissionFindings
from evidrun.contracts.execution_trust import ExecutionTrustRecord
from evidrun.contracts.runtime.records import AdmissionRecord
from evidrun.contracts.runtime.spec import AdmissionIssue, ResolvedAgentInventory, RunSpec
from evidrun.shared.types import utc_now


class RuntimeSpecValidator(Protocol):
    """The second admission layer: what only a resolved adapter pair can decide."""

    def __call__(self, spec: RunSpec) -> Iterable[AdmissionIssue]: ...


class AdmissionService:
    def __init__(
        self,
        *,
        envelope: RuntimeCapabilityEnvelope,
        execution_validators: Iterable[RuntimeSpecValidator] = (),
    ) -> None:
        self.envelope = envelope
        self.execution_validators = tuple(execution_validators)

    def admit(
        self,
        spec: RunSpec,
        execution_trust: ExecutionTrustRecord | None = None,
    ) -> AdmissionRecord:
        envelope = self.envelope

        runner = check_runner(spec, envelope)
        provider = check_provider(spec, envelope)
        capabilities = check_capabilities(spec, envelope)
        runtime_capabilities = check_runtime_capabilities(spec, envelope)
        workspace = check_workspace(spec, envelope)
        interaction = check_interaction(spec, envelope)
        disclosure = check_subject_disclosure(spec)

        # The fold order below IS the persisted order of the three tuples.
        findings = AdmissionFindings()
        for part in (
            (
                check_unverified_execution_policy(spec, execution_trust, envelope)
                if execution_trust is not None
                else AdmissionFindings()
            ),
            runner.findings,
            provider.findings,
            capabilities.findings,
            runtime_capabilities.findings,
            workspace.findings,
            interaction.findings,
            check_capture(spec, envelope),
            check_progress_observer(spec),
            check_checkpoint_coordinator(spec),
            check_goal_mode(spec),
            check_evaluation_pipeline(spec),
            check_human_adjudication(spec),
            disclosure.findings,
            check_budgets(spec, envelope),
            check_stop_conditions(spec),
        ):
            findings = findings.merge(part)
        adapter_issues = tuple(
            item
            for validator in self.execution_validators
            for item in validator(spec)
        )
        findings = findings.merge(AdmissionFindings(issues=adapter_issues))

        # Disclosure downgrades a status the interaction checker already resolved.
        interaction_status = disclosure.value or interaction.value
        resolved = capabilities.value
        blocked = (
            findings.blocks
            or any(item.required and item.status != "resolved" for item in resolved)
            or workspace.value != "resolved"
            or interaction_status != "resolved"
        )
        inventory = ResolvedAgentInventory(
            requirement_ref=spec.agent_inventory_ref,
            runner_ref=runner.value or spec.agent_inventory.runner_ref,
            provider_profile_id=provider.value.profile_id,
            provider_profile_digest=provider.value.profile_digest,
            provider_model=provider.value.model,
            provider_reasoning_effort=provider.value.reasoning_effort,
            provider_adapter=provider.value.adapter,
            capabilities=resolved,
            runtime_capabilities=runtime_capabilities.value,
        )
        return AdmissionRecord(
            run_spec_ref=f"run-spec:{spec.digest}",
            run_spec_digest=spec.digest,
            decision="rejected" if blocked else "admitted",
            resolved_inventory=inventory,
            workspace_status=workspace.value,
            interaction_status=interaction_status,
            missing_requirements=findings.missing,
            denied_policies=findings.denied_policies,
            issues=findings.issues,
            warnings=findings.warnings,
            execution_trust=(
                execution_trust.ref if execution_trust is not None else None
            ),
            created_at_utc=utc_now(),
        )
