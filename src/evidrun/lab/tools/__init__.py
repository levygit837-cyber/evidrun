"""O catálogo fechado de tools do Lab Agent, uma tool por módulo.

O catálogo é fechado e derivado: uma tool ausente da tabela do contrato não é oferecida ao
modelo, e o conjunto oferecido é função da forma de sessão, não de configuração por
chamada.

`build_catalog` é a única fonte do conjunto efetivo. O laço a consulta e nunca monta a
lista por conta própria: duas listas divergiriam no primeiro patch, e a divergência
apareceria como tool oferecida ao modelo que o enforcement recusa.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from evidrun.contracts.lab_agent.scope import LabAgentSessionForm
from evidrun.lab.protocol import LabTool

__all__ = ["build_catalog", "offered_tools"]


def build_catalog(tools: Sequence[LabTool]) -> Mapping[str, LabTool]:
    """Indexa as tools por nome, recusando nome duplicado.

    Nome duplicado é erro de programação, não configuração: duas tools com o mesmo nome
    tornariam indeterminado qual o modelo invocou.
    """

    catalog: dict[str, LabTool] = {}
    for tool in tools:
        if tool.name in catalog:
            raise ValueError(f"tool name declared twice in the catalog: {tool.name}")
        catalog[tool.name] = tool
    return catalog


def offered_tools(
    catalog: Mapping[str, LabTool], form: LabAgentSessionForm
) -> Mapping[str, LabTool]:
    """O catálogo efetivo daquela forma de sessão, em ordem estável por nome."""

    return {
        name: tool for name, tool in sorted(catalog.items()) if tool.availability.offers(form)
    }
