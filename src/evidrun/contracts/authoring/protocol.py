"""Protocolo de interação: nós, gatilhos e arestas do grafo de execução."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator

from evidrun.contracts.base import (
    ArtifactRef,
    CapabilityDescriptorRef,
    ContractModel,
    ContractType,
    NonEmptyStr,
    RevisionEnvelope,
)


class InteractionNode(ContractModel):
    id: NonEmptyStr
    kind: Literal["prompt", "await_subject", "checkpoint", "human_approval", "terminal"]
    content_ref: ArtifactRef | None = None


class AlwaysTrigger(ContractModel):
    kind: Literal["always"] = "always"


class EventTrigger(ContractModel):
    kind: Literal["event"] = "event"
    event_type: NonEmptyStr


class CheckpointReachedTrigger(ContractModel):
    kind: Literal["checkpoint_reached"] = "checkpoint_reached"
    checkpoint_definition_id: NonEmptyStr


class EvaluatorSignalTrigger(ContractModel):
    kind: Literal["evaluator_signal"] = "evaluator_signal"
    stage_id: NonEmptyStr
    signal: NonEmptyStr


class HumanSignalTrigger(ContractModel):
    kind: Literal["human_signal"] = "human_signal"
    signal: NonEmptyStr


class PredicateTrigger(ContractModel):
    kind: Literal["predicate"] = "predicate"
    predicate_ref: CapabilityDescriptorRef


InteractionTrigger = Annotated[
    AlwaysTrigger
    | EventTrigger
    | CheckpointReachedTrigger
    | EvaluatorSignalTrigger
    | HumanSignalTrigger
    | PredicateTrigger,
    Field(discriminator="kind"),
]


class InteractionEdge(ContractModel):
    source: NonEmptyStr
    target: NonEmptyStr
    trigger: InteractionTrigger
    priority: int = 0
    max_activations: int = Field(default=1, gt=0)


class InteractionProtocolSpec(ContractModel):
    mode: Literal["single_turn", "graph"]
    system_prompt_ref: ArtifactRef | None = None
    initial_message_refs: tuple[ArtifactRef, ...] = ()
    max_turns: int = Field(default=1, gt=0)
    nodes: tuple[InteractionNode, ...] = ()
    edges: tuple[InteractionEdge, ...] = ()

    @model_validator(mode="after")
    def validate_graph(self) -> InteractionProtocolSpec:
        if self.mode == "single_turn" and (self.nodes or self.edges):
            raise ValueError("single_turn protocol cannot declare graph nodes or edges")
        if self.mode == "graph":
            ids = [node.id for node in self.nodes]
            if not ids:
                raise ValueError("graph protocol requires nodes")
            if len(ids) != len(set(ids)):
                raise ValueError("interaction node ids must be unique")
            known = set(ids)
            for edge in self.edges:
                if edge.source not in known or edge.target not in known:
                    raise ValueError("interaction edge references unknown node")
        return self


class InteractionProtocolRevision(RevisionEnvelope):
    contract_type: Literal[ContractType.INTERACTION_PROTOCOL] = ContractType.INTERACTION_PROTOCOL
    payload: InteractionProtocolSpec
