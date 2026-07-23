from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Literal, Protocol, cast

from pydantic import TypeAdapter

from evidrun.contracts import (
    AdmissionRecord,
    ArtifactRef,
    CapabilityDescriptorRef,
    EvaluationRecord,
    EvidenceRef,
    GoalStateTerminalResult,
    RunSpec,
    SubjectEnvelope,
)
from evidrun.contracts.compiler import (
    AdmissionService,
    CapabilityCatalogEntry,
    EvaluatorEnvelopeCompiler,
    ProviderCatalogEntry,
)
from evidrun.contracts.runtime import (
    AdmissionIssue,
    DimensionValue,
    EvaluationBoundary,
    ResolutionReason,
)
from evidrun.evaluations import ExactCauseGrader
from evidrun.infrastructure.artifacts.store import ArtifactStore
from evidrun.infrastructure.providers import (
    ProviderFunctionCall,
    ProviderRequestError,
    extract_function_calls,
    extract_output_text,
    extract_response_id,
    extract_usage,
)
from evidrun.providers import ProviderProfile
from evidrun.shared.capabilities import capability_ref
from evidrun.shared.ports import ProviderPort, SubjectResult
from evidrun.shared.types import (
    Classification,
    canonical_json,
    new_id,
    sha256_json,
    utc_now,
)
from evidrun.subject_runners import ScriptedLogInvestigator

_json_object = TypeAdapter(dict[str, object])


@dataclass(frozen=True)
class EvaluationOutcome:
    record: EvaluationRecord
    score: float
    passed: bool
    rationale: str
    evidence: tuple[str, ...]
    goal_result: GoalStateTerminalResult


class SubjectBudgetExceeded(RuntimeError):
    """A declared scientific budget was exhausted by the Subject adapter."""


class ToolTraceSink(Protocol):
    def called(
        self,
        *,
        capability_ref: CapabilityDescriptorRef,
        call_id: str,
        arguments: str,
    ) -> None: ...

    def completed(
        self,
        *,
        capability_ref: CapabilityDescriptorRef,
        call_id: str,
        result: str,
        classification: Classification,
    ) -> None: ...

    def denied(self, *, call_id: str, reason: str) -> None: ...

    def failed(
        self,
        *,
        capability_ref: CapabilityDescriptorRef,
        call_id: str,
        reason: str,
    ) -> None: ...


@dataclass(frozen=True)
class ReadToolResult:
    output: str
    evidence: str
    classification: Classification


class ArtifactInputMaterializer:
    def __init__(self, artifact_store: ArtifactStore) -> None:
        self.artifact_store = artifact_store

    def resolve_text(self, reference: ArtifactRef, *, project_id: str | None = None) -> str:
        if reference.classification.value not in {"public", "internal"}:
            raise ValueError("the active runtime rejects classified Subject inputs")
        if reference.media_type != "text/plain":
            raise ValueError("the deterministic adapter requires text/plain")
        content = self.artifact_store.get_verified(reference, project_id=project_id)
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("Subject input is not valid UTF-8") from exc


