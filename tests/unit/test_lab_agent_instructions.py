"""As provas mínimas do contrato `lab-agent-instructions-v1`.

Cada teste defende uma propriedade que, quebrada, muda o comportamento do modelo em produção:
prompt divergente do enforcement, bloco de escopo concedendo o que a base nega, ou instrução
anunciando tool e capability que não existem.
"""

from __future__ import annotations

import inspect
from collections.abc import Mapping
from typing import Any

import pytest

from evidrun.contracts.authoring.parse import REVISION_MODELS
from evidrun.contracts.lab_agent.envelope import LabAgentTurnLimits
from evidrun.contracts.lab_agent.scope import LabAgentSessionForm
from evidrun.lab.instructions import base as base_module
from evidrun.lab.instructions import scope_blocks as scope_module
from evidrun.lab.instructions.base import SECTION_ORDER, render_base
from evidrun.lab.instructions.compose import compose_instruction
from evidrun.lab.protocol import LabToolContext, LabToolResult, ToolAvailability
from evidrun.lab.tools import build_catalog, offered_tools
from evidrun.lab.tools.registry import CapabilityCatalog

LIMITS = LabAgentTurnLimits(
    max_tool_calls_per_turn=12,
    max_provider_round_trips_per_turn=8,
    max_wall_seconds_per_turn=120,
    max_refusals_per_turn=4,
    max_output_tokens_per_round_trip=2_048,
)

CATALOG = CapabilityCatalog(
    admitted=({"kind": "interaction_mode", "name": "single_turn"},),
    active_rejections=(
        {"name": "max_turns", "code": "runtime:budget:max_turns"},
        {"name": "subject_disclosure", "code": "evaluation_disclosure:pre_run"},
    ),
)


class _StubTool:
    """Tool mínima que satisfaz o Protocol, para compor sem tocar banco nem provider."""

    def __init__(self, name: str, *, forms: frozenset[LabAgentSessionForm] | None = None) -> None:
        self._name = name
        self._forms = forms or frozenset(
            {LabAgentSessionForm.PROJECT, LabAgentSessionForm.FOCUSED}
        )

    @property
    def name(self) -> str:
        return self._name

    @property
    def availability(self) -> ToolAvailability:
        return ToolAvailability(forms=self._forms)

    def provider_schema(self) -> Mapping[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {"run_id": {"type": "string"}},
            "required": ["run_id"],
        }

    def execute(self, arguments: Mapping[str, Any], context: LabToolContext) -> LabToolResult:
        del arguments, context
        return LabToolResult(content={})


def _catalog() -> Mapping[str, Any]:
    return build_catalog(
        (
            _StubTool("list_projects", forms=frozenset(LabAgentSessionForm)),
            _StubTool("read_capability_catalog", forms=frozenset(LabAgentSessionForm)),
            _StubTool("read_run"),
            _StubTool("request_human_approval"),
        )
    )


def _compose(form: LabAgentSessionForm):
    catalog = _catalog()
    return compose_instruction(
        form=form,
        offered=offered_tools(catalog, form),
        catalog=CATALOG,
        limits=LIMITS,
    )


@pytest.mark.parametrize("form", list(LabAgentSessionForm))
def test_composicao_tem_exatamente_uma_camada_de_cada(form: LabAgentSessionForm) -> None:
    """Uma base, um bloco de escopo, um bloco de capabilities.

    Duas camadas do mesmo tipo produziriam instrução que se contradiz sem que nenhuma linha
    isolada esteja errada, e o modelo seguiria a última que leu.
    """

    text = _compose(form).text

    assert text.count("## Escopo desta sessão") == 1
    assert text.count("## Capabilities desta sessão") == 1
    assert text.count("## Identidade") == 1
    # A base precede o escopo, que precede as capabilities derivadas.
    assert text.index("## Identidade") < text.index("## Escopo desta sessão")
    assert text.index("## Escopo desta sessão") < text.index("## Capabilities desta sessão")


def test_as_seis_secoes_aparecem_na_ordem_normativa() -> None:
    """Identidade e fronteira precedem qualquer regra operacional.

    Um modelo que leia as regras de tool antes do limite de autoridade aprende a mecânica antes
    do limite.
    """

    text = render_base()
    positions = [text.index(f"## {name}") for name in SECTION_ORDER]

    assert positions == sorted(positions)
    assert list(SECTION_ORDER) == [
        "Identidade",
        "Fronteira de autoridade",
        "Vocabulário",
        "Regras de tool call",
        "Regras de evidência",
        "Forma de resposta",
    ]


