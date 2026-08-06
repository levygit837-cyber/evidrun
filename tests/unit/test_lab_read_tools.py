from __future__ import annotations

import sys
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from evidrun.contracts.admission.envelope import RuntimeCapabilityEnvelope
from evidrun.contracts.lab_agent.errors import LabAgentErrorCode
from evidrun.contracts.lab_agent.scope import LabAgentSessionForm, LabAgentSessionScope
from evidrun.lab.protocol import LabToolContext, LabToolRejected
from evidrun.lab.tools import build_catalog, build_read_tools, offered_tools
from evidrun.lab.tools.read_port import LabReadRepository
from evidrun.lab.tools.registry import AdmissionCapabilityCatalog, CapabilityCatalog
from evidrun.lab.turn import validate_schema


class FakeReadRepository:
    def __init__(self) -> None:
        self.scopes: list[LabAgentSessionScope] = []

    def list_projects(self, scope: LabAgentSessionScope) -> Sequence[Mapping[str, Any]]:
        self.scopes.append(scope)
        return ({"id": "project-1", "name": "Alpha", "created_at": "2026-08-02"},)

    def read_contract_revision(
        self, scope: LabAgentSessionScope, revision_ref: str
    ) -> Mapping[str, Any]:
        self.scopes.append(scope)
        return {"document": {"title": "Study"}, "status": "accepted", "digest": "d" * 64}

    def list_runs(
        self, scope: LabAgentSessionScope, *, limit: int, status: str | None
    ) -> Sequence[Mapping[str, Any]]:
        self.scopes.append(scope)
        return ()

    def read_run(self, scope: LabAgentSessionScope, run_id: str) -> Mapping[str, Any]:
        self.scopes.append(scope)
        return {"run_id": run_id, "status": "completed"}

    def read_run_events(
        self,
        scope: LabAgentSessionScope,
        run_id: str,
        *,
        after_sequence: int,
        limit: int,
    ) -> Sequence[Mapping[str, Any]]:
        self.scopes.append(scope)
        return ({"event_id": "event-1", "sequence": 1},)

    def read_evaluation_records(
        self, scope: LabAgentSessionScope, run_id: str
    ) -> Sequence[Mapping[str, Any]]:
        self.scopes.append(scope)
        return ({"record_id": "evaluation-1", "dimensions": [], "source_type": "model_judge"},)

    def read_comparison(
        self, scope: LabAgentSessionScope, comparison_id: str
    ) -> Mapping[str, Any]:
        self.scopes.append(scope)
        return {"comparison_id": comparison_id, "delta": 0.5}

    def read_admission(
        self, scope: LabAgentSessionScope, admission_id: str
    ) -> Mapping[str, Any]:
        self.scopes.append(scope)
        return {"decision": "rejected", "rejection_codes": ["unsupported"]}

    def read_capability_catalog(self) -> CapabilityCatalog:
        return CapabilityCatalog(
            admitted=({"name": "single_turn"},),
            active_rejections=(
                {"name": "max_turns", "code": "runtime:budget:max_turns"},
                {"name": "token_budget", "code": "runtime:budget:max_input_tokens"},
                {"name": "cost_budget", "code": "runtime:budget:max_cost"},
                {"name": "checkpoint_policy", "code": "checkpoint_coordinator"},
                {"name": "progress_policy", "code": "background_progress_observer"},
                {"name": "evaluation_stages", "code": "evaluation_pipeline"},
                {"name": "human_adjudication", "code": "verified_human_adjudication"},
                {"name": "bounded_exploration", "code": "bounded_exploration_terminal"},
                {"name": "subject_disclosure", "code": "evaluation_disclosure:pre_run"},
            ),
        )

    def aggregate_metrics(
        self,
        scope: LabAgentSessionScope,
        *,
        metric: str,
        group_by: str,
        run_ids: Sequence[str],
    ) -> Sequence[Mapping[str, Any]]:
        self.scopes.append(scope)
        return ({"group": "completed", "value": 1.0, "sample_size": len(run_ids)},)


def context() -> LabToolContext:
    return LabToolContext(
        scope=LabAgentSessionScope(workspace_id="workspace-1", project_id="project-1"),
        session_id="session-1",
        turn_sequence=1,
    )


