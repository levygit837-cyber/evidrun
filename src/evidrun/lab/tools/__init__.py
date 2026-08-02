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
from evidrun.lab.tools.aggregate_metrics import AggregateMetricsTool
from evidrun.lab.tools.list_projects import ListProjectsTool
from evidrun.lab.tools.list_runs import ListRunsTool
from evidrun.lab.tools.read_admission import ReadAdmissionTool
from evidrun.lab.tools.read_capability_catalog import ReadCapabilityCatalogTool
from evidrun.lab.tools.read_comparison import ReadComparisonTool
from evidrun.lab.tools.read_contract_revision import ReadContractRevisionTool
from evidrun.lab.tools.read_evaluation_records import ReadEvaluationRecordsTool
from evidrun.lab.tools.read_repository import LabReadRepository
from evidrun.lab.tools.read_run import ReadRunTool
from evidrun.lab.tools.read_run_events import ReadRunEventsTool

__all__ = ["build_catalog", "build_read_tools", "offered_tools"]


def build_read_tools(repository: LabReadRepository) -> tuple[LabTool, ...]:
    """Monta somente as dez tools de leitura, sem redecidir o catálogo compartilhado."""

    return (
        ListProjectsTool(repository),
        ReadContractRevisionTool(repository),
        ListRunsTool(repository),
        ReadRunTool(repository),
        ReadRunEventsTool(repository),
        ReadEvaluationRecordsTool(repository),
        ReadComparisonTool(repository),
        ReadAdmissionTool(repository),
        ReadCapabilityCatalogTool(repository),
        AggregateMetricsTool(repository),
    )


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
