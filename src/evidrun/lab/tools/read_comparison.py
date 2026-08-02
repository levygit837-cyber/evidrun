from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from evidrun.lab.protocol import LabToolContext, LabToolResult, ToolAvailability
from evidrun.lab.tools._base import strict_schema, validate_arguments
from evidrun.lab.tools.read_repository import LabReadRepository


class ReadComparisonTool:
    name = "read_comparison"
    availability = ToolAvailability()

    def __init__(self, repository: LabReadRepository) -> None:
        self._repository = repository

    def provider_schema(self) -> Mapping[str, Any]:
        return strict_schema(
            {"comparison_id": {"type": "string"}}, required=("comparison_id",)
        )

    def execute(self, arguments: Mapping[str, Any], context: LabToolContext) -> LabToolResult:
        validate_arguments(self.name, self.provider_schema(), arguments)
        comparison_id = str(arguments["comparison_id"])
        content = self._repository.read_comparison(context.scope, comparison_id)
        return LabToolResult(
            content=content,
            requested_refs=(comparison_id,),
            returned_refs=(comparison_id,),
        )
