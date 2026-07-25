"""The second admission layer: what only a resolved adapter pair can decide.

The declared envelope in `contracts/admission` answers "does this runtime claim
to support the shape?". These checks answer "can the exact adapter pair resolved
for this RunSpec actually execute it?". A capability appears in both layers only
where each one owns a distinct question; the owner of each overlapping axis is
recorded in `docs/architecture/codebase-layout.md`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal, Protocol

from evidrun.contracts.authoring import InputBinding
from evidrun.contracts.base import ArtifactRef
from evidrun.contracts.runtime import AdmissionIssue, ResolutionReason, RunSpec

IssueCategory = Literal["runtime", "provider", "capability", "policy"]
ReasonCode = Literal["unsupported", "denied", "unavailable", "digest_mismatch"]


class SpecSupport(Protocol):
    """An adapter that can say whether it serves a RunSpec exactly."""

    def supports(self, spec: RunSpec) -> bool: ...


class TextMaterializer(Protocol):
    """Reads a text artifact back from the canonical store, verifying identity."""

    def resolve_text(
        self, reference: ArtifactRef, *, project_id: str | None = ...
    ) -> str: ...


def issue(
    subject_ref: str,
    detail: str,
    *,
    category: IssueCategory = "runtime",
    code: ReasonCode = "unsupported",
) -> AdmissionIssue:
    """Build the blocking issue shape shared by every adapter-layer check."""

    return AdmissionIssue(
        category=category,
        subject_ref=subject_ref,
        reason=ResolutionReason(code=code, detail=detail),
        blocking=True,
    )


def check_shared_spec(
    spec: RunSpec,
    *,
    materializer: TextMaterializer | None,
    project_id_for_spec: Callable[[RunSpec], str] | None,
) -> list[AdmissionIssue]:
    """Checks that hold for both adapter pairs, in the baseline's exact order."""

    issues: list[AdmissionIssue] = []
    visible_inputs = tuple(
        item
        for item in spec.scenario.input_bindings
        if item.visibility in {"subject", "subject_and_evaluator"}
    )
    if len(spec.scenario.input_bindings) != 1:
        issues.append(
            issue(
                "scenario_input_count",
                "the active adapters require exactly one scenario input in total",
            )
        )
    issues.extend(
        _check_subject_input(
            spec,
            visible_inputs=visible_inputs,
            materializer=materializer,
            project_id_for_spec=project_id_for_spec,
        )
    )
    if spec.context_policy is None:
        issues.append(
            issue("context_policy", "the active Subject adapter requires a ContextPolicy")
        )
    if spec.extensions:
        issues.append(
            issue(
                "runtime_extensions",
                "the active adapters do not execute RunSpec extensions",
            )
        )
    if spec.evaluation_plan.disclosure.hidden_input_refs:
        issues.append(
            issue(
                "evaluation_hidden_inputs",
                "the active evaluator adapter does not consume hidden input artifacts",
            )
        )
    if spec.evaluation_plan.blinding_policy.hidden_fields:
        issues.append(
            issue(
                "evaluation_blinding",
                "the active evaluator adapter does not implement field blinding",
            )
        )
    if spec.evaluation_plan.aggregation is not None:
        issues.append(
            issue(
                "evaluation_aggregation",
                "the active evaluator adapter does not execute an aggregation projector",
            )
        )
    return issues


def check_evaluator_resolution(
    spec: RunSpec, *, evaluators: tuple[SpecSupport, ...]
) -> list[AdmissionIssue]:
    """At least one wired evaluator must serve the plan exactly."""

    if any(evaluator.supports(spec) for evaluator in evaluators):
        return []
    return [
        issue(
            "evaluator_adapter",
            "the EvaluationPlan has no exact deterministic evaluator adapter",
        )
    ]


def _check_subject_input(
    spec: RunSpec,
    *,
    visible_inputs: tuple[InputBinding, ...],
    materializer: TextMaterializer | None,
    project_id_for_spec: Callable[[RunSpec], str] | None,
) -> list[AdmissionIssue]:
    """One Subject-visible text input that the canonical store can verify.

    The branches stay chained: a spec with two visible inputs must not also be
    told its media type is wrong, because the baseline never emitted both.
    """

    if len(visible_inputs) != 1:
        return [
            issue(
                "subject_input_count",
                "the active Subject adapter requires exactly one Subject-visible input",
            )
        ]
    visible = visible_inputs[0]
    if visible.source.media_type != "text/plain":
        return [
            issue(
                "subject_input_media_type",
                "the active Subject adapter requires a text/plain input",
            )
        ]
    if materializer is None or project_id_for_spec is None:
        return [
            issue(
                "subject_input_materializer",
                "the active catalog has no artifact materializer",
            )
        ]
    try:
        materializer.resolve_text(visible.source, project_id=project_id_for_spec(spec))
    except FileNotFoundError, KeyError, ValueError:
        return [
            issue(
                "subject_input_artifact",
                "the Subject input cannot be verified in the canonical ArtifactStore",
            )
        ]
    return []
