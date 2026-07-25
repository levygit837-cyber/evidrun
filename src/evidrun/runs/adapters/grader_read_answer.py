"""Strict JSON answer grader grounded in persisted read-tool result artifacts.

The grader trusts nothing the Subject said about its own evidence. It rebuilds the
set of lines the read tool actually returned from persisted `tool.completed`
artifacts, then requires that every citation and the answer itself resolve inside
that set. A well-shaped answer citing a line the tool never returned fails.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import cast

from pydantic import TypeAdapter

from evidrun.contracts import (
    ArtifactRef,
    EvaluationRecord,
    EvidenceRef,
    GoalStateTerminalResult,
    RunSpec,
)
from evidrun.contracts.runtime import DimensionValue, EvaluationBoundary
from evidrun.infrastructure.artifacts.store import ArtifactStore
from evidrun.runs.adapters.types import EvaluationOutcome
from evidrun.shared.capabilities import capability_ref
from evidrun.shared.ports import SubjectResult
from evidrun.shared.types import new_id, utc_now

_json_object = TypeAdapter(dict[str, object])

PersistedLine = tuple[str, int, str]


@dataclass(slots=True)
class _PersistedEvidence:
    """Every line the read tool actually returned, plus the events that prove it."""

    lines: set[PersistedLine] = field(default_factory=set[PersistedLine])
    evidence_refs: list[EvidenceRef] = field(default_factory=list[EvidenceRef])


@dataclass(frozen=True, slots=True)
class _ParsedAnswer:
    """The Subject's terminal JSON, only as far as it is well-shaped."""

    valid_shape: bool
    answer: object
    cited: tuple[tuple[str, int], ...]


