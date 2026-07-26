"""Durable job and attempt: the lease chain that executes a Run."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, computed_field, model_validator

from evidrun.contracts.base import (
    ContractModel,
    Digest,
    NonEmptyStr,
    UtcDateTime,
    semantic_model_dump,
)
from evidrun.shared.types import sha256_json


class RunExecutionJob(ContractModel):
    """Durable operational queue state for one canonical Run."""

    schema_version: Literal["1"] = "1"
    job_id: NonEmptyStr
    run_id: NonEmptyStr
    status: Literal["queued", "leased", "completed", "rejected"]
    idempotency_key: NonEmptyStr
    request_digest: Digest
    available_at_utc: UtcDateTime
    active_attempt_id: NonEmptyStr | None = None
    lease_generation: int = Field(ge=0)
    created_at_utc: UtcDateTime
    finished_at_utc: UtcDateTime | None = None
    rejection_code: NonEmptyStr | None = None

    @model_validator(mode="after")
    def validate_state(self) -> RunExecutionJob:
        if self.status == "leased" and self.active_attempt_id is None:
            raise ValueError("leased job requires an active attempt")
        if self.status != "leased" and self.active_attempt_id is not None:
            raise ValueError("only a leased job can expose an active attempt")
        if self.status in {"completed", "rejected"} and self.finished_at_utc is None:
            raise ValueError("terminal job requires finished_at_utc")
        if self.status not in {"completed", "rejected"} and self.finished_at_utc is not None:
            raise ValueError("non-terminal job cannot have finished_at_utc")
        if self.status == "rejected" and self.rejection_code is None:
            raise ValueError("rejected job requires a rejection code")
        if self.status != "rejected" and self.rejection_code is not None:
            raise ValueError("only a rejected job can have a rejection code")
        return self

    @computed_field
    @property
    def digest(self) -> str:
        return sha256_json(semantic_model_dump(self))


class RunExecutionAttempt(ContractModel):
    """One fenced worker lease over a RunExecutionJob."""

    schema_version: Literal["1"] = "1"
    attempt_id: NonEmptyStr
    job_id: NonEmptyStr
    ordinal: int = Field(gt=0)
    worker_id: NonEmptyStr
    lease_generation: int = Field(gt=0)
    status: Literal["leased", "completed", "released", "expired", "rejected"]
    leased_at_utc: UtcDateTime
    lease_expires_at_utc: UtcDateTime
    last_heartbeat_at_utc: UtcDateTime
    finished_at_utc: UtcDateTime | None = None
    reason_code: NonEmptyStr | None = None

    @model_validator(mode="after")
    def validate_state(self) -> RunExecutionAttempt:
        if self.lease_expires_at_utc <= self.leased_at_utc:
            raise ValueError("lease expiry must be after lease acquisition")
        if self.last_heartbeat_at_utc < self.leased_at_utc:
            raise ValueError("heartbeat cannot predate lease acquisition")
        if self.status == "leased" and self.finished_at_utc is not None:
            raise ValueError("active attempt cannot be finished")
        if self.status != "leased" and self.finished_at_utc is None:
            raise ValueError("inactive attempt requires finished_at_utc")
        return self

    @computed_field
    @property
    def digest(self) -> str:
        return sha256_json(semantic_model_dump(self))
