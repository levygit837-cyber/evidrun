"""O que uma sessão, mensagem e rastro do Lab Agent são, fora de como são persistidos.

Separado de `lab.py` porque as duas razões de mudança são distintas: aqui mora a forma que as
bordas leem — a projeção que API e CLI compartilham por exigência do ADR 0025 — e lá mora o
enforcement de pertencimento sobre linhas do banco. Um módulo com as duas coisas obriga quem
lê a projeção a atravessar consultas SQLAlchemy que não a afetam.

Nenhum tipo aqui conhece `Session`, `select` ou linha de tabela.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from evidrun.contracts.lab_agent.scope import LabAgentSessionScope

__all__ = [
    "LabMessage",
    "LabSession",
    "LabToolTrace",
    "LabTurnInstruction",
    "ProjectNavigationItem",
]


@dataclass(frozen=True, slots=True)
class LabSession:
    id: str
    workspace_id: str
    project_id: str | None
    focus_kind: str | None
    focus_id: str | None
    title: str
    created_at: datetime

    def scope_document(self) -> dict[str, str | None]:
        return {
            "workspace_id": self.workspace_id,
            "project_id": self.project_id,
            "focus_kind": self.focus_kind,
            "focus_id": self.focus_id,
        }

    def document(self) -> dict[str, Any]:
        """A projeção única desta sessão, compartilhada por API e CLI.

        Vive no record, e não numa função de projeção por borda, porque o ADR 0025 exige que
        `evidrun chat list` e `GET /lab/sessions` devolvam o mesmo documento. Duas projeções
        divergiriam no primeiro campo novo, e a divergência apareceria como a CLI afirmando
        uma forma de sessão que a API não reconhece.
        """

        return {
            "id": self.id,
            "workspace_id": self.workspace_id,
            "project_id": self.project_id,
            "focus_kind": self.focus_kind,
            "focus_id": self.focus_id,
            "form": self.form,
            "title": self.title,
            "created_at": self.created_at.isoformat(),
        }

    @property
    def form(self) -> str:
        """Derivada pelo contrato, nunca por uma segunda cascata aqui.

        `LabAgentSessionScope.form` já decide a forma a partir de `focus_kind` e `project_id`.
        Repetir a cascata neste record criaria duas regras para o mesmo vocabulário fechado, e
        a primeira divergência apareceria como a CLI e a API classificando a mesma sessão de
        formas diferentes — exatamente o que a projeção única existe para impedir.
        """

        return LabAgentSessionScope.model_validate(self.scope_document()).form.value


@dataclass(frozen=True, slots=True)
class LabMessage:
    id: str
    session_id: str
    role: str
    content: str
    sequence: int
    created_at: datetime


@dataclass(frozen=True, slots=True)
class LabTurnInstruction:
    """Identifica a instrução enviada em um turno sem inventar uma mensagem ou uma tool.

    O digest pertence ao turno: terminais incompletos não têm fala do agente, e registrar uma
    linha sintética no rastro de tool declararia uma execução que nunca aconteceu. Mantê-lo
    separado preserva esses dois fatos e permite que uma correção seja outro registro append-only.
    """

    id: str
    session_id: str
    turn_sequence: int
    instruction_digest: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class LabToolTrace:
    id: str
    session_id: str
    turn_sequence: int
    tool_name: str
    arguments_digest: str
    requested_refs: tuple[Any, ...]
    returned_refs: tuple[Any, ...]
    outcome: str
    refusal_code: str | None
    scope_snapshot: dict[str, str | None]
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ProjectNavigationItem:
    id: str
    name: str
    created_at: datetime
