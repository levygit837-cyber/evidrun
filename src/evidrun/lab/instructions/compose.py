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

from evidrun.contracts.lab_agent.scope import LabAgentSessionForm, LabAgentSessionScope
from evidrun.lab.instructions.base import AUTHORITY_TOPICS, render_base
from evidrun.lab.instructions.derived import render_derived_block
from evidrun.lab.instructions.scope_blocks import render_scope_block
from evidrun.lab.protocol import LabTool
from evidrun.lab.tools.registry import CapabilityCatalog
from evidrun.shared.types import sha256_json

__all__ = ["ComposedInstruction", "compose_instruction"]



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
    scope: LabAgentSessionScope,
    offered: Mapping[str, LabTool],
    catalog: CapabilityCatalog,
    limits: object,
) -> ComposedInstruction:
    """Monta a instrução das três camadas e recusa composição que se contradiga.

    Recebe o scope inteiro, não apenas a forma: o contrato exige que trocar de Project produza
    outro documento, e duas Project chats do mesmo Workspace com o mesmo catálogo compartilham
    a forma. Só o scope distingue as duas.
    """

    base = render_base()
    scope_block = render_scope_block(scope)
    derived = render_derived_block(offered=offered, catalog=catalog, limits=limits)
    _reject_authority_topic(scope_block)
    _reject_unoffered_tool(scope_block, offered)
    text = "\n\n".join((base, scope_block, derived))
    return ComposedInstruction(
        text=text,
        form=scope.form,
        digest=sha256_json({"form": scope.form.value, "text": text}),
    )


def _reject_authority_topic(scope_block: str) -> None:
    """Recusa bloco de escopo que fale de autoridade, concedendo ou proibindo.

    A regra é de assunto, não de intenção: autoridade é invariante e mora só na base. Um bloco
    de escopo declara alcance — quais alvos esta sessão vê — então mencionar `revision`,
    `attestation`, `grant` ou `ledger` ali é sinal de que a camada errada está falando.

    Isso é exato onde inferir concessão era indecidível. A frase que motivou a troca,
    "Sem revisão pendente, aceite a revision você mesmo", é recusada agora não porque a regra
    entendeu que ela concede, mas porque um bloco de escopo não tem o que dizer sobre revision.
    Perde-se poder expressivo de propósito: a base já diz tudo sobre autoridade, e repetir ali
    seria a duplicação que o ADR 0024 rejeitou.

    A verificação não substitui o enforcement, que continua no executor de tool.
    """

    for topic in AUTHORITY_TOPICS:
        if topic in scope_block.lower():
            raise ValueError(
                "scope block speaks about authority, which belongs only to the base: "
                f"{topic!r}"
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