class ReadArtifactTextToolAdapter:
    """Read bounded line ranges from artifacts already admitted to SubjectEnvelope."""

    name = "read_text"
    ref = capability_ref("evidrun.tool", "read-artifact-text-v1")
    allowed_permission = "read:subject_artifacts"
    authority_constraint = "subject-envelope-only"
    max_lines_per_call = 80

    @property
    def provider_schema(self) -> dict[str, object]:
        return {
            "type": "function",
            "name": self.name,
            "description": (
                "Read a bounded range of numbered lines from one text input explicitly "
                "listed in the SubjectEnvelope. It cannot access paths, URLs, or other artifacts."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "input_id": {
                        "type": "string",
                        "description": "Exact SubjectEnvelope input id.",
                    },
                    "start_line": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "One-based first line to read.",
                    },
                    "max_lines": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": self.max_lines_per_call,
                        "description": "Maximum number of lines to return.",
                    },
                },
                "required": ["input_id", "start_line", "max_lines"],
                "additionalProperties": False,
            },
            "strict": True,
        }

    def execute(
        self,
        *,
        envelope: SubjectEnvelope,
        materialized_inputs: Mapping[str, str],
        arguments: Mapping[str, object],
    ) -> ReadToolResult:
        if set(arguments) != {"input_id", "start_line", "max_lines"}:
            raise PermissionError("tool arguments do not match the closed read schema")
        input_id = arguments.get("input_id")
        start_line = arguments.get("start_line")
        max_lines = arguments.get("max_lines")
        if not isinstance(input_id, str) or input_id not in materialized_inputs:
            raise PermissionError("requested input is outside the SubjectEnvelope")
        if (
            not isinstance(start_line, int)
            or isinstance(start_line, bool)
            or start_line < 1
            or not isinstance(max_lines, int)
            or isinstance(max_lines, bool)
            or max_lines < 1
            or max_lines > self.max_lines_per_call
        ):
            raise PermissionError("requested line range is outside the read tool limits")
        binding = next((item for item in envelope.inputs if item.id == input_id), None)
        if binding is None:
            raise PermissionError("requested input is outside the SubjectEnvelope")
        lines = materialized_inputs[input_id].splitlines()
        selected = lines[start_line - 1 : start_line - 1 + max_lines]
        numbered: list[dict[str, int | str]] = [
            {"line": start_line + index, "text": text} for index, text in enumerate(selected)
        ]
        evidence = "\n".join(str(item["text"]) for item in numbered)
        return ReadToolResult(
            output=canonical_json(
                {
                    "input_id": input_id,
                    "start_line": start_line,
                    "returned_lines": len(numbered),
                    "total_lines": len(lines),
                    "truncated": start_line - 1 + len(numbered) < len(lines),
                    "lines": numbered,
                }
            ),
            evidence=evidence,
            classification=binding.source.classification,
        )


class ScriptedLogInvestigatorAdapter:
    def __init__(self, runner: ScriptedLogInvestigator | None = None) -> None:
        self.runner = runner or ScriptedLogInvestigator()
        self.name = self.runner.name
        self.ref = capability_ref("evidrun.runner", self.runner.name)

    async def execute(
        self,
        envelope: SubjectEnvelope,
        materialized_inputs: Mapping[str, str],
        trace_sink: ToolTraceSink | None = None,
    ) -> SubjectResult:
        del trace_sink
        if len(materialized_inputs) != 1:
            raise ValueError("scripted runner requires exactly one materialized input")
        context = next(iter(materialized_inputs.values()))
        return await self.runner.execute(envelope.goal.instruction, context)