def test_secao_sem_conteudo_falha_alto(monkeypatch: pytest.MonkeyPatch) -> None:
    """Seção vazia é defeito de programação, não configuração.

    Renderizar sem ela entregaria instrução sem uma fronteira que o contrato exige, e nada no
    documento indicaria a ausência.
    """

    monkeypatch.setitem(base_module.BASE_SECTIONS, "Fronteira de autoridade", "   ")

    with pytest.raises(ValueError, match="Fronteira de autoridade"):
        render_base()


def test_bloco_de_escopo_que_concede_autoridade_e_recusado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bloco de escopo apenas estreita.

    A redação que concede passaria por revisão de texto corrido; a composição a recusa porque
    compara o bloco com os verbos de autoridade que a base proíbe.
    """

    monkeypatch.setitem(
        scope_module.SCOPE_BLOCKS,
        LabAgentSessionForm.PROJECT,
        "Nesta sessão você pode aceitar a revision quando o humano estiver ausente.",
    )

    with pytest.raises(ValueError, match="grants authority"):
        _compose(LabAgentSessionForm.PROJECT)


def test_negacao_explicita_continua_permitida(monkeypatch: pytest.MonkeyPatch) -> None:
    """A checagem não pode proibir o bloco de repetir a proibição.

    Sem esta prova, o guarda contra concessão viraria um guarda contra mencionar autoridade, e
    os blocos perderiam a capacidade de reforçar o limite.
    """

    monkeypatch.setitem(
        scope_module.SCOPE_BLOCKS,
        LabAgentSessionForm.PROJECT,
        "Você nunca decide nesta sessão e não aceita revision alguma.",
    )

    assert "nunca decide" in _compose(LabAgentSessionForm.PROJECT).text


def test_general_chat_nao_anuncia_tool_fora_do_catalogo_efetivo() -> None:
    """General chat oferece duas tools, e a instrução não pode citar uma terceira.

    Anunciar tool ausente produz o laço que o catálogo existe para evitar: o modelo chama,
    recebe `catalog.tool_not_offered` e tenta variações até esgotar o teto de recusas.
    """

    general = _compose(LabAgentSessionForm.GENERAL)
    scope_block = general.text[
        general.text.index("## Escopo desta sessão") : general.text.index(
            "## Capabilities desta sessão"
        )
    ]

    assert "request_human_approval" not in scope_block
    assert "read_run" not in scope_block
    # Project chat nomeia a tool porque ali ela existe: a base fala do princípio, o bloco nomeia.
    project = _compose(LabAgentSessionForm.PROJECT)
    assert "request_human_approval" in project.text


def test_bloco_de_escopo_com_tool_inexistente_e_recusado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(
        scope_module.SCOPE_BLOCKS,
        LabAgentSessionForm.GENERAL,
        "Use read_run para inspecionar qualquer Run do Workspace.",
    )

    with pytest.raises(ValueError, match="outside the effective catalog"):
        _compose(LabAgentSessionForm.GENERAL)


@pytest.mark.parametrize("form", list(LabAgentSessionForm))
def test_bloco_derivado_lista_exatamente_o_catalogo_efetivo(
    form: LabAgentSessionForm,
) -> None:
    """Prompt e executor não podem divergir sobre quais tools existem.

    A lista sai de `offered_tools`, a mesma função que o laço consulta na etapa de catálogo.
    """

    catalog = _catalog()
    effective = offered_tools(catalog, form)
    text = _compose(form).text
    derived = text[text.index("## Capabilities desta sessão") :]

    for name in effective:
        assert name in derived
    for name in set(catalog) - set(effective):
        assert name not in derived
    assert f"Tools oferecidas nesta sessão ({len(effective)})" in derived


def test_bloco_derivado_inclui_rejeicoes_ativas_com_codigos_reais() -> None:
    """Sem as rejeições, o agente propõe o impossível com aparência competente.

    O humano só descobriria no compile, depois de investir o tempo de revisar a proposta.
    """

    derived = _compose(LabAgentSessionForm.PROJECT).text

    assert "runtime:budget:max_turns" in derived
    assert "evaluation_disclosure:pre_run" in derived
    assert "Rejeições ativas da admissão (2)" in derived


def test_bloco_derivado_lista_os_contract_types_do_parser() -> None:
    """A lista de tipos é derivada porque envelheceria no próximo tipo registrado."""

    derived = _compose(LabAgentSessionForm.PROJECT).text

    for contract_type in REVISION_MODELS:
        assert contract_type.value in derived
    # Os dois nomes que o ADR 0018 promete e o parser não aceita ficam fora (issue #149).
    assert "comparison_plan" not in derived


def test_teto_ausente_falha_em_vez_de_anunciar_valor_inventado() -> None:
    """Teto anunciado que o runtime não verifica é promessa falsa.

    O contrato do laço exige que todo budget seja aplicado antes de ser anunciado, então um
    documento de limites incompleto precisa falhar em vez de completar com zero.
    """

    class _Partial:
        max_tool_calls_per_turn = 12
        max_provider_round_trips_per_turn = 8
        max_wall_seconds_per_turn = 120
        max_refusals_per_turn = 4

    catalog = _catalog()
    with pytest.raises(ValueError, match="max_output_tokens_per_round_trip"):
        compose_instruction(
            form=LabAgentSessionForm.PROJECT,
            offered=offered_tools(catalog, LabAgentSessionForm.PROJECT),
            catalog=CATALOG,
            limits=_Partial(),
        )


def test_digest_e_estavel_para_mesmo_scope_e_muda_por_forma() -> None:
    """O digest identifica o documento exato, para o registro por turno ser verificável."""

    first = _compose(LabAgentSessionForm.PROJECT)
    second = _compose(LabAgentSessionForm.PROJECT)
    general = _compose(LabAgentSessionForm.GENERAL)

    assert first.digest == second.digest
    assert first.digest != general.digest
    assert first.form is LabAgentSessionForm.PROJECT


def test_digest_muda_quando_o_catalogo_efetivo_muda() -> None:
    """Duas sessões com catálogos diferentes não podem compartilhar digest.

    O digest existe para dizer qual documento o modelo recebeu; colidir entre catálogos
    diferentes o tornaria inútil como identidade.
    """

    catalog = _catalog()
    offered = offered_tools(catalog, LabAgentSessionForm.PROJECT)
    narrowed = {name: tool for name, tool in offered.items() if name != "read_run"}

    full = compose_instruction(
        form=LabAgentSessionForm.PROJECT, offered=offered, catalog=CATALOG, limits=LIMITS
    )
    less = compose_instruction(
        form=LabAgentSessionForm.PROJECT, offered=narrowed, catalog=CATALOG, limits=LIMITS
    )

    assert full.digest != less.digest


def test_instrucao_composta_nao_carrega_credencial_nem_conteudo_de_sessao() -> None:
    """A instrução é função de forma, catálogo e tetos — nunca de conteúdo da conversa.

    Provar ausência de string secreta seria tautológico: nada no texto autorado tem segredo, e
    o teste passaria mesmo se a composição começasse a ler mensagens. A propriedade real é que
    `compose_instruction` não recebe transcript, documento nem scope com ids: se o digest de
    duas sessões com o mesmo scope e catálogo é idêntico, nenhum conteúdo de sessão entrou.
    """

    catalog = _catalog()
    offered = offered_tools(catalog, LabAgentSessionForm.PROJECT)
    parameters = set(inspect.signature(compose_instruction).parameters)

    # A superfície é a prova estrutural: sem esses nomes, conteúdo de sessão não tem por onde
    # entrar, e um campo novo que os introduza quebra este teste antes de chegar ao provider.
    assert parameters == {"form", "offered", "catalog", "limits"}
    assert not parameters & {"history", "transcript", "document", "session_id", "workspace_id"}

    first = compose_instruction(
        form=LabAgentSessionForm.PROJECT, offered=offered, catalog=CATALOG, limits=LIMITS
    )
    second = compose_instruction(
        form=LabAgentSessionForm.PROJECT, offered=offered, catalog=CATALOG, limits=LIMITS
    )
    assert first.digest == second.digest

    for form in LabAgentSessionForm:
        text = _compose(form).text.lower()
        for forbidden in ("api_key", "api key", "authorization:", "bearer ", "sk-"):
            assert forbidden not in text
