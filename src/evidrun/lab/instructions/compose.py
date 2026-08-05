"""A composição: exatamente uma base, um bloco de escopo e um bloco de capabilities.

O documento final é a concatenação ordenada das três camadas. A ordem é normativa e a
verificação de não-contradição roda na composição, não numa revisão de texto: uma frase de bloco
de escopo que conceda autoridade passaria despercebida na leitura corrida e só apareceria como
comportamento errado em produção.

O digest identifica o documento exato. Mesmo scope e mesmo catálogo produzem o mesmo digest;
trocar de Project produz outro documento e outro digest, porque o bloco derivado carrega o
catálogo efetivo daquela sessão.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from evidrun.contracts.lab_agent.scope import LabAgentSessionForm
from evidrun.lab.instructions.base import FORBIDDEN_VERBS, render_base
from evidrun.lab.instructions.derived import render_derived_block
from evidrun.lab.instructions.scope_blocks import render_scope_block
from evidrun.lab.protocol import LabTool
from evidrun.lab.tools.registry import CapabilityCatalog
from evidrun.shared.types import sha256_json

__all__ = ["ComposedInstruction", "compose_instruction"]

#: Um bloco de escopo que use um verbo de autoridade em construção afirmativa está concedendo.
#: A negação explícita é permitida — os blocos precisam poder dizer "não decide" — então o
#: padrão exige o verbo sem uma negação imediatamente antes.
_NEGATIONS = ("não", "nunca", "jamais", "nenhum", "nenhuma", "sem")


@dataclass(frozen=True, slots=True)
class ComposedInstruction:
    """O documento composto e sua identidade.

    `text` é o que vai ao provider. `digest` identifica o documento exato para o registro por
    turno. As duas coisas juntas num único objeto impedem que alguém registre o digest de um
    documento e envie outro.
    """

    text: str
    form: LabAgentSessionForm
    digest: str


def compose_instruction(
    *,
    form: LabAgentSessionForm,
    offered: Mapping[str, LabTool],
    catalog: CapabilityCatalog,
    limits: object,
) -> ComposedInstruction:
    """Monta a instrução das três camadas e recusa composição que se contradiga."""

    base = render_base()
    scope = render_scope_block(form)
    derived = render_derived_block(offered=offered, catalog=catalog, limits=limits)
    _reject_authority_grant(scope)
    _reject_unoffered_tool(scope, offered)
    text = "\n\n".join((base, scope, derived))
    return ComposedInstruction(
        text=text,
        form=form,
        digest=sha256_json({"form": form.value, "text": text}),
    )


def _reject_authority_grant(scope_block: str) -> None:
    """Recusa bloco de escopo que conceda o que a base proíbe.

    Estreitar é permitido; conceder não. O teste procura verbo de autoridade sem negação
    imediatamente antes, porque um bloco precisa poder dizer "não decide" e não pode dizer
    "decide". Heurística de texto é grosseira de propósito: ela não substitui o enforcement,
    que continua no executor de tool, e existe para pegar a redação que ninguém revisou.
    """

    for verb in FORBIDDEN_VERBS:
        for match in re.finditer(rf"\b{verb}\w*", scope_block.lower()):
            prefix = scope_block.lower()[max(0, match.start() - 40) : match.start()]
            if not any(negation in prefix for negation in _NEGATIONS):
                raise ValueError(
                    "scope block grants authority the base forbids: "
                    f"{scope_block[max(0, match.start() - 40) : match.end()].strip()!r}"
                )


def _reject_unoffered_tool(scope_block: str, offered: Mapping[str, LabTool]) -> None:
    """Recusa bloco que nomeie tool ausente do catálogo efetivo.

    Anunciar tool que a sessão não oferece produz exatamente o laço que o catálogo existe para
    evitar: o modelo chama, recebe `catalog.tool_not_offered` e tenta variações. General chat é
    o caso real, porque a base fala do pedido de aprovação sem nomear a tool.
    """

    named = set(re.findall(r"\b(?:list|read|aggregate|validate|propose|request)_\w+", scope_block))
    unknown = tuple(sorted(name for name in named if name not in offered))
    if unknown:
        raise ValueError(
            "scope block names tools outside the effective catalog: " + ", ".join(unknown)
        )