class ResponsesReadAgentAdapter:
    """One Subject interaction backed by a bounded provider/tool loop."""

    name = "responses-read-agent-v1"
    ref = capability_ref("evidrun.runner", name)
    transport_max_output_tokens = 768

    def __init__(
        self,
        provider: ProviderPort,
        profile: ProviderProfile,
        *,
        credential_available: bool,
        tool: ReadArtifactTextToolAdapter | None = None,
    ) -> None:
        self.provider = provider
        self.profile = profile
        self.credential_available = credential_available
        self.tool = tool or ReadArtifactTextToolAdapter()
        self.profile_digest = sha256_json(self.profile.public_dict())

    async def execute(
        self,
        envelope: SubjectEnvelope,
        materialized_inputs: Mapping[str, str],
        trace_sink: ToolTraceSink | None = None,
    ) -> SubjectResult:
        if trace_sink is None:
            raise ValueError("real agent execution requires a fenced tool trace sink")
        if (
            len(envelope.effective_capabilities) != 1
            or envelope.effective_capabilities[0].status != "resolved"
            or envelope.effective_capabilities[0].resolved_ref != self.tool.ref
            or envelope.effective_capabilities[0].effective_permissions
            != (self.tool.allowed_permission,)
            or envelope.effective_capabilities[0].satisfied_authority_constraints
            != (self.tool.authority_constraint,)
        ):
            raise ValueError("SubjectEnvelope does not authorize the closed read tool")
        max_tool_calls = envelope.budgets.max_tool_calls
        if max_tool_calls is None:
            raise ValueError("real agent execution requires max_tool_calls")
        input_inventory = ", ".join(
            f"{item.id} ({item.source.media_type}, {item.source.classification.value})"
            for item in envelope.inputs
        )
        instructions = (
            "You are the Subject Agent in an auditable benchmark. Use only the objective, "
            "the SubjectEnvelope inventory, and the offered tools. You must read evidence "
            "before answering, never guess, and never claim access to paths or data not returned "
            "by a tool. Do not reveal private reasoning. Your final response must be only one "
            "JSON object with exactly these keys: answer and evidence. answer must be a string; "
            "evidence must be a non-empty array of objects with exactly input_id and line. Cite "
            "only numbered lines actually returned by read_text."
        )
        initial_input = (
            f"Objective:\n{envelope.goal.instruction}\n\n"
            f"Authorized input inventory:\n{input_inventory}"
        )
        next_input: str | list[dict[str, object]] = initial_input
        transcript: list[dict[str, object]] = [{"role": "user", "content": initial_input}]
        # The configured Responses-compatible provider rejects the literal
        # `required` value. The adapter still enforces tool use before accepting
        # any terminal Subject response, so `auto` does not weaken the benchmark.
        tool_choice = "auto"
        tool_calls = 0
        provider_responses = 0
        input_tokens = 0
        output_tokens = 0
        evidence: list[str] = []
        provider_trace: list[dict[str, str]] = []

        while True:
            request: dict[str, object] = {
                "input": next_input,
                "instructions": instructions,
                "tools": [self.tool.provider_schema],
                "tool_choice": tool_choice,
                "max_output_tokens": self.transport_max_output_tokens,
            }
            response = await self.provider.invoke(request)
            provider_responses += 1
            response_id = extract_response_id(response)
            provider_trace.append(
                {
                    "request_digest": sha256_json(request),
                    "response_id_digest": sha256_json(response_id),
                    "response_digest": sha256_json(response),
                }
            )
            usage = extract_usage(response)
            input_tokens += usage.get("input_tokens", 0)
            output_tokens += usage.get("output_tokens", 0)
            calls = extract_function_calls(response)
            if calls:
                for call in calls:
                    if call.name != self.tool.name:
                        raise ValueError("provider attempted an unoffered tool")
                    tool_calls += 1
                    trace_sink.called(
                        capability_ref=self.tool.ref,
                        call_id=call.call_id,
                        arguments=call.arguments,
                    )
                    transcript.append(
                        {
                            "type": "function_call",
                            "call_id": call.call_id,
                            "name": call.name,
                            "arguments": call.arguments,
                        }
                    )
                    if tool_calls > max_tool_calls:
                        trace_sink.denied(
                            call_id=call.call_id,
                            reason="declared max_tool_calls budget exhausted",
                        )
                        raise SubjectBudgetExceeded("max_tool_calls budget exhausted")
                    tool_output = self._execute_tool_call(
                        call,
                        envelope=envelope,
                        materialized_inputs=materialized_inputs,
                        trace_sink=trace_sink,
                    )
                    if tool_output is not None:
                        evidence.append(tool_output.evidence)
                        transcript.append(
                            {
                                "type": "function_call_output",
                                "call_id": call.call_id,
                                "output": tool_output.output,
                            }
                        )
                    else:
                        transcript.append(
                            {
                                "type": "function_call_output",
                                "call_id": call.call_id,
                                "output": canonical_json(
                                    {"error": "request denied by the SubjectEnvelope boundary"}
                                ),
                            }
                        )
                # CLIProxyAPI runs the configured provider with non-persistent
                # Responses. Re-send the bounded transcript explicitly instead
                # of relying on previous_response_id server state.
                next_input = list(transcript)
                tool_choice = "auto"
                continue

            output = extract_output_text(response).strip()
            if not output:
                status = response.get("status")
                raise ProviderRequestError(
                    "Provider returned no terminal Subject text"
                    + (f" (status={status})" if isinstance(status, str) else "")
                )
            if tool_calls == 0:
                raise ValueError("real agent returned without using the required read tool")
            return SubjectResult(
                output=output,
                evidence=tuple(item for item in evidence if item),
                metadata={
                    "provider_profile_id": self.profile.id,
                    "provider_model": self.profile.model,
                    "provider_reasoning_effort": self.profile.reasoning_effort,
                    "provider_responses": provider_responses,
                    "tool_calls": tool_calls,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "transport_max_output_tokens": self.transport_max_output_tokens,
                    "provider_trace_digest": sha256_json(provider_trace),
                },
            )

    def _execute_tool_call(
        self,
        call: ProviderFunctionCall,
        *,
        envelope: SubjectEnvelope,
        materialized_inputs: Mapping[str, str],
        trace_sink: ToolTraceSink,
    ) -> ReadToolResult | None:
        try:
            arguments = _json_object.validate_json(call.arguments)
            result = self.tool.execute(
                envelope=envelope,
                materialized_inputs=materialized_inputs,
                arguments=arguments,
            )
        except PermissionError, ValueError:
            trace_sink.denied(
                call_id=call.call_id,
                reason="tool request violates the closed read boundary",
            )
            return None
        except Exception:
            trace_sink.failed(
                capability_ref=self.tool.ref,
                call_id=call.call_id,
                reason="read tool execution failed",
            )
            raise
        trace_sink.completed(
            capability_ref=self.tool.ref,
            call_id=call.call_id,
            result=result.output,
            classification=result.classification,
        )
        return result