def test_general_chat_offers_exactly_the_two_navigation_tools() -> None:
    catalog = build_catalog(build_read_tools(FakeReadRepository()))

    assert set(offered_tools(catalog, LabAgentSessionForm.GENERAL)) == {
        "list_projects",
        "read_capability_catalog",
    }
    assert len(catalog) == 10


def test_every_schema_is_strict_and_declares_no_scope_argument() -> None:
    tools = build_read_tools(FakeReadRepository())
    forbidden = {"workspace_id", "project_id", "scope", "session_id", "actor", "authority"}

    for tool in tools:
        schema = tool.provider_schema()
        assert schema["additionalProperties"] is False
        assert not (set(schema["properties"]) & forbidden)


@pytest.mark.parametrize(
    ("arguments", "code"),
    [
        ({"run_id": "run-1", "project_id": "project-2"}, "schema.scope_argument_forbidden"),
        ({}, "schema.argument_set_invalid"),
        ({"run_id": 1}, "schema.argument_type_invalid"),
        # Chave desconhecida junto de uma chave válida: o critério de aceitação da issue
        # exige recusa, e a validação é por igualdade exata do conjunto, não por presença
        # dos obrigatórios. Sem este caso, trocar a igualdade por um superset passaria.
        ({"run_id": "run-1", "foo": 1}, "schema.argument_set_invalid"),
    ],
)
def test_exact_argument_validation_refuses_override_missing_and_wrong_type(
    arguments: Mapping[str, Any], code: str
) -> None:
    repository = FakeReadRepository()
    tool = build_catalog(build_read_tools(repository))["read_run"]

    with pytest.raises(LabToolRejected) as rejected:
        tool.execute(arguments, context())

    assert rejected.value.error.code.value == code
    assert repository.scopes == []


def test_tools_pass_only_the_validated_session_scope_to_repository() -> None:
    repository = FakeReadRepository()
    tool = build_catalog(build_read_tools(repository))["read_run"]
    expected = context()

    tool.execute({"run_id": "run-1"}, expected)

    assert repository.scopes == [expected.scope]


def test_capability_catalog_contains_real_active_admission_codes() -> None:
    catalog = AdmissionCapabilityCatalog(
        RuntimeCapabilityEnvelope.declare(runners=())
    ).capability_catalog()
    codes = {str(item["code"]) for item in catalog.active_rejections}

    assert catalog.admitted
    assert {
        "runtime:budget:max_turns",
        "runtime:budget:max_input_tokens",
        "runtime:budget:max_output_tokens",
        "runtime:budget:max_cost",
        "runtime:checkpoint_coordinator",
        "runtime:background_progress_observer",
        "runtime:evaluation_pipeline",
        "runtime:verified_human_adjudication",
        "runtime:bounded_exploration_terminal",
        # O runner ativo só aceita goal_complete e budget_exhausted terminal, então esta
        # rejeição existe de verdade. Ela ficava fora do catálogo porque a derivação não
        # inspecionava check_stop_conditions: omitir rejeição ativa produz um agente que
        # propõe o impossível, que é o dano que o catálogo existe para evitar.
        "runtime:stop_condition_coordinator",
        "evaluation_disclosure:pre_run",
        "evaluation_disclosure:on_request",
        "evaluation_disclosure:post_run",
    } <= codes


def test_requested_and_returned_refs_remain_separate() -> None:
    tool = build_catalog(build_read_tools(FakeReadRepository()))["read_run_events"]

    result = tool.execute(
        {"run_id": "run-1", "after_sequence": 0, "limit": 10}, context()
    )

    assert result.requested_refs == ("run-1",)
    assert result.returned_refs == ("event-1",)


def test_aggregate_metrics_requires_sample_size_and_allowlisted_schema() -> None:
    tool = build_catalog(build_read_tools(FakeReadRepository()))["aggregate_metrics"]

    result = tool.execute(
        {"metric": "run_count", "group_by": "status", "run_ids": ["run-1"]}, context()
    )
    assert result.content["groups"] == (
        {"group": "completed", "value": 1.0, "sample_size": 1},
    )

    with pytest.raises(LabToolRejected) as rejected:
        tool.execute(
            {"metric": "DROP TABLE runs", "group_by": "status", "run_ids": ["run-1"]},
            context(),
        )
    assert rejected.value.error.code == LabAgentErrorCode.SCHEMA_ARGUMENT_TYPE_INVALID


