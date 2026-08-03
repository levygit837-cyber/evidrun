from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from evidrun.contracts.lab_agent.envelope import (
    LabAgentEnvelope,
    LabAgentMessage,
    LabAgentMessageRole,
    LabAgentTurnLimits,
)
from evidrun.contracts.lab_agent.errors import (
    LabAgentError,
    LabAgentErrorCode,
)
from evidrun.contracts.lab_agent.scope import LabAgentSessionScope
from evidrun.lab.loop import LabAgentLoop
from evidrun.lab.protocol import LabToolContext, LabToolResult, ToolAvailability
from evidrun.lab.tools import build_catalog
from evidrun.lab.turn import LabTurnTerminalName, TurnBudget, refusal_error


class FakeProvider:
    def __init__(self, responses: list[Mapping[str, Any] | Exception]) -> None:
        self.responses = responses
        self.requests: list[Mapping[str, Any]] = []

    async def invoke(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        self.requests.append(request)
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class FakeTraceSink:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def append_tool_trace(self, **values: Any) -> None:
        self.rows.append(values)


class StubTool:
    availability = ToolAvailability()

    def __init__(self, name: str = "read_run") -> None:
        self.name = name
        self.executions: list[Mapping[str, Any]] = []

    def provider_schema(self) -> Mapping[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {"run_id": {"type": "string", "maxLength": 20}},
            "required": ["run_id"],
        }

    def execute(self, arguments: Mapping[str, Any], context: LabToolContext) -> LabToolResult:
        self.executions.append(arguments)
        return LabToolResult(
            content={"run_id": arguments["run_id"]},
            requested_refs=(str(arguments["run_id"]),),
            returned_refs=(str(arguments["run_id"]),),
        )


class RecordingPolicy:
    def __init__(
        self,
        *,
        scope_error: LabAgentError | None = None,
        classification_error: LabAgentError | None = None,
    ) -> None:
        self.scope_error = scope_error
        self.classification_error = classification_error
        self.steps: list[str] = []

    def check_scope(self, tool: Any, arguments: Any, context: Any) -> LabAgentError | None:
        del tool, arguments, context
        self.steps.append("scope")
        return self.scope_error

    def check_classification(self, tool: Any, arguments: Any, context: Any) -> LabAgentError | None:
        del tool, arguments, context
        self.steps.append("classification")
        return self.classification_error


def envelope(
    *tools: str,
    max_tools: int = 3,
    max_round_trips: int = 4,
    max_refusals: int = 3,
) -> LabAgentEnvelope:
    return LabAgentEnvelope(
        session_id="chat_1",
        scope=LabAgentSessionScope(workspace_id="ws_1", project_id="project_1"),
        history=(
            LabAgentMessage(role=LabAgentMessageRole.HUMAN, sequence=1, content="Leia a run."),
        ),
        offered_tools=tools,
        limits=LabAgentTurnLimits(
            max_tool_calls_per_turn=max_tools,
            max_provider_round_trips_per_turn=max_round_trips,
            max_wall_seconds_per_turn=30,
            max_refusals_per_turn=max_refusals,
            max_output_tokens_per_round_trip=256,
        ),
    )


def call(response_id: str, name: str, arguments: str, call_id: str = "call_1") -> dict[str, Any]:
    return {
        "id": response_id,
        "output": [
            {"type": "function_call", "call_id": call_id, "name": name, "arguments": arguments}
        ],
        "usage": {"input_tokens": 3, "output_tokens": 2, "total_tokens": 5},
    }


def answer(response_id: str = "resp_answer", text: str = "Pronto.") -> dict[str, Any]:
    return {"id": response_id, "output_text": text, "output": []}


def refusal(code: LabAgentErrorCode) -> LabAgentError:
    return LabAgentError(
        stage=code.stage,
        code=code,
        message="Chamada recusada.",
        remediation="Corrija a chamada.",
        tool_name="read_run",
    )


@pytest.mark.anyio
async def test_tool_budget_is_denied_and_traced_before_effect() -> None:
    tool = StubTool()
    provider = FakeProvider(
        [
            call("r1", "read_run", '{"run_id":"run_1"}'),
            call("r2", "read_run", '{"run_id":"run_2"}', "call_2"),
        ]
    )
    trace = FakeTraceSink()

    result = await LabAgentLoop(provider, build_catalog([tool])).execute(
        envelope("read_run", max_tools=1), trace_sink=trace
    )

    assert result.name is LabTurnTerminalName.BUDGET_EXHAUSTED
    assert result.budget == "max_tool_calls_per_turn"
    assert tool.executions == [{"run_id": "run_1"}]
    assert trace.rows[-1]["outcome"] == "refused"
    assert trace.rows[-1]["refusal_code"] == "budget.tool_calls_exhausted"


@pytest.mark.anyio
async def test_unknown_tool_does_not_consume_tool_budget() -> None:
    tool = StubTool()
    provider = FakeProvider(
        [
            call("r1", "missing", "{}"),
            call("r2", "read_run", '{"run_id":"run_1"}', "call_2"),
            answer(),
        ]
    )
    result = await LabAgentLoop(provider, build_catalog([tool])).execute(
        envelope("read_run", max_tools=1), trace_sink=FakeTraceSink()
    )

    assert result.name is LabTurnTerminalName.ANSWERED
    assert result.tool_calls == 1
    assert tool.executions == [{"run_id": "run_1"}]


@pytest.mark.anyio
async def test_schema_precedes_scope_and_scope_precedes_classification() -> None:
    tool = StubTool()
    policy = RecordingPolicy(
        scope_error=refusal(LabAgentErrorCode.SCOPE_TARGET_NOT_VISIBLE),
        classification_error=refusal(LabAgentErrorCode.CLASSIFICATION_GRANT_REQUIRED),
    )
    provider = FakeProvider([call("r1", "read_run", '{"other":"x"}'), answer()])
    trace = FakeTraceSink()
    result = await LabAgentLoop(provider, build_catalog([tool])).execute(
        envelope("read_run"), trace_sink=trace, policy=policy
    )
    assert result.name is LabTurnTerminalName.ANSWERED
    assert policy.steps == []
    assert trace.rows[0]["refusal_code"] == "schema.argument_set_invalid"

    policy.steps.clear()
    provider = FakeProvider([call("r2", "read_run", '{"run_id":"run_1"}'), answer()])
    trace = FakeTraceSink()
    await LabAgentLoop(provider, build_catalog([tool])).execute(
        envelope("read_run"), trace_sink=trace, policy=policy
    )
    assert policy.steps == ["scope"]
    assert trace.rows[0]["refusal_code"] == "scope.target_not_visible"

    policy = RecordingPolicy(
        classification_error=refusal(LabAgentErrorCode.CLASSIFICATION_GRANT_REQUIRED)
    )
    provider = FakeProvider([call("r3", "read_run", '{"run_id":"run_1"}'), answer()])
    trace = FakeTraceSink()
    await LabAgentLoop(provider, build_catalog([tool])).execute(
        envelope("read_run"), trace_sink=trace, policy=policy
    )
    assert policy.steps == ["scope", "classification"]
    assert trace.rows[0]["refusal_code"] == "classification.grant_required"


@pytest.mark.anyio
async def test_refusal_budget_terminates_refusal_only_turn() -> None:
    provider = FakeProvider([call("r1", "missing", "{}")])
    result = await LabAgentLoop(provider, build_catalog([])).execute(
        envelope(max_refusals=1), trace_sink=FakeTraceSink()
    )

    assert result.name is LabTurnTerminalName.BUDGET_EXHAUSTED
    assert result.budget == "max_refusals_per_turn"
    assert result.complete is False


@pytest.mark.anyio
async def test_exact_repeated_refusal_stops_before_third_round_trip() -> None:
    provider = FakeProvider(
        [call("r1", "missing", '{"id":"same"}'), call("r2", "missing", '{"id":"same"}')]
    )
    result = await LabAgentLoop(provider, build_catalog([])).execute(
        envelope(max_refusals=3), trace_sink=FakeTraceSink()
    )

    assert result.name is LabTurnTerminalName.REPEATED_REFUSAL
    assert len(provider.requests) == 2


@pytest.mark.anyio
async def test_different_arguments_are_not_repeated_refusal() -> None:
    provider = FakeProvider(
        [
            call("r1", "missing", '{"id":"one"}'),
            call("r2", "missing", '{"id":"two"}'),
            answer(),
        ]
    )
    result = await LabAgentLoop(provider, build_catalog([])).execute(
        envelope(max_refusals=3), trace_sink=FakeTraceSink()
    )

    assert result.name is LabTurnTerminalName.ANSWERED
    assert len(provider.requests) == 3


@pytest.mark.anyio
async def test_cancel_after_draft_keeps_trace_and_returns_partial_terminal() -> None:
    tool = StubTool("propose_draft")
    trace = FakeTraceSink()
    checks = iter([False, True])
    result = await LabAgentLoop(
        FakeProvider([call("r1", "propose_draft", '{"run_id":"draft_1"}')]),
        build_catalog([tool]),
    ).execute(
        envelope("propose_draft"),
        trace_sink=trace,
        cancelled=lambda: next(checks, True),
    )

    assert result.name is LabTurnTerminalName.CANCELLED
    assert result.complete is False
    assert trace.rows[0]["outcome"] == "completed"
    assert result.returned_refs == ("draft_1",)


@pytest.mark.anyio
async def test_proposed_and_ui_events_are_distinct_from_answered() -> None:
    tool = StubTool("propose_draft")
    events: list[Mapping[str, Any]] = []
    provider = FakeProvider(
        [call("r1", "propose_draft", '{"run_id":"draft_1"}'), answer(text="Draft pronto.")]
    )
    result = await LabAgentLoop(provider, build_catalog([tool])).execute(
        envelope("propose_draft"), trace_sink=FakeTraceSink(), emit=events.append
    )

    assert result.name is LabTurnTerminalName.PROPOSED
    assert [event["type"] for event in events] == [
        "status",
        "tool",
        "tool",
        "message",
        "status",
        "done",
    ]
    assert provider.requests[0]["tool_choice"] == "auto"
    assert provider.requests[0]["max_output_tokens"] == 256
    assert len(provider.requests[1]["input"]) == 3


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("responses", "expected"),
    [
        ([answer()], LabTurnTerminalName.ANSWERED),
        ([ValueError("provider")], LabTurnTerminalName.PROVIDER_FAILED),
    ],
)
async def test_terminal_names_are_observable(
    responses: list[Mapping[str, Any] | Exception], expected: LabTurnTerminalName
) -> None:
    result = await LabAgentLoop(FakeProvider(responses), build_catalog([])).execute(
        envelope(), trace_sink=FakeTraceSink()
    )
    assert result.name is expected