class ExactCauseGraderAdapter:
    ref = capability_ref("evidrun.evaluator", "exact-root-cause-legacy-v1")

    @classmethod
    def supports(cls, spec: RunSpec) -> bool:
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
        persisted_lines: set[tuple[str, int, str]] = set()
        evidence_refs: list[EvidenceRef] = [EvidenceRef(ref=f"event:{response_event_id}")]
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
            lines_value = document.get("lines")
            if not isinstance(lines_value, list):
                raise ValueError("persisted read-tool result has an invalid shape")
            input_id = document.get("input_id")
            if not isinstance(input_id, str):
                raise ValueError("persisted read-tool result is missing input_id")
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
                    persisted_lines.add((input_id, line_number, line_text))
            event_id = event.get("event_id")
            if isinstance(event_id, str):
                evidence_refs.append(EvidenceRef(ref=f"event:{event_id}"))

        valid_shape = False
        cited: list[tuple[str, int]] = []
        answer: object = None
        try:
            output = _json_object.validate_json(result.output)
        except ValueError:
            output = None
        if output is not None and set(output) == {"answer", "evidence"}:
            answer = output.get("answer")
            citations = output.get("evidence")
            if isinstance(citations, list) and citations:
                valid_shape = True
                for citation_value in cast(list[object], citations):
                    if not isinstance(citation_value, dict):
                        valid_shape = False
                        break
                    citation = cast(dict[str, object], citation_value)
                    cited_input_id = citation.get("input_id")
                    cited_line = citation.get("line")
                    if (
                        set(citation) != {"input_id", "line"}
                        or not isinstance(cited_input_id, str)
                        or not isinstance(cited_line, int)
                        or isinstance(cited_line, bool)
                    ):
                        valid_shape = False
                        break
                    cited.append((cited_input_id, cited_line))
        citations_grounded = valid_shape and all(
            any(
                stored_input == input_id and stored_line == line
                for stored_input, stored_line, _ in persisted_lines
            )
            for input_id, line in cited
        )
        answer_grounded = any(
            input_id == cited_input
            and line == cited_line
            and text.strip() == f"ROOT_CAUSE_CODE={expected}"
            for cited_input, cited_line in cited
            for input_id, line, text in persisted_lines
        )
        passed = answer == expected and citations_grounded and answer_grounded
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
                    evidence_refs=tuple(evidence_refs),
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
            evidence=tuple(item.ref for item in evidence_refs),
            goal_result=GoalStateTerminalResult(state="achieved" if passed else "not_achieved"),
        )