def test_aggregate_metrics_rejects_group_without_sample_size() -> None:
    class BrokenRepository(FakeReadRepository):
        def aggregate_metrics(
            self,
            scope: LabAgentSessionScope,
            *,
            metric: str,
            group_by: str,
            run_ids: Sequence[str],
        ) -> Sequence[Mapping[str, Any]]:
            return ({"group": "completed", "value": 1.0},)

    tool = build_catalog(build_read_tools(BrokenRepository()))["aggregate_metrics"]

    with pytest.raises(ValueError, match="sample_size"):
        tool.execute(
            {"metric": "run_count", "group_by": "status", "run_ids": ["run-1"]},
            context(),
        )


def test_no_read_tool_can_reach_a_write_surface() -> None:
    """O invariante de autoridade, provado pela superfície e não pela intenção.

    As tools só alcançam o mundo pelo `LabReadRepository`. Se todo método da porta é leitura,
    nenhuma tool pode chamar `append_event`, `decide_contract_revision` nem criar
    AdmissionRecord — não por disciplina de quem escreveu a tool, mas porque o verbo não
    existe onde ela pode chegar. Um método de escrita adicionado à porta quebra este teste
    antes de qualquer tool passar a usá-lo.
    """

    forbidden = ("append_event", "decide_contract_revision", "save_admission_record", "admit")
    port_methods = tuple(
        name for name in vars(LabReadRepository) if not name.startswith("_")
    )

    assert port_methods
    assert not [name for name in port_methods if name in forbidden]
    assert all(
        name.startswith(("read_", "list_", "aggregate_")) for name in port_methods
    ), port_methods

    # E o módulo de cada tool não importa nenhuma superfície de escrita por outra via.
    for tool in build_read_tools(FakeReadRepository()):
        module = sys.modules[type(tool).__module__]
        reachable = tuple(vars(module))
        assert not [name for name in reachable if name in forbidden], type(tool).__name__


def test_dispatch_gate_accepts_every_null_the_tool_schema_declares_nullable() -> None:
    """O gate de despacho e a tool precisam concordar sobre o que é argumento válido.

    O gate roda antes da tool e recusa por conta própria. Enquanto ele ignorava
    `nullable`, `status=None` — anunciado como aceitável no schema que o modelo recebe —
    era recusado com `schema.argument_type_invalid`. O modelo obedecia o schema, levava
    recusa, tentava de novo igual, e o turno morria em `repeated_refusal`. Este teste
    varre o catálogo real para que qualquer tool nova com campo anulável fique coberta.
    """

    catalog = build_catalog(build_read_tools(FakeReadRepository()))
    checked: list[tuple[str, str]] = []

    for name, tool in catalog.items():
        schema = tool.provider_schema()
        properties = schema["properties"]
        nullable_fields = [
            field for field, rule in properties.items() if rule.get("nullable") is True
        ]
        if not nullable_fields:
            continue
        arguments = {field: _sample_for(rule) for field, rule in properties.items()}
        for field in nullable_fields:
            candidate = {**arguments, field: None}
            assert validate_schema(schema, candidate, name) is None, (name, field)
            checked.append((name, field))

    assert ("list_runs", "status") in checked, checked


def test_dispatch_gate_still_refuses_null_where_the_schema_forbids_it() -> None:
    """Aceitar `nullable` não pode virar aceitar qualquer null."""

    catalog = build_catalog(build_read_tools(FakeReadRepository()))
    schema = catalog["list_runs"].provider_schema()

    error = validate_schema(schema, {"limit": None, "status": None}, "list_runs")

    assert error is not None
    assert error.code is LabAgentErrorCode.SCHEMA_ARGUMENT_TYPE_INVALID
    assert error.field_path == ("limit",)


def _sample_for(rule: Mapping[str, Any]) -> Any:
    """Valor mínimo que satisfaz a regra, para isolar o campo sob teste."""

    match rule.get("type"):
        case "integer" | "number":
            return rule.get("minimum", 1)
        case "boolean":
            return False
        case "array":
            return []
        case "object":
            return {}
        case _:
            choices = rule.get("enum")
            return choices[0] if choices else "x"
