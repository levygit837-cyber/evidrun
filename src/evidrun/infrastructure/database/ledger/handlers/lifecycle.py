"""Per-family factual checks for `append_event`.

Each function answers one question: given the Run, its prior events and the
normalized payload, may this event type be appended right now? They only raise —
the caller owns the session, the hash chain and the status advance, so an event
that fails here leaves nothing written.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any, cast

from sqlalchemy import select

from evidrun.contracts import (
    EvaluationRecord,
    EvaluationValidator,
    RunSpec,
)
from evidrun.infrastructure.database.models import (
    AdmissionRecordRow,
    CheckpointRecordRow,
    ContextSnapshotRow,
    EvaluationRecordRow,
    RunEventRow,
    RunRow,
    RunSpecRow,
)

__all__ = [
    "check_context_composed",
    "check_run_queued",
    "check_terminal_event",
]


def check_run_queued(
    session: Any,
    run: RunRow,
    normalized_payload: Mapping[str, Any],
) -> None:
    if run.run_spec_id is None or run.admission_id is None:
        raise ValueError("run.queued requires canonical Run contracts")
    spec_row = session.get(RunSpecRow, run.run_spec_id)
    admission_row = session.get(AdmissionRecordRow, run.admission_id)
    if spec_row is None or admission_row is None:
        raise ValueError("run.queued references missing Run contracts")
    if (
        normalized_payload.get("run_spec_digest") != spec_row.digest
        or normalized_payload.get("admission_digest") != admission_row.digest
    ):
        raise ValueError("run.queued contract digests do not match the RunRecord")


def check_context_composed(
    session: Any,
    run: RunRow,
    run_id: str,
    normalized_payload: Mapping[str, Any],
) -> None:
    snapshot = session.get(ContextSnapshotRow, str(normalized_payload["snapshot_id"]))
    if (
        snapshot is None
        or snapshot.run_id != run_id
        or snapshot.policy_id != normalized_payload["policy_id"]
        or snapshot.strategy != normalized_payload["strategy"]
        or snapshot.content_hash != normalized_payload["content_hash"]
        or snapshot.source_chars != normalized_payload["source_chars"]
        or snapshot.selected_chars != normalized_payload["selected_chars"]
        or bool(json.loads(snapshot.omitted_json)) != normalized_payload["omitted"]
    ):
        raise ValueError(
            "context.composed requires the exact persisted ContextSnapshot"
        )
    if run.run_spec_id is None:
        raise ValueError("context.composed requires a canonical RunSpec")
    context_spec_row = session.get(RunSpecRow, run.run_spec_id)
    if context_spec_row is None:
        raise ValueError("context.composed references a missing RunSpec")
    context_spec = RunSpec.model_validate(json.loads(context_spec_row.spec_json))
    if (
        context_spec.context_policy is None
        or context_spec.context_policy.id != snapshot.policy_id
        or context_spec.context_policy.strategy != snapshot.strategy
    ):
        raise ValueError("ContextSnapshot policy does not match the admitted RunSpec")


def check_terminal_event(
    session: Any,
    run: RunRow,
    run_id: str,
    event_type: str,
    normalized_payload: Mapping[str, Any],
    prior_events: Sequence[RunEventRow],
    prior_event_types: Sequence[str],
) -> None:
    if run.run_spec_id is None:
        raise ValueError("terminal event requires a canonical RunSpec")
    terminal_spec_row = session.get(RunSpecRow, run.run_spec_id)
    if terminal_spec_row is None:
        raise ValueError("terminal event references a missing RunSpec")
    terminal_spec = RunSpec.model_validate(json.loads(terminal_spec_row.spec_json))
    goal_result = cast(Mapping[str, object], normalized_payload["goal_result"])
    if goal_result.get("goal_mode") != terminal_spec.goal.mode:
        raise ValueError("terminal Goal result mode does not match the RunSpec Goal")
    if goal_result.get("goal_mode") == "bounded_exploration":
        declared_stop = goal_result.get("stop_condition_kind")
        if declared_stop not in {item.kind for item in terminal_spec.stop_conditions}:
            raise ValueError(
                "bounded exploration terminal references an undeclared stop condition"
            )
    evaluation_refs = cast(
        list[object],
        normalized_payload.get("evaluation_record_refs", []),
    )
    persisted_evaluation_ids = set(
        session.scalars(
            select(EvaluationRecordRow.id).where(EvaluationRecordRow.run_id == run_id)
        )
    )
    if {str(item) for item in evaluation_refs} != persisted_evaluation_ids:
        raise ValueError(
            "terminal event must reference every persisted EvaluationRecord exactly"
        )
    if event_type == "run.completed" and (
        "subject.responded" not in prior_event_types or not evaluation_refs
    ):
        raise ValueError(
            "completed Run requires a Subject response and evaluation records"
        )
    referenced_evaluations: list[EvaluationRecord] = []
    for evaluation_id in evaluation_refs:
        evaluation = session.get(EvaluationRecordRow, str(evaluation_id))
        if evaluation is None or evaluation.run_id != run_id:
            raise ValueError("terminal event references an evaluation outside the Run")
        referenced_evaluations.append(
            EvaluationRecord.model_validate(json.loads(evaluation.record_json))
        )
        if not any(
            item.event_type == "evaluation.completed"
            and json.loads(item.payload_json).get("evaluation_record_id")
            == str(evaluation_id)
            and json.loads(item.payload_json).get("evaluation_record_digest")
            == evaluation.record_digest
            for item in prior_events
        ):
            raise ValueError("terminal evaluation ref has no matching completion event")
    if event_type == "run.completed":
        gate_results = EvaluationValidator.gate_results(
            terminal_spec.evaluation_plan,
            referenced_evaluations,
        )
        required_stages = EvaluationValidator.stages_visible_after_gates(
            terminal_spec.evaluation_plan,
            gate_results,
        )
        if not set(required_stages).issubset(gate_results):
            raise ValueError(
                "completed Run does not cover the required EvaluationPlan stages"
            )
    if terminal_spec.evaluation_plan.human_adjudication_policy.required:
        referenced_records = [
            session.get(EvaluationRecordRow, str(evaluation_id))
            for evaluation_id in evaluation_refs
        ]
        if not any(
            record is not None and record.source_type == "human_adjudicator"
            for record in referenced_records
        ):
            raise ValueError(
                "terminal event requires the planned verified human adjudication"
            )
    checkpoint_refs = cast(list[object], normalized_payload.get("checkpoint_refs", []))
    for checkpoint_id in checkpoint_refs:
        checkpoint = session.get(CheckpointRecordRow, str(checkpoint_id))
        if checkpoint is None or checkpoint.run_id != run_id:
            raise ValueError("terminal event references a checkpoint outside the Run")
    open_tool_calls = {
        str(json.loads(item.payload_json)["call_id"])
        for item in prior_events
        if item.event_type == "tool.called"
    } - {
        str(json.loads(item.payload_json)["call_id"])
        for item in prior_events
        if item.event_type in {"tool.completed", "tool.denied", "tool.failed"}
    }
    if open_tool_calls:
        raise ValueError("terminal Run cannot contain an unresolved tool call")
