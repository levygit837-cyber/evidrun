"""One Subject interaction backed by a bounded provider/tool loop.

`execute` is a loop with three phases: send the bounded transcript, service any
tool calls, or accept the terminal answer. The phases are separate methods so the
loop reads as those three decisions rather than as one long body.

Two invariants the decomposition preserves:

- the tool-call budget is checked BEFORE the call runs, and exceeding it raises
  `SubjectBudgetExceeded` after the denial is traced;
- a Subject that answers without ever reading evidence is refused, because an
  unread answer is a guess.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from pydantic import TypeAdapter

from evidrun.contracts import SubjectEnvelope, capability_ref
from evidrun.infrastructure.providers import (
    ProviderFunctionCall,
    ProviderRequestError,
    extract_function_calls,
    extract_output_text,
    extract_response_id,
    extract_usage,
)
from evidrun.providers import ProviderProfile
from evidrun.runs.adapters.tool_read_text import ReadArtifactTextToolAdapter
from evidrun.runs.adapters.types import (
    ReadToolResult,
    SubjectBudgetExceeded,
    ToolTraceSink,
)
from evidrun.shared.ports import ProviderPort, SubjectResult
from evidrun.shared.types import canonical_json, sha256_json

_json_object = TypeAdapter(dict[str, object])

SUBJECT_INSTRUCTIONS = (
    "You are the Subject Agent in an auditable benchmark. Use only the objective, "
    "the SubjectEnvelope inventory, and the offered tools. You must read evidence "
    "before answering, never guess, and never claim access to paths or data not returned "
    "by a tool. Do not reveal private reasoning. Your final response must be only one "
    "JSON object with exactly these keys: answer and evidence. answer must be a string; "
    "evidence must be a non-empty array of objects with exactly input_id and line. Cite "
    "only numbered lines actually returned by read_text."
)


@dataclass(slots=True)
class _LoopState:
    """What accumulates across provider round-trips within one Subject turn."""

    next_input: str | list[dict[str, object]]
    transcript: list[dict[str, object]]
    tool_calls: int = 0
    provider_responses: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    evidence: list[str] = field(default_factory=list[str])
    provider_trace: list[dict[str, str]] = field(default_factory=list[dict[str, str]])


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
        self._assert_authorized_tool(envelope)
        max_tool_calls = envelope.budgets.max_tool_calls
        if max_tool_calls is None:
            raise ValueError("real agent execution requires max_tool_calls")
        initial_input = self._initial_input(envelope)
        state = _LoopState(
            next_input=initial_input,
            transcript=[{"role": "user", "content": initial_input}],
        )

        while True:
            response = await self._ask_provider(state)
            calls = extract_function_calls(response)
            if calls:
                self._service_tool_calls(
                    calls,
                    state=state,
                    envelope=envelope,
                    materialized_inputs=materialized_inputs,
                    trace_sink=trace_sink,
                    max_tool_calls=max_tool_calls,
                )
                continue
            return self._terminal_result(response, state)

    def _assert_authorized_tool(self, envelope: SubjectEnvelope) -> None:
        """Exactly one resolved capability, and it must be this closed read tool."""

        capabilities = envelope.effective_capabilities
        if (
            len(capabilities) != 1
            or capabilities[0].status != "resolved"
            or capabilities[0].resolved_ref != self.tool.ref
            or capabilities[0].effective_permissions != (self.tool.allowed_permission,)
            or capabilities[0].satisfied_authority_constraints
            != (self.tool.authority_constraint,)
        ):
            raise ValueError("SubjectEnvelope does not authorize the closed read tool")

    @staticmethod
    def _initial_input(envelope: SubjectEnvelope) -> str:
        inventory = ", ".join(
            f"{item.id} ({item.source.media_type}, {item.source.classification.value})"
            for item in envelope.inputs
        )
        return (
            f"Objective:\n{envelope.goal.instruction}\n\n"
            f"Authorized input inventory:\n{inventory}"
        )

    async def _ask_provider(self, state: _LoopState) -> Mapping[str, object]:
        """One provider round-trip, recording usage and a digest-only trace."""

        request: dict[str, object] = {
            "input": state.next_input,
            "instructions": SUBJECT_INSTRUCTIONS,
            "tools": [self.tool.provider_schema],
            # The configured Responses-compatible provider rejects the literal
            # `required` value. The adapter still enforces tool use before accepting
            # any terminal Subject response, so `auto` does not weaken the benchmark.
            "tool_choice": "auto",
            "max_output_tokens": self.transport_max_output_tokens,
        }
        response = await self.provider.invoke(request)
        state.provider_responses += 1
        state.provider_trace.append(
            {
                "request_digest": sha256_json(request),
                "response_id_digest": sha256_json(extract_response_id(response)),
                "response_digest": sha256_json(response),
            }
        )
        usage = extract_usage(response)
        state.input_tokens += usage.get("input_tokens", 0)
        state.output_tokens += usage.get("output_tokens", 0)
        return response

    def _service_tool_calls(
        self,
        calls: tuple[ProviderFunctionCall, ...],
        *,
        state: _LoopState,
        envelope: SubjectEnvelope,
        materialized_inputs: Mapping[str, str],
        trace_sink: ToolTraceSink,
        max_tool_calls: int,
    ) -> None:
        for call in calls:
            if call.name != self.tool.name:
                raise ValueError("provider attempted an unoffered tool")
            state.tool_calls += 1
            trace_sink.called(
                capability_ref=self.tool.ref,
                call_id=call.call_id,
                arguments=call.arguments,
            )
            state.transcript.append(
                {
                    "type": "function_call",
                    "call_id": call.call_id,
                    "name": call.name,
                    "arguments": call.arguments,
                }
            )
            if state.tool_calls > max_tool_calls:
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
                state.evidence.append(tool_output.evidence)
                state.transcript.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": tool_output.output,
                    }
                )
            else:
                state.transcript.append(
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
        state.next_input = list(state.transcript)

    def _terminal_result(
        self, response: Mapping[str, object], state: _LoopState
    ) -> SubjectResult:
        output = extract_output_text(response).strip()
        if not output:
            status = response.get("status")
            raise ProviderRequestError(
                "Provider returned no terminal Subject text"
                + (f" (status={status})" if isinstance(status, str) else "")
            )
        if state.tool_calls == 0:
            raise ValueError("real agent returned without using the required read tool")
        return SubjectResult(
            output=output,
            evidence=tuple(item for item in state.evidence if item),
            metadata={
                "provider_profile_id": self.profile.id,
                "provider_model": self.profile.model,
                "provider_reasoning_effort": self.profile.reasoning_effort,
                "provider_responses": state.provider_responses,
                "tool_calls": state.tool_calls,
                "input_tokens": state.input_tokens,
                "output_tokens": state.output_tokens,
                "transport_max_output_tokens": self.transport_max_output_tokens,
                "provider_trace_digest": sha256_json(state.provider_trace),
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
        """Run one tool call; a boundary violation is denied, not raised."""

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
