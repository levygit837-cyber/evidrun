"""LabAgentSessionScope: as três formas válidas de sessão do Lab Agent.

Pertencimento entre entidades é validado no repository, que conhece as linhas. Aqui vale
apenas a coerência estrutural do documento: qual combinação de campos pode existir.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import computed_field, model_validator

from evidrun.contracts.base import ContractModel, NonEmptyStr


class LabAgentFocusKind(StrEnum):
    """As entidades que podem estreitar uma sessão. Vocabulário fechado do escopo v1."""

    STUDY = "study"
    RUN = "run"
    COMPARISON = "comparison"


class LabAgentSessionForm(StrEnum):
    """A forma derivada da sessão. Deriva do scope; nunca é declarada em paralelo a ele."""

    GENERAL = "general"
    PROJECT = "project"
    FOCUSED = "focused"


class LabAgentSessionScope(ContractModel):
    """O scope imutável de uma sessão do Lab Agent.

    O modelo é uma allowlist fechada de quatro campos: `extra="forbid"` recusa tanto um
    segundo foco (`focus_kind`/`focus_id` são slots únicos) quanto o par genérico
    `scope_type`/`scope_id` da persistência atual, que não é o contrato final.
    """

    workspace_id: NonEmptyStr
    project_id: NonEmptyStr | None = None
    focus_kind: LabAgentFocusKind | None = None
    focus_id: NonEmptyStr | None = None

    @model_validator(mode="after")
    def validate_session_form(self) -> LabAgentSessionScope:
        if (self.focus_kind is None) != (self.focus_id is None):
            raise ValueError("focus requires focus_kind and focus_id together")
        if self.focus_kind is not None and self.project_id is None:
            raise ValueError("focus requires project_id")
        return self

    @computed_field
    @property
    def form(self) -> LabAgentSessionForm:
        if self.focus_kind is not None:
            return LabAgentSessionForm.FOCUSED
        if self.project_id is not None:
            return LabAgentSessionForm.PROJECT
        return LabAgentSessionForm.GENERAL