@pytest.mark.anyio
async def test_cancelled_at_initial_safe_boundary_does_not_call_provider() -> None:
    provider = FakeProvider([answer()])
    result = await LabAgentLoop(provider, build_catalog([])).execute(
        envelope(), trace_sink=FakeTraceSink(), cancelled=lambda: True
    )
    assert result.name is LabTurnTerminalName.CANCELLED
    assert provider.requests == []


def test_every_refusal_code_the_loop_raises_has_its_own_remediation() -> None:
    """Sem fallback genérico: recusa que só nega faz o modelo tentar variações até o budget.

    A tabela de errors-v1 nomeia "A chamada foi recusada." como remediação causadora de laço.
    Este teste falha se alguém introduzir código sem texto próprio, no import e não no laço.
    """

    raised = {
        LabAgentErrorCode.CATALOG_TOOL_UNKNOWN,
        LabAgentErrorCode.CATALOG_TOOL_NOT_OFFERED,
        LabAgentErrorCode.BUDGET_TOOL_CALLS_EXHAUSTED,
        LabAgentErrorCode.BUDGET_WALL_TIME_EXHAUSTED,
        LabAgentErrorCode.SCHEMA_ARGUMENT_SET_INVALID,
        LabAgentErrorCode.SCHEMA_ARGUMENT_TYPE_INVALID,
        LabAgentErrorCode.SCHEMA_ARGUMENT_LIMIT_EXCEEDED,
        LabAgentErrorCode.SCHEMA_SCOPE_ARGUMENT_FORBIDDEN,
    }

    for code in raised:
        error = refusal_error(code, tool_name="read_run")
        assert error.code is code
        assert error.stage is code.stage
        assert error.remediation.strip()
        assert "A chamada foi recusada" not in error.message


def test_a_code_without_declared_text_fails_loudly() -> None:
    """Código novo sem texto é defeito de programação, não degradação aceitável."""

    with pytest.raises(ValueError, match="without a declared message"):
        refusal_error(LabAgentErrorCode.SCOPE_TARGET_NOT_VISIBLE)


def test_budget_names_come_from_the_enum_not_free_text() -> None:
    """O teto atravessa o stream até a UI, que precisa distinguir qual foi alcançado."""

    assert TurnBudget.TOOL_CALLS.value == "max_tool_calls_per_turn"
    assert TurnBudget.ROUND_TRIPS.value == "max_provider_round_trips_per_turn"
    assert TurnBudget.WALL_SECONDS.value == "max_wall_seconds_per_turn"
    assert TurnBudget.REFUSALS.value == "max_refusals_per_turn"
