from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from evidrun.contracts.lab_agent.scope import LabAgentSessionForm
from evidrun.lab.protocol import LabToolContext, LabToolResult, ToolAvailability
from evidrun.lab.tools._base import strict_schema, validate_arguments
from evidrun.lab.tools.read_repository import LabReadRepository


class ListProjectsTool:
    name = "list_projects"
    availability = ToolAvailability(forms=frozenset(LabAgentSessionForm))

    def __init__(self, repository: LabReadRepository) -> None:
        self._repository = repository

    def provider_schema(self) -> Mapping[str, Any]:
        return strict_schema({}, required=())

    def execute(self, arguments: Mapping[str, Any], context: LabToolContext) -> LabToolResult:
        validate_arguments(self.name, self.provider_schema(), arguments)
        projects = tuple(self._repository.list_projects(context.scope))
        refs = tuple(str(item["id"]) for item in projects)
        return LabToolResult(content={"projects": projects}, returned_refs=refs)
