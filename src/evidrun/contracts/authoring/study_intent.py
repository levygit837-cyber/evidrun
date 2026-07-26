"""A Study's declared intent: its scope and its question."""

from __future__ import annotations

from pydantic import model_validator

from evidrun.contracts.base import (
    ContractModel,
    NonEmptyStr,
)


class IntentScope(ContractModel):
    included: tuple[NonEmptyStr, ...] = ()
    excluded: tuple[NonEmptyStr, ...] = ()

    @model_validator(mode="after")
    def validate_boundaries(self) -> IntentScope:
        if set(self.included) & set(self.excluded):
            raise ValueError("intent scope cannot both include and exclude the same boundary")
        return self


class StudyIntent(ContractModel):
    purpose: NonEmptyStr
    questions: tuple[NonEmptyStr, ...] = ()
    hypothesis: NonEmptyStr | None = None
    decision_to_inform: NonEmptyStr | None = None
    scope: IntentScope = IntentScope()
    assumptions: tuple[NonEmptyStr, ...] = ()