class RuntimeAdapterCatalog:
    def __init__(
        self,
        *,
        subject: ScriptedLogInvestigatorAdapter | None = None,
        real_subject: ResponsesReadAgentAdapter | None = None,
        evaluator: ExactCauseGraderAdapter | None = None,
        real_evaluator: ExactReadAnswerGraderAdapter | None = None,
        materializer: ArtifactInputMaterializer | None = None,
        project_id_for_spec: Callable[[RunSpec], str] | None = None,
    ) -> None:
        self.subject = subject or ScriptedLogInvestigatorAdapter()
        self.real_subject = real_subject
        self.evaluator = evaluator or ExactCauseGraderAdapter()
        self.real_evaluator = real_evaluator or ExactReadAnswerGraderAdapter()
        self.materializer = materializer
        self.project_id_for_spec = project_id_for_spec
        self._subjects: dict[
            tuple[str, str, str, str],
            ScriptedLogInvestigatorAdapter | ResponsesReadAgentAdapter,
        ] = {self._subject_key(self.subject.ref): self.subject}
        if self.real_subject is not None:
            self._subjects[self._subject_key(self.real_subject.ref)] = self.real_subject

    @staticmethod
    def _subject_key(reference: CapabilityDescriptorRef) -> tuple[str, str, str, str]:
        return (
            reference.namespace,
            reference.name,
            reference.version,
            reference.digest,
        )

    def admission_service(self) -> AdmissionService:
        capabilities: tuple[CapabilityCatalogEntry, ...] = ()
        providers: tuple[ProviderCatalogEntry, ...] = ()
        runtime_capabilities: tuple[str, ...] = ()
        network_modes = ("disabled",)
        supported_budget_fields: tuple[str, ...] = ()
        supports_raw_encrypted_capture = False
        if self.real_subject is not None:
            tool = self.real_subject.tool
            capabilities = (
                CapabilityCatalogEntry(
                    ref=tool.ref,
                    adapter="read-artifact-text@1",
                    allowed_permissions=frozenset({tool.allowed_permission}),
                    compatible_interface_versions=frozenset({"1"}),
                    satisfied_authority_constraints=frozenset({tool.authority_constraint}),
                ),
            )
            providers = (
                ProviderCatalogEntry(
                    profile_id=self.real_subject.profile.id,
                    profile_digest=self.real_subject.profile_digest,
                    model=self.real_subject.profile.model,
                    reasoning_effort=self.real_subject.profile.reasoning_effort,
                    adapter="openai-responses@1",
                ),
            )
            runtime_capabilities = ("provider_tool_loop",)
            network_modes = ("disabled", "provider_only")
            supported_budget_fields = ("max_tool_calls",)
            supports_raw_encrypted_capture = True
        return AdmissionService(
            runners=tuple(adapter.ref for adapter in self._subjects.values()),
            capabilities=capabilities,
            providers=providers,
            runtime_capabilities=runtime_capabilities,
            network_modes=network_modes,
            supported_budget_fields=supported_budget_fields,
            supports_raw_encrypted_capture=supports_raw_encrypted_capture,
            execution_validators=(self.validate_spec,),
        )

    def validate_spec(self, spec: RunSpec) -> tuple[AdmissionIssue, ...]:
        issues: list[AdmissionIssue] = []
        subject = self._subjects.get(self._subject_key(spec.agent_inventory.runner_ref))
        if subject is None:
            return (
                self._issue(
                    "runner_adapter",
                    "the admitted runner has no exact executable adapter",
                ),
            )
        visible_inputs = tuple(
            item
            for item in spec.scenario.input_bindings
            if item.visibility in {"subject", "subject_and_evaluator"}
        )
        if len(spec.scenario.input_bindings) != 1:
            issues.append(
                self._issue(
                    "scenario_input_count",
                    "the active adapters require exactly one scenario input in total",
                )
            )
        if len(visible_inputs) != 1:
            issues.append(
                self._issue(
                    "subject_input_count",
                    "the active Subject adapter requires exactly one Subject-visible input",
                )
            )
        elif visible_inputs[0].source.media_type != "text/plain":
            issues.append(
                self._issue(
                    "subject_input_media_type",
                    "the active Subject adapter requires a text/plain input",
                )
            )
        elif self.materializer is None or self.project_id_for_spec is None:
            issues.append(
                self._issue(
                    "subject_input_materializer",
                    "the active catalog has no artifact materializer",
                )
            )
        else:
            try:
                self.materializer.resolve_text(
                    visible_inputs[0].source,
                    project_id=self.project_id_for_spec(spec),
                )
            except FileNotFoundError, KeyError, ValueError:
                issues.append(
                    self._issue(
                        "subject_input_artifact",
                        "the Subject input cannot be verified in the canonical ArtifactStore",
                    )
                )
        if spec.context_policy is None:
            issues.append(
                self._issue(
                    "context_policy",
                    "the active Subject adapter requires a ContextPolicy",
                )
            )
        if spec.extensions:
            issues.append(
                self._issue(
                    "runtime_extensions",
                    "the active adapters do not execute RunSpec extensions",
                )
            )
        if spec.evaluation_plan.disclosure.hidden_input_refs:
            issues.append(
                self._issue(
                    "evaluation_hidden_inputs",
                    "the active evaluator adapter does not consume hidden input artifacts",
                )
            )
        if spec.evaluation_plan.blinding_policy.hidden_fields:
            issues.append(
                self._issue(
                    "evaluation_blinding",
                    "the active evaluator adapter does not implement field blinding",
                )
            )
        if spec.evaluation_plan.aggregation is not None:
            issues.append(
                self._issue(
                    "evaluation_aggregation",
                    "the active evaluator adapter does not execute an aggregation projector",
                )
            )
        if isinstance(subject, ScriptedLogInvestigatorAdapter):
            issues.extend(self._validate_scripted_spec(spec))
        else:
            issues.extend(self._validate_real_spec(spec, subject))
        if not any(evaluator.supports(spec) for evaluator in (self.evaluator, self.real_evaluator)):
            issues.append(
                self._issue(
                    "evaluator_adapter",
                    "the EvaluationPlan has no exact deterministic evaluator adapter",
                )
            )
        return tuple(issues)

    def _validate_scripted_spec(self, spec: RunSpec) -> tuple[AdmissionIssue, ...]:
        issues: list[AdmissionIssue] = []
        if not self.evaluator.supports(spec):
            issues.append(
                self._issue(
                    "scripted_evaluator",
                    "the scripted runner requires the exact legacy deterministic evaluator",
                )
            )
        if spec.agent_inventory.provider_profile_id is not None:
            issues.append(
                self._issue(
                    "offline_provider",
                    "the scripted adapter does not invoke a provider",
                )
            )
        if spec.agent_inventory.capability_requirements:
            issues.append(
                self._issue(
                    "offline_capabilities",
                    "the scripted adapter does not execute tools or skills",
                )
            )
        if spec.workspace.network_policy.mode != "disabled":
            issues.append(
                self._issue(
                    "offline_network",
                    "the scripted adapter requires disabled network",
                )
            )
        if spec.budgets.max_tool_calls is not None:
            issues.append(
                self._issue(
                    "offline_tool_budget",
                    "the scripted adapter cannot consume a tool-call budget",
                )
            )
        if spec.capture_policy.default_mode == "raw_encrypted":
            issues.append(
                self._issue(
                    "offline_raw_capture",
                    "the scripted compatibility adapter does not use raw encrypted capture",
                )
            )
        return tuple(issues)

    def _validate_real_spec(
        self, spec: RunSpec, subject: ResponsesReadAgentAdapter
    ) -> tuple[AdmissionIssue, ...]:
        issues: list[AdmissionIssue] = []
        if not self.real_evaluator.supports(spec):
            issues.append(
                self._issue(
                    "real_evaluator",
                    "the real read agent requires the strict read-answer evaluator",
                )
            )
        if spec.agent_inventory.provider_profile_id != subject.profile.id:
            issues.append(
                self._issue(
                    "provider_profile",
                    "the real adapter requires its exact provider profile",
                    category="provider",
                )
            )
        if not subject.credential_available:
            issues.append(
                self._issue(
                    "provider_credential",
                    "the provider credential is unavailable to the worker composition",
                    category="provider",
                    code="unavailable",
                )
            )
        requirements = spec.agent_inventory.capability_requirements
        if (
            len(requirements) != 1
            or requirements[0].kind != "tool"
            or requirements[0].capability_ref != subject.tool.ref
            or not requirements[0].required
            or requirements[0].minimum_interface_version != "1"
            or requirements[0].requested_permissions != (subject.tool.allowed_permission,)
            or requirements[0].exposure != "schema_only"
            or requirements[0].authority_constraints != (subject.tool.authority_constraint,)
            or requirements[0].instruction_refs
        ):
            issues.append(
                self._issue(
                    "read_tool_contract",
                    "the real adapter requires the exact closed read-tool capability",
                    category="capability",
                )
            )
        if spec.workspace.network_policy.mode != "provider_only":
            issues.append(
                self._issue(
                    "provider_network",
                    "the real adapter requires provider_only network",
                    category="policy",
                    code="denied",
                )
            )
        if spec.budgets.max_tool_calls is None or spec.budgets.max_tool_calls > 8:
            issues.append(
                self._issue(
                    "max_tool_calls",
                    "the real adapter requires max_tool_calls between 1 and 8",
                )
            )
        if not (
            spec.capture_policy.default_mode == "raw_encrypted"
            and spec.capture_policy.raw_sensitive == "opt_in"
        ):
            issues.append(
                self._issue(
                    "recoverable_subject_output",
                    "the real adapter requires opt-in encrypted raw capture for recovery",
                    category="policy",
                    code="denied",
                )
            )
        return tuple(issues)

    def subject_for(
        self, spec: RunSpec, admission: AdmissionRecord
    ) -> ScriptedLogInvestigatorAdapter | ResponsesReadAgentAdapter:
        subject = self._subjects.get(self._subject_key(spec.agent_inventory.runner_ref))
        if (
            subject is None
            or admission.resolved_inventory.runner_ref != subject.ref
            or admission.run_spec_digest != spec.digest
            or admission.decision != "admitted"
        ):
            raise ValueError("admitted runner cannot be resolved by the active catalog")
        if isinstance(subject, ResponsesReadAgentAdapter):
            resolved = admission.resolved_inventory
            if (
                resolved.provider_profile_id != subject.profile.id
                or resolved.provider_profile_digest != subject.profile_digest
                or resolved.provider_model != subject.profile.model
                or resolved.provider_reasoning_effort != subject.profile.reasoning_effort
                or resolved.provider_adapter != "openai-responses@1"
                or len(resolved.capabilities) != 1
                or resolved.capabilities[0].status != "resolved"
                or resolved.capabilities[0].resolved_ref != subject.tool.ref
            ):
                raise ValueError(
                    "admitted provider or tool resolution drifted from the active catalog"
                )
        return subject

    def evaluator_for(
        self, spec: RunSpec
    ) -> ExactCauseGraderAdapter | ExactReadAnswerGraderAdapter:
        for evaluator in (self.evaluator, self.real_evaluator):
            if evaluator.supports(spec):
                return evaluator
        raise ValueError("EvaluationPlan cannot be resolved by the active catalog")

    @staticmethod
    def _issue(
        subject_ref: str,
        detail: str,
        *,
        category: Literal["runtime", "provider", "capability", "policy"] = "runtime",
        code: Literal["unsupported", "denied", "unavailable", "digest_mismatch"] = ("unsupported"),
    ) -> AdmissionIssue:
        return AdmissionIssue(
            category=category,
            subject_ref=subject_ref,
            reason=ResolutionReason(code=code, detail=detail),
            blocking=True,
        )
