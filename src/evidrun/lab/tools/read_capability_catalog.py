from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from evidrun.contracts.lab_agent.scope import LabAgentSessionForm
from evidrun.lab.protocol import LabToolContext, LabToolResult, ToolAvailability
from evidrun.lab.tools._base import strict_schema, validate_arguments
from evidrun.lab.tools.read_repository import LabReadRepository


class ReadCapabilityCatalogTool:
    name = "read_capability_catalog"
    availability = ToolAvailability(forms=frozenset(LabAgentSessionForm))

    def __init__(self, repository: LabReadRepository) -> None:
        self._repository = repository

    def provider_schema(self) -> Mapping[str, Any]:
        return strict_schema({}, required=())

    def execute(self, arguments: Mapping[str, Any], context: LabToolContext) -> LabToolResult:
        del context
        validate_arguments(self.name, self.provider_schema(), arguments)
        catalog = self._repository.read_capability_catalog()
        return LabToolResult(
            content={
                "admitted_capabilities": catalog.admitted,
                "active_rejections": catalog.active_rejections,
            }
        )
