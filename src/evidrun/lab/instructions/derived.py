"""O bloco de capabilities, derivado do runtime e nunca redigido à mão.

Derivação é a invariante, não uma conveniência. Uma lista autorada de tools, tetos ou rejeições
envelhece no primeiro patch que mude um check, e a divergência ensina o modelo a pedir o que não
existe — com aparência competente, até o humano descobrir no compile.

Cinco partes, todas com fonte executável:

| Parte | Fonte |
| --- | --- |
| tools oferecidas | catálogo efetivo da sessão (`offered_tools`) |
| contract_types aceitos | `REVISION_MODELS` do parser canônico |
| tetos do turno | o `LabAgentTurnLimits` do próprio envelope |
| capabilities admitidas | `CapabilityCatalog.admitted` |
| rejeições ativas | `CapabilityCatalog.active_rejections` |

As duas últimas vêm do mesmo catálogo que as tools de leitura devolvem, então prompt e
enforcement não podem divergir: é literalmente o mesmo objeto.
"""

from __future__ import annotations

import json
from collections.abc import Mapping

from evidrun.contracts.authoring.parse import REVISION_MODELS
from evidrun.lab.protocol import LabTool
from evidrun.lab.tools.registry import CapabilityCatalog

__all__ = ["render_derived_block"]


def render_derived_block(
    *,
    offered: Mapping[str, LabTool],
    catalog: CapabilityCatalog,
    limits: object,
) -> str:
    """Compõe o bloco a partir das cinco fontes executáveis.

    `limits` é lido por atributo em vez de tipado como `LabAgentTurnLimits` para manter este
    módulo fora da dependência de contrato do envelope: ele só precisa dos cinco tetos, e é o
    laço que decide qual documento os declara.
    """

    return "\n\n".join(
        (
            "## Capabilities desta sessão",
            _tools(offered),
            _contract_types(),
            _limits(limits),
            _admitted(catalog),
            _rejections(catalog),
        )
    )


def _tools(offered: Mapping[str, LabTool]) -> str:
    """As tools oferecidas, com o schema exato que o provider vai receber.

    O schema entra junto porque a etapa de schema compara chaves por igualdade exata: anunciar
    o nome sem as chaves faria o modelo adivinhar argumentos e gastar recusa por chamada.
    """

    lines = [
        f"Tools oferecidas nesta sessão ({len(offered)}). "
        "Envie exatamente as chaves de `required`, nenhuma além:"
    ]
    for name, tool in offered.items():
        schema = tool.provider_schema()
        required = ", ".join(str(item) for item in schema.get("required", ()))
        lines.append(f"- {name}({required or 'sem argumentos'})")
        lines.append(f"  schema: {json.dumps(schema, ensure_ascii=False, sort_keys=True)}")
    return "\n".join(lines)


def _contract_types() -> str:
    """Os contract_type que o parser canônico aceita, em ordem estável.

    Derivado de `REVISION_MODELS` porque o mapa é a fonte que `validate_draft` consulta. Uma
    lista escrita à mão perderia o próximo tipo registrado, e o modelo proporia um tipo que a
    validação recusa como inexistente.
    """

    names = ", ".join(sorted(item.value for item in REVISION_MODELS))
    return f"Os contract_type que existem: {names}."


def _limits(limits: object) -> str:
    """Os cinco tetos do turno, lidos do documento que o runtime verifica."""

    fields = (
        ("max_tool_calls_per_turn", "tool calls"),
        ("max_provider_round_trips_per_turn", "idas ao provider"),
        ("max_wall_seconds_per_turn", "segundos"),
        ("max_refusals_per_turn", "recusas"),
        ("max_output_tokens_per_round_trip", "tokens de saída por ida ao provider"),
    )
    declared: list[str] = []
    for attribute, label in fields:
        value = getattr(limits, attribute, None)
        if value is None:
            # Teto ausente não é teto zero. Inventar um valor anunciaria limite que o runtime
            # não verifica, que é exatamente a promessa falsa que o loop-v1 proíbe.
            raise ValueError(f"turn limits without {attribute}")
        declared.append(f"{value} {label}")
    return (
        "Tetos deste turno: "
        + "; ".join(declared)
        + ". Recusa tem teto próprio porque chamada recusada não executou. Esgotar o teto de tool "
        "calls, de idas ao provider, de tempo ou de recusas encerra o turno com o que foi feito "
        "até ali. O teto de tokens de saída é do transporte: ele trunca a resposta daquela ida ao "
        "provider, sem encerrar o turno."
    )


def _admitted(catalog: CapabilityCatalog) -> str:
    """O que um experimento pode declarar hoje, para a proposta não nascer inadmissível."""

    if not catalog.admitted:
        return "Capabilities admitidas: nenhuma foi declarada por este runtime."
    entries = "\n".join(f"- {_entry(item)}" for item in catalog.admitted)
    return f"Capabilities admitidas ({len(catalog.admitted)}):\n{entries}"


def _rejections(catalog: CapabilityCatalog) -> str:
    """O que a admissão recusa hoje, com os códigos reais.

    Esta é a parte que evita a falha mais custosa. Sem ela o agente propõe experimentos
    impossíveis com aparência competente, e o humano só descobre no compile.
    """

    if not catalog.active_rejections:
        return "Rejeições ativas: nenhuma; este runtime admite tudo que sabe representar."
    entries = "\n".join(f"- {_entry(item)}" for item in catalog.active_rejections)
    return (
        f"Rejeições ativas da admissão ({len(catalog.active_rejections)}). "
        "Um experimento que declare qualquer uma destas é recusado na admissão, "
        f"então não as proponha:\n{entries}"
    )


def _entry(item: Mapping[str, object]) -> str:
    """Uma entrada do catálogo em texto estável, sem inventar campo ausente."""

    return ", ".join(f"{key}={item[key]}" for key in sorted(item))