class ExactReadAnswerGraderAdapter:
    """Strict JSON answer grader grounded in persisted read-tool result artifacts."""

    ref = capability_ref("evidrun.evaluator", "exact-read-answer-v1")

    @classmethod
    def supports(cls, spec: RunSpec) -> bool:
        if len(spec.evaluation_plan.stages) != 1:
            return False
        stage = spec.evaluation_plan.stages[0]
        dimensions = {item.id: item for item in spec.evaluation_plan.dimensions}
        return (
            stage.evaluator_ref == cls.ref
            and stage.kind == "deterministic_grader"
            and stage.trigger.kind == "event"
            and stage.trigger.reference == "subject.responded"
            and len(stage.output_dimensions) == 1
            and dimensions.get(stage.output_dimensions[0]) is not None
            and dimensions[stage.output_dimensions[0]].value_type == "boolean"
            and len(stage.parameters) == 1
            and stage.parameters[0].key == "expected"
            and isinstance(stage.parameters[0].value, str)
            and bool(stage.parameters[0].value.strip())
        )

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
        if artifact_store is None:
            raise ValueError("strict read evaluation requires the canonical ArtifactStore")
        stage = spec.evaluation_plan.stages[0]
        expected = str(stage.parameters[0].value)
        persisted = self._collect_persisted_evidence(
            tool_events,
            response_event_id=response_event_id,
            artifact_store=artifact_store,
            project_id=project_id,
        )
        parsed = self._parse_answer(result.output)
        passed = self._is_grounded(parsed, persisted.lines, expected=expected)
        rationale = (
            "Strict answer matched the hidden reference and cited a persisted read-tool line."
            if passed
            else "Strict answer or its cited persisted read-tool evidence did not match."
        )
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
                    evidence_refs=tuple(persisted.evidence_refs),
                ),
            ),
            gate_status="passed" if passed else "failed",
            status="final",
            created_at_utc=utc_now(),
        )
        return EvaluationOutcome(
            record=record,
            score=1.0 if passed else 0.0,
            passed=passed,
            rationale=rationale,
            evidence=tuple(item.ref for item in persisted.evidence_refs),
            goal_result=GoalStateTerminalResult(state="achieved" if passed else "not_achieved"),
        )

    def _collect_persisted_evidence(
        self,
        tool_events: tuple[Mapping[str, object], ...],
        *,
        response_event_id: str,
        artifact_store: ArtifactStore,
        project_id: str | None,
    ) -> _PersistedEvidence:
        """Rebuild what the tool returned by reading its persisted result artifacts."""

        persisted = _PersistedEvidence(
            evidence_refs=[EvidenceRef(ref=f"event:{response_event_id}")]
        )
        for event in tool_events:
            if event.get("type") != "tool.completed":
                continue
            payload_value: object = event.get("payload")
            if not isinstance(payload_value, Mapping):
                continue
            payload = cast(Mapping[str, object], payload_value)
            result_ref = payload.get("result_ref")
            if result_ref is None:
                continue
            reference = ArtifactRef.model_validate(result_ref)
            document = _json_object.validate_json(
                artifact_store.get_verified(reference, project_id=project_id)
            )
            persisted.lines.update(self._document_lines(document))
            event_id = event.get("event_id")
            if isinstance(event_id, str):
                persisted.evidence_refs.append(EvidenceRef(ref=f"event:{event_id}"))
        return persisted

    @staticmethod
    def _document_lines(document: Mapping[str, object]) -> set[PersistedLine]:
        """A malformed persisted result is a hard error, not a silent empty set."""

        lines_value = document.get("lines")
        if not isinstance(lines_value, list):
            raise ValueError("persisted read-tool result has an invalid shape")
        input_id = document.get("input_id")
        if not isinstance(input_id, str):
            raise ValueError("persisted read-tool result is missing input_id")
        found: set[PersistedLine] = set()
        for line_value in cast(list[object], lines_value):
            if not isinstance(line_value, dict):
                continue
            line = cast(dict[str, object], line_value)
            line_number = line.get("line")
            line_text = line.get("text")
            if (
                isinstance(line_number, int)
                and not isinstance(line_number, bool)
                and isinstance(line_text, str)
            ):
                found.add((input_id, line_number, line_text))
        return found

    @staticmethod
    def _parse_answer(output: str) -> _ParsedAnswer:
        """Accept only `{answer, evidence}` with a non-empty `{input_id, line}` list."""

        try:
            document = _json_object.validate_json(output)
        except ValueError:
            return _ParsedAnswer(valid_shape=False, answer=None, cited=())
        if set(document) != {"answer", "evidence"}:
            return _ParsedAnswer(valid_shape=False, answer=None, cited=())
        answer = document.get("answer")
        citations = document.get("evidence")
        if not isinstance(citations, list) or not citations:
            return _ParsedAnswer(valid_shape=False, answer=answer, cited=())
        cited: list[tuple[str, int]] = []
        for citation_value in cast(list[object], citations):
            if not isinstance(citation_value, dict):
                return _ParsedAnswer(valid_shape=False, answer=answer, cited=())
            citation = cast(dict[str, object], citation_value)
            cited_input_id = citation.get("input_id")
            cited_line = citation.get("line")
            if (
                set(citation) != {"input_id", "line"}
                or not isinstance(cited_input_id, str)
                or not isinstance(cited_line, int)
                or isinstance(cited_line, bool)
            ):
                return _ParsedAnswer(valid_shape=False, answer=answer, cited=())
            cited.append((cited_input_id, cited_line))
        return _ParsedAnswer(valid_shape=True, answer=answer, cited=tuple(cited))

    @staticmethod
    def _is_grounded(
        parsed: _ParsedAnswer, persisted_lines: set[PersistedLine], *, expected: str
    ) -> bool:
        """Three conditions, all required: exact answer, cited lines real, answer read."""

        citations_grounded = parsed.valid_shape and all(
            any(
                stored_input == input_id and stored_line == line
                for stored_input, stored_line, _ in persisted_lines
            )
            for input_id, line in parsed.cited
        )
        answer_grounded = any(
            input_id == cited_input
            and line == cited_line
            and text.strip() == f"ROOT_CAUSE_CODE={expected}"
            for cited_input, cited_line in parsed.cited
            for input_id, line, text in persisted_lines
        )
        return parsed.answer == expected and citations_grounded and answer_grounded
