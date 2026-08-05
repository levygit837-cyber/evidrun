"""A costura entre o laço e as tools: o que o laço exige de qualquer tool.

Este módulo existe para que o laço (issue #131) e as tools (issues #132 e #133) sejam
escritos contra o mesmo contrato sem que um importe o outro. O laço depende de
`LabTool`; cada tool satisfaz o Protocol. Nenhum lado conhece a implementação do outro.

A fronteira é deliberada. O executor da tool é o único ponto que resolve pertencimento,
classificação e budget; a tool declara o que aceita e devolve o que leu. Uma tool que
recebesse `workspace_id` ou `session_id` como argumento ofereceria ao modelo um controle
que o escopo v1 nega, então `execute` recebe o scope pelo contexto e não pelos argumentos.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol, cast, runtime_checkable

from evidrun.contracts.lab_agent.errors import LabAgentError
from evidrun.contracts.lab_agent.scope import LabAgentSessionForm, LabAgentSessionScope

__all__ = [
    "LabTool",
    "LabToolContext",
    "LabToolRejected",
    "LabToolResult",
    "ToolAvailability",
    "declared_argument_keys",
    "required_argument_keys",
]


class LabToolRejected(Exception):
    """Recusa nomeada que o laço devolve ao modelo sem inferir por texto.

    Vive aqui, e não no módulo de uma família de tools, porque é a costura: o laço precisa
    distinguir recusa de falha, e uma exceção declarada duas vezes em dois módulos-folha é
    exatamente por que o laço não conseguia capturá-la.
    """

    def __init__(self, error: LabAgentError) -> None:
        super().__init__(error.message)
        self.error = error


@dataclass(frozen=True, slots=True)
class LabToolContext:
    """O que a tool recebe além dos argumentos validados.

    `scope` vem da sessão já validada, nunca do modelo. `session_id` acompanha para que o
    executor registre o rastro; a tool não o usa para ampliar leitura.
    """

    scope: LabAgentSessionScope
    session_id: str
    turn_sequence: int


@dataclass(frozen=True, slots=True)
class LabToolResult:
    """O que a tool devolve ao laço.

    `requested_refs` e `returned_refs` são separados porque a diferença entre os dois
    conjuntos é a evidência de que o enforcement recusou algo. Um campo único apagaria a
    tentativa, e o humano perderia a capacidade de ver o que o agente tentou ler.
    """

    content: Mapping[str, Any]
    requested_refs: tuple[str, ...] = ()
    returned_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ToolAvailability:
    """Em quais formas de sessão a tool é oferecida.

    General chat recebe exatamente duas tools por decisão do ADR 0021: navegação do
    Workspace não é leitura implícita de todos os Projects.
    """

    forms: frozenset[LabAgentSessionForm] = field(
        default_factory=lambda: frozenset(
            {LabAgentSessionForm.PROJECT, LabAgentSessionForm.FOCUSED}
        )
    )

    def offers(self, form: LabAgentSessionForm) -> bool:
        return form in self.forms


@runtime_checkable
class LabTool(Protocol):
    """Uma tool do catálogo fechado.

    `name` é a identidade no catálogo. `provider_schema` é o schema estrito enviado ao
    provider: `additionalProperties: false`, obrigatórios explícitos e tetos declarados.
    `availability` decide a oferta por forma de sessão, e o laço a consulta na etapa de
    catálogo, antes de qualquer consumo de budget.
    """

    @property
    def name(self) -> str: ...

    @property
    def availability(self) -> ToolAvailability: ...

    def provider_schema(self) -> Mapping[str, Any]: ...

    def execute(
        self, arguments: Mapping[str, Any], context: LabToolContext
    ) -> LabToolResult: ...


def declared_argument_keys(schema: Mapping[str, Any]) -> frozenset[str]:
    """As chaves que o schema declara, para comparação por igualdade exata.

    O catálogo v1 exige igualdade exata do conjunto de chaves, não presença dos
    obrigatórios: chave desconhecida, chave ausente e tipo divergente são recusa, nunca
    coerção. Derivar as chaves do próprio schema evita a segunda lista que divergiria.
    """

    properties = schema.get("properties")
    if not isinstance(properties, Mapping):
        return frozenset()
    keys = cast(Mapping[object, object], properties)
    return frozenset(str(key) for key in keys)


def required_argument_keys(schema: Mapping[str, Any]) -> frozenset[str]:
    required = schema.get("required")
    if not isinstance(required, Sequence) or isinstance(required, str | bytes):
        return frozenset()
    items = cast(Sequence[object], required)
    return frozenset(str(item) for item in items)
