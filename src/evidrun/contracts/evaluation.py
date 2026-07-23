from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

from evidrun.contracts.authoring import EvaluationDimension, EvaluationPlanSpec
from evidrun.contracts.runtime import DimensionValue, EvaluationRecord


class EvaluationValidator:
    @classmethod
    def validate(cls, plan: EvaluationPlanSpec, record: EvaluationRecord) -> None:
        stage = next((item for item in plan.stages if item.id == record.stage_id), None)
        if stage is None:
            raise ValueError("evaluation record references an unknown stage")
        if record.source_type != "human_adjudicator":
            expected_sources = {
                "integrity": "deterministic_grader",
                "deterministic_grader": "deterministic_grader",
                "model_judge": "model_judge",
                "human_review": "human_adjudicator",
            }
            if record.source_type != expected_sources[stage.kind]:
                raise ValueError("evaluation source type does not match its plan stage")
            if record.evaluator_ref != stage.evaluator_ref:
                raise ValueError("evaluation record substituted the planned evaluator")
        dimension_by_id = {item.id: item for item in plan.dimensions}
        record_ids = {item.dimension_id for item in record.dimension_values}
        if record_ids != set(stage.output_dimensions):
            raise ValueError("evaluation record does not cover the stage output dimensions")
        for value in record.dimension_values:
            cls._validate_dimension_value(dimension_by_id[value.dimension_id], value)

    @staticmethod
    def _validate_dimension_value(
        dimension: EvaluationDimension, observation: DimensionValue
    ) -> None:
        value = observation.value
        if dimension.value_type == "boolean":
            if not isinstance(value, bool):
                raise ValueError("boolean evaluation dimension requires a boolean value")
            return
        if dimension.value_type == "number":
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError("numeric evaluation dimension requires a number")
            if dimension.minimum is not None and value < dimension.minimum:
                raise ValueError("evaluation value is below the dimension minimum")
            if dimension.maximum is not None and value > dimension.maximum:
                raise ValueError("evaluation value is above the dimension maximum")
            return
        if not isinstance(value, str):
            raise ValueError("category evaluation dimension requires a string value")
        categories = {str(anchor.value) for anchor in dimension.anchors}
        if categories and value not in categories:
            raise ValueError("evaluation category is not declared by an anchor")

    @staticmethod
    def stages_visible_after_gates(
        plan: EvaluationPlanSpec,
        gate_results: Mapping[str, Literal["passed", "failed", "not_applicable"]],
    ) -> tuple[str, ...]:
        visible: list[str] = []
        for stage in plan.stages:
            visible.append(stage.id)
            if stage.hard_gate:
                result = gate_results.get(stage.id)
                if result not in {"passed", "not_applicable"}:
                    break
        return tuple(visible)
