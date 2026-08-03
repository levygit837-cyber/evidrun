"""A porta de leitura das tools: a recusa nomeada e o Protocol que as tools consomem.

Separado do adapter de propósito. As nove tools de leitura e a validação de schema em
`_base.py` dependem apenas deste módulo, que não importa SQLAlchemy. Mantê-lo junto do
adapter arrastava o ORM para o caminho de validação de argumentos, onde nenhuma sessão de
banco é aberta — e fazia o módulo do adapter mudar por três razões diferentes.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, NoReturn, Protocol

from evidrun.contracts.lab_agent.errors import (
    LabAgentError,
    LabAgentErrorCode,
    LabAgentStage,
    LabAgentTargetSituation,
    target_not_visible,
)
from evidrun.contracts.lab_agent.scope import LabAgentSessionScope
from evidrun.lab.tools.registry import CapabilityCatalog

#: Projeção pública do catálogo v1: o que a tool devolve ao modelo, nunca a linha do banco.
Readable = Mapping[str, Any]

#: As duas classificações que o runtime ativo recusa. Uma tupla, não três literais soltos:
#: o conjunto era repetido em três callsites, e o quarto esqueceria um dos valores.
CLASSIFIED = frozenset({"sensitive", "restricted"})

__all__ = [
    "CLASSIFIED",
    "LabReadRepository",
    "LabToolRejected",
    "Readable",
    "is_classified",
    "reject_classification",
    "reject_project_required",
    "reject_target",
]


class LabToolRejected(Exception):
    """Recusa nomeada que o laço pode devolver ao modelo sem inferir por texto."""

    def __init__(self, error: LabAgentError) -> None:
        self.error = error
        super().__init__(error.code.value)


def is_classified(classification: object) -> bool:
    """Se o runtime ativo recusa este conteúdo.

    Aceita `object` porque dois dos três callsites leem uma coluna tipada e o terceiro varre
    um documento arbitrário, onde a chave `classification` pode carregar qualquer valor.
    Estreitar para `str | None` obrigaria o scanner a um cast que não prova nada: a pergunta
    real é de pertencimento ao conjunto, e um valor de outro tipo simplesmente não pertence.

    `None` não é classificado: ausência de classificação é o caso comum das linhas antigas,
    e tratá-la como restrita recusaria leitura que o contrato permite.
    """

    return classification in CLASSIFIED


def reject_target(situation: LabAgentTargetSituation, field: str) -> NoReturn:
    """Recusa alvo não visível. `NoReturn` é o contrato, não decoração.

    Sem ele, cada callsite depois de um `row is None` precisava de um `assert row is not None`
    só para o type checker aceitar o caminho — cinco asserts que afirmavam ao leitor uma
    dúvida que não existe. A anotação move a garantia para um lugar só.
    """

    raise LabToolRejected(target_not_visible(situation, field_path=(field,)))


def reject_classification(field: str) -> NoReturn:
    """Recusa conteúdo classificado sem dizer o que o conteúdo é."""

    raise LabToolRejected(
        LabAgentError(
            stage=LabAgentStage.CLASSIFICATION,
            code=LabAgentErrorCode.CLASSIFICATION_GRANT_REQUIRED,
            message="O conteúdo solicitado exige um grant de classificação.",
            remediation="Use apenas conteúdo internal/public nesta sessão.",
            field_path=(field,),
        )
    )


def reject_project_required() -> NoReturn:
    """Recusa leitura que exige Project quando a sessão é General.

    Distinta de `reject_target`: aqui nada foi pedido que possa não existir. A sessão é que
    não tem Project, e dizer isso não revela nada sobre alvo algum — por isso esta é a única
    recusa de scope que pode ser explícita. Sem `field_path`: nenhum argumento está errado.
    """

    raise LabToolRejected(
        LabAgentError(
            stage=LabAgentStage.SCOPE,
            code=LabAgentErrorCode.SCOPE_PROJECT_REQUIRED,
            message="Esta leitura exige uma sessão de Project.",
            remediation="Peça ao humano para abrir uma Project chat.",
        )
    )


class LabReadRepository(Protocol):
    def list_projects(self, scope: LabAgentSessionScope) -> Sequence[Readable]: ...
    def read_contract_revision(
        self, scope: LabAgentSessionScope, revision_ref: str
    ) -> Readable: ...
    def list_runs(
        self, scope: LabAgentSessionScope, *, limit: int, status: str | None
    ) -> Sequence[Readable]: ...
    def read_run(self, scope: LabAgentSessionScope, run_id: str) -> Readable: ...
    def read_run_events(
        self, scope: LabAgentSessionScope, run_id: str, *, after_sequence: int, limit: int
    ) -> Sequence[Readable]: ...
    def read_evaluation_records(
        self, scope: LabAgentSessionScope, run_id: str
    ) -> Sequence[Readable]: ...
    def read_comparison(self, scope: LabAgentSessionScope, comparison_id: str) -> Readable: ...
    def read_admission(self, scope: LabAgentSessionScope, admission_id: str) -> Readable: ...
    def read_capability_catalog(self) -> CapabilityCatalog: ...
    def aggregate_metrics(
        self,
        scope: LabAgentSessionScope,
        *,
        metric: str,
        group_by: str,
        run_ids: Sequence[str],
    ) -> Sequence[Readable]: ...
