"""The legacy deterministic grader: exact root-cause match against the Subject output."""

from __future__ import annotations

from collections.abc import Mapping

from evidrun.contracts import (
    EvaluationRecord,
    EvidenceRef,
    GoalStateTerminalResult,
    RunSpec,
)
from evidrun.contracts.compiler import EvaluatorEnvelopeCompiler
from evidrun.contracts.runtime import DimensionValue, EvaluationBoundary
from evidrun.evaluations import ExactCauseGrader
from evidrun.infrastructure.artifacts.store import ArtifactStore
from evidrun.runs.adapters.types import EvaluationOutcome
from evidrun.shared.capabilities import capability_ref
from evidrun.shared.ports import SubjectResult
from evidrun.shared.types import new_id, utc_now


class ExactCauseGraderAdapter:
    ref = capability_ref("evidrun.evaluator", "exact-root-cause-legacy-v1")

    @classmethod
    def supports(cls, spec: RunSpec) -> bool:
        """Exactly one boolean deterministic stage, triggered by subject.responded."""

        if len(spec.evaluation_plan.stages) != 1:
            return False
        stage = spec.evaluation_plan.stages[0]
        if (
            stage.kind != "deterministic_grader"
            or stage.trigger.kind != "event"
            or stage.trigger.reference != "subject.responded"
            or len(stage.output_dimensions) != 1
            or len(stage.parameters) != 1
            or stage.parameters[0].key != "expected"
            or not isinstance(stage.parameters[0].value, str)
            or not stage.parameters[0].value.strip()
        ):
            return False
        dimensions = {item.id: item for item in spec.evaluation_plan.dimensions}
        output_dimension = dimensions.get(stage.output_dimensions[0])
        if output_dimension is None or output_dimension.value_type != "boolean":
            return False
        return stage.evaluator_ref == cls.ref

    def evaluate(
        self,
        *,
        run_id: str,
        spec: RunSpec,
        result: SubjectResult,
        response_event_id: str,
        response_sequence: int,
        response_event_hash: str,
        tool_events: tuple[Mapping[str, object], ...] = (),
        artifact_store: ArtifactStore | None = None,
        project_id: str | None = None,
    ) -> EvaluationOutcome:
        """Grade the Subject output; the expected value never leaves the evaluator."""

        del tool_events, artifact_store, project_id
        evaluator_envelope = EvaluatorEnvelopeCompiler.compile(
            spec, spec.evaluation_plan.stages[0].id
        )
        stage = evaluator_envelope.stage
        expected_parameter = next(item for item in stage.parameters if item.key == "expected")
        grade = ExactCauseGrader(stage.id, str(expected_parameter.value)).grade(
            result.output, result.evidence
        )
        passed = bool(grade["passed"])
        rationale = str(grade["rationale"])
        record = EvaluationRecord(
            record_id=new_id("eval"),
            run_id=run_id,
            plan_ref=spec.evaluation_plan_ref,
            stage_id=stage.id,
            source_type="deterministic_grader",
            evaluator_ref=stage.evaluator_ref,
            boundary=EvaluationBoundary(
                up_to_event_sequence=response_sequence,
                event_hash=response_event_hash,
            ),
            dimension_values=(
                DimensionValue(
                    dimension_id=stage.output_dimensions[0],
                    value=passed,
                    rationale=rationale,
                    confidence=1.0,
                    evidence_refs=(EvidenceRef(ref=f"event:{response_event_id}"),),
                ),
            ),
            gate_status="passed" if passed else "failed",
            status="final",
            created_at_utc=utc_now(),
        )
        return EvaluationOutcome(
            record=record,
            score=float(grade["score"]),
            passed=passed,
            rationale=rationale,
            evidence=tuple(
                item.ref for value in record.dimension_values for item in value.evidence_refs
            ),
            goal_result=GoalStateTerminalResult(state="achieved" if passed else "not_achieved"),
        )
