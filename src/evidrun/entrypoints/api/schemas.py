"""Request bodies the API accepts.

Response shapes are deliberately absent: they are the contract `apps/web` consumes
and are produced inline by each route. Typing them belongs to WS-41.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LabSessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workspace_id: str
    title: str = Field(min_length=1, max_length=120)
    project_id: str | None = None
    focus_kind: str | None = None
    focus_id: str | None = None


class LabMessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workspace_id: str
    content: str = Field(min_length=1, max_length=100_000)


class ManifestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    yaml: str


class ContractDocumentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document: dict[str, object]
    status: Literal["draft", "proposed"] = "draft"


class ContractRegistrationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document: dict[str, object]
    status: str = "draft"


class ContractDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["accepted", "rejected", "superseded"]
    rationale: str = Field(min_length=1)


class RunEnqueueRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    admission_id: str = Field(min_length=1)


class ExecutionAdmissionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    execution_trust_id: str = Field(min_length=1)


class WorkspaceCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str


class ProjectCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workspace_id: str
    name: str
