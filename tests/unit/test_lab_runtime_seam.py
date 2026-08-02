from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from evidrun.contracts.lab_agent.scope import LabAgentSessionForm, LabAgentSessionScope
from evidrun.lab.protocol import (
    LabTool,
    LabToolContext,
    LabToolResult,
    ToolAvailability,
    declared_argument_keys,
    required_argument_keys,
)
from evidrun.lab.tools import build_catalog, offered_tools


class _StubTool:
    """Uma tool mínima que satisfaz o Protocol, para exercitar a costura sem runtime."""

    def __init__(self, name: str, availability: ToolAvailability | None = None) -> None:
        self._name = name
        self._availability = availability or ToolAvailability()

    @property
    def name(self) -> str:
        return self._name

    @property
    def availability(self) -> ToolAvailability:
        return self._availability

    def provider_schema(self) -> Mapping[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {"run_id": {"type": "string"}, "limit": {"type": "integer"}},
            "required": ["run_id"],
        }

    def execute(self, arguments: Mapping[str, Any], context: LabToolContext) -> LabToolResult:
        return LabToolResult(
            content={"echo": dict(arguments)},
            requested_refs=(str(arguments.get("run_id", "")),),
            returned_refs=(),
        )


GENERAL_ONLY = ToolAvailability(forms=frozenset(LabAgentSessionForm))


def test_a_stub_tool_satisfies_the_protocol() -> None:
    assert isinstance(_StubTool("read_run"), LabTool)


def test_availability_defaults_exclude_general_chat() -> None:
    """General chat oferece exatamente duas tools; o default não pode ser uma delas.

    Se o default incluísse General, cada tool nova de leitura vazaria para o Workspace scope
    por esquecimento, e o ADR 0021 seria violado por omissão em vez de por decisão.
    """

    availability = ToolAvailability()

    assert not availability.offers(LabAgentSessionForm.GENERAL)
    assert availability.offers(LabAgentSessionForm.PROJECT)
    assert availability.offers(LabAgentSessionForm.FOCUSED)


def test_offered_tools_filters_by_session_form_in_stable_order() -> None:
    catalog = build_catalog(
        [
            _StubTool("read_run"),
            _StubTool("list_projects", GENERAL_ONLY),
            _StubTool("read_capability_catalog", GENERAL_ONLY),
        ]
    )

    general = offered_tools(catalog, LabAgentSessionForm.GENERAL)
    project = offered_tools(catalog, LabAgentSessionForm.PROJECT)

    assert list(general) == ["list_projects", "read_capability_catalog"]
    assert list(project) == ["list_projects", "read_capability_catalog", "read_run"]


def test_duplicate_tool_name_is_refused() -> None:
    with pytest.raises(ValueError, match="declared twice"):
        build_catalog([_StubTool("read_run"), _StubTool("read_run")])


def test_declared_keys_come_from_the_schema_itself() -> None:
    """As chaves saem do schema, não de uma segunda lista que divergiria no primeiro patch."""

    schema = _StubTool("read_run").provider_schema()

    assert declared_argument_keys(schema) == {"run_id", "limit"}
    assert required_argument_keys(schema) == {"run_id"}


@pytest.mark.parametrize("schema", [{}, {"properties": "nao-e-mapa"}, {"required": "run_id"}])
def test_key_helpers_never_raise_on_malformed_schema(schema: Mapping[str, Any]) -> None:
    """Schema malformado devolve conjunto vazio, que recusa por igualdade exata.

    Levantar aqui transformaria um schema errado em erro interno; devolver vazio faz a
    comparação de igualdade recusar a chamada, que é a recusa nomeada correta.
    """

    assert declared_argument_keys(schema) == frozenset()
    assert required_argument_keys(schema) == frozenset()


def test_result_keeps_requested_and_returned_refs_apart() -> None:
    """A diferença entre pedido e devolvido é a evidência de que o enforcement recusou."""

    context = LabToolContext(
        scope=LabAgentSessionScope(workspace_id="ws-1", project_id="proj-1"),
        session_id="chat-1",
        turn_sequence=1,
    )

    result = _StubTool("read_run").execute({"run_id": "run-9"}, context)

    assert result.requested_refs == ("run-9",)
    assert result.returned_refs == ()
