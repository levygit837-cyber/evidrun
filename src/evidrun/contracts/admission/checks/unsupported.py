"""Contracts that compile and validate, but that no active coordinator executes.

Each check here maps to a runtime component that does not exist yet. They all
reject, and that is the designed behaviour: a capability is announced only when
its adapter is wired, never when its contract merely parses.
"""

from __future__ import annotations

from evidrun.contracts.admission.envelope import RuntimeCapabilityEnvelope
from evidrun.contracts.admission.issues import (
    AdmissionFindings,
    CheckResult,
    FindingsBuilder,
    InteractionStatus,
)
from evidrun.contracts.runtime import RunSpec


def check_progress_observer(spec: RunSpec) -> AdmissionFindings:
    """No background observer exists, so a progress policy cannot be honoured."""

    found = FindingsBuilder()
    if spec.progress_artifact_policy is not None:
        found.require("runtime:background_progress_observer")
        found.reject(
            "observer",
            "background_progress_observer",
            "background progress observer is not implemented",
        )
    return found.freeze()


def check_checkpoint_coordinator(spec: RunSpec) -> AdmissionFindings:
    """Checkpoint contracts are valid; nothing observes their triggers."""

    found = FindingsBuilder()
    if spec.checkpoint_policy is not None:
        found.require("runtime:checkpoint_coordinator")
        found.reject(
            "runtime",
            "checkpoint_coordinator",
            "checkpoint contracts are valid, but the active runtime does not "
            "observe triggers, execute validators, or create records",
        )
    return found.freeze()


def check_goal_mode(spec: RunSpec) -> AdmissionFindings:
    """Only goal_state terminals exist; bounded exploration has no terminal path."""

    found = FindingsBuilder()
    if spec.goal.mode == "bounded_exploration":
        found.require("runtime:bounded_exploration_terminal")
        found.reject(
            "runtime",
            "bounded_exploration_terminal",
            "the active deterministic runner only emits goal_state terminal results",
        )
    return found.freeze()


def check_evaluation_pipeline(spec: RunSpec) -> AdmissionFindings:
    """One deterministic boolean grader triggered by subject.responded, exactly."""

    found = FindingsBuilder()
    if not _is_supported_evaluation(spec):
        found.require("runtime:evaluation_pipeline")
        found.reject(
            "runtime",
            "evaluation_pipeline",
            "the active runtime supports one deterministic boolean grader "
            "triggered by subject.responded",
        )
    return found.freeze()


def check_human_adjudication(spec: RunSpec) -> AdmissionFindings:
    """Verified human adjudication needs an authority path that does not exist."""

    found = FindingsBuilder()
    if spec.evaluation_plan.human_adjudication_policy.required:
        found.require("runtime:verified_human_adjudication")
        found.reject(
            "authority",
            "verified_human_adjudication",
            "verified human adjudication is not implemented",
        )
    return found.freeze()


def check_subject_disclosure(spec: RunSpec) -> CheckResult[InteractionStatus | None]:
    """Any disclosure other than `none` needs a delivery path the runner lacks.

    This is the one check that also downgrades interaction status, so it returns
    the replacement status, or `None` when the already-computed status stands: the
    runner receives objective and context only, which makes guidance delivery an
    interaction capability rather than merely a missing requirement.
    """

    disclosure_mode = spec.evaluation_plan.disclosure.subject.mode
    if disclosure_mode == "none":
        return CheckResult(value=None)
    found = FindingsBuilder()
    found.require("runtime:subject_evaluation_guidance_delivery")
    found.reject(
        "interaction",
        f"evaluation_disclosure:{disclosure_mode}",
        "the active runner receives objective and context only; it does "
        "not consume Subject evaluation guidance",
    )
    return CheckResult(value="unsupported", findings=found.freeze())


def check_budgets(
    spec: RunSpec, envelope: RuntimeCapabilityEnvelope
) -> AdmissionFindings:
    """Reject every declared budget the active runtime cannot enforce."""

    unsupported_budget_fields = tuple(
        name
        for name, value in (
            ("max_input_tokens", spec.budgets.max_input_tokens),
            ("max_output_tokens", spec.budgets.max_output_tokens),
            ("max_tool_calls", spec.budgets.max_tool_calls),
            ("max_cost", spec.budgets.max_cost),
        )
        if value is not None and name not in envelope.supported_budget_fields
    )
    if spec.budgets.max_turns not in {None, 1}:
        unsupported_budget_fields += ("max_turns",)
    found = FindingsBuilder()
    if not unsupported_budget_fields:
        return found.freeze()
    for field_name in unsupported_budget_fields:
        found.require(f"runtime:budget:{field_name}")
    found.reject(
        "runtime",
        "budget_enforcement",
        "the active runtime cannot enforce one or more declared budgets",
    )
    return found.freeze()


def check_stop_conditions(spec: RunSpec) -> AdmissionFindings:
    """Terminal goal completion and wall-time exhaustion, and nothing else."""

    supported_stop_kinds = {"goal_complete", "budget_exhausted"}
    unsupported_stops = tuple(
        item
        for item in spec.stop_conditions
        if item.kind not in supported_stop_kinds or item.action != "terminal"
    )
    has_terminal_budget = any(
        item.kind == "budget_exhausted" and item.action == "terminal"
        for item in spec.stop_conditions
    )
    found = FindingsBuilder()
    if unsupported_stops or not has_terminal_budget:
        found.require("runtime:stop_condition_coordinator")
        found.reject(
            "runtime",
            "stop_condition_coordinator",
            "the active runner supports terminal goal completion and wall-time "
            "budget exhaustion only",
        )
    return found.freeze()


def _is_supported_evaluation(spec: RunSpec) -> bool:
    stages = spec.evaluation_plan.stages
    if len(stages) != 1:
        return False
    stage = stages[0]
    dimension_by_id = {item.id: item for item in spec.evaluation_plan.dimensions}
    return (
        stage.kind == "deterministic_grader"
        and stage.trigger.kind == "event"
        and stage.trigger.reference == "subject.responded"
        and len(stage.output_dimensions) == 1
        and dimension_by_id[stage.output_dimensions[0]].value_type == "boolean"
        and any(item.key == "expected" for item in stage.parameters)
    )
