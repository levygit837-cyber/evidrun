"""The Goal and its revision: what the Run pursues, and how its mode is declared."""

from __future__ import annotations

from typing import Literal

from pydantic import model_validator

from evidrun.contracts.base import (
    ContractModel,
    ContractType,
    NonEmptyStr,
    RevisionEnvelope,
)


class GoalOutcome(ContractModel):
    id: NonEmptyStr
    description: NonEmptyStr


class GoalConstraint(ContractModel):
    id: NonEmptyStr
    rule: Literal["must", "must_not"]
    description: NonEmptyStr


class GoalSpec(ContractModel):
    mode: Literal["goal_state", "bounded_exploration"]
    instruction: NonEmptyStr
    outcomes: tuple[GoalOutcome, ...] = ()
    learning_targets: tuple[NonEmptyStr, ...] = ()
    constraints: tuple[GoalConstraint, ...] = ()
    evidence_expectations: tuple[NonEmptyStr, ...] = ()
    completion_observations: tuple[NonEmptyStr, ...] = ()

    @model_validator(mode="after")
    def validate_goal_shape(self) -> GoalSpec:
        outcome_ids = [item.id for item in self.outcomes]
        constraint_ids = [item.id for item in self.constraints]
        if len(outcome_ids) != len(set(outcome_ids)):
            raise ValueError("goal outcome ids must be unique")
        if len(constraint_ids) != len(set(constraint_ids)):
            raise ValueError("goal constraint ids must be unique")
        if set(outcome_ids) & set(constraint_ids):
            raise ValueError("goal ids must be unique across outcomes and constraints")
        if self.mode == "goal_state" and not self.outcomes:
            raise ValueError("goal_state requires at least one outcome")
        if self.mode == "bounded_exploration" and not (self.learning_targets or self.outcomes):
            raise ValueError("bounded_exploration requires a learning target or outcome")
        return self


class GoalRevision(RevisionEnvelope):
    contract_type: Literal[ContractType.GOAL] = ContractType.GOAL
    payload: GoalSpec
