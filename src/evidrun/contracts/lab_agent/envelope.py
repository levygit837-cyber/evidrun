"""LabAgentEnvelope: a allowlist fechada do que uma sessão do Lab Agent recebe.

Ele não contém credenciais, bytes de Artifact por consequência de uma ref, conteúdo de
outro Project, chat de outra sessão, nem qualquer authority adicional. Campo novo de
sessão, contract, artifact ou capability não entra aqui automaticamente.

Refs de memória recuperada ficam de fora: a capability de memória não existe, e declarar
o campo anunciaria retrieval que nenhum runtime executa. O contrato v2 já reserva o lugar.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import Field, computed_field, model_validator

from evidrun.contracts.base import (
    ArtifactRef,
    ContractModel,
    ContractRef,
    EvidenceRef,
    NonEmptyStr,
    semantic_model_dump,
)
from evidrun.contracts.lab_agent.scope import LabAgentSessionForm, LabAgentSessionScope
from evidrun.shared.types import sha256_json


class LabAgentMessageRole(StrEnum):
    """Quem produziu a mensagem. Fechado: distinguir humano de agente com garantia é a
    base de toda a fronteira de autoridade, e texto livre apagaria a distinção."""

    HUMAN = "human"
    AGENT = "agent"
    SYSTEM_NOTE = "system_note"


class LabAgentMessage(ContractModel):
    """Uma mensagem do transcript. `sequence` é a ordem reproduzível; timestamp não entra
    porque ordenar por tempo é ambíguo sob escrita concorrente e nada no laço o lê."""

    role: LabAgentMessageRole
    sequence: int = Field(gt=0)
    content: NonEmptyStr


class LabAgentTurnLimits(ContractModel):
    """Os tetos efetivamente verificados no turno.

    Um teto anunciado que o runtime não verifica é promessa falsa, então este documento só
    existe quando os cinco valem. Budgets são do turno, não da sessão.
    """

    max_tool_calls_per_turn: int = Field(gt=0)
    max_provider_round_trips_per_turn: int = Field(gt=0)
    max_wall_seconds_per_turn: int = Field(gt=0)
    max_refusals_per_turn: int = Field(gt=0)
    max_output_tokens_per_round_trip: int = Field(gt=0)


class LabAgentEnvelope(ContractModel):
    """O documento exato oferecido a uma sessão do Lab Agent.

    `offered_tools` carrega os nomes do catálogo efetivo daquela forma de sessão; quais
    tools existem é do catálogo v1, que tem casa própria. O envelope divulga o conjunto,
    não o define.
    """

    schema_version: Literal["1"] = "1"
    session_id: NonEmptyStr
    scope: LabAgentSessionScope
    history: tuple[LabAgentMessage, ...] = ()
    contract_refs: tuple[ContractRef, ...] = ()
    evidence_refs: tuple[EvidenceRef, ...] = ()
    artifact_refs: tuple[ArtifactRef, ...] = ()
    offered_tools: tuple[NonEmptyStr, ...] = ()
    limits: LabAgentTurnLimits

    @model_validator(mode="after")
    def validate_disclosure(self) -> LabAgentEnvelope:
        if len({item.sequence for item in self.history}) != len(self.history):
            raise ValueError("session history requires distinct sequences")
        sequences = [item.sequence for item in self.history]
        if sequences != sorted(sequences):
            # Lacuna é permitida: o transcript enviado ao provider é limitado, então uma
            # janela pode começar depois do início da sessão. Ordem trocada não é janela.
            raise ValueError("session history must be ordered by sequence")
        if self.scope.form is LabAgentSessionForm.GENERAL and (
            self.contract_refs or self.evidence_refs or self.artifact_refs
        ):
            raise ValueError("General chat envelope cannot disclose Project content refs")
        return self

    @computed_field
    @property
    def digest(self) -> str:
        return sha256_json(semantic_model_dump(self))
