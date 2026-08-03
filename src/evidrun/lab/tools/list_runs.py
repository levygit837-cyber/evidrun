from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from evidrun.lab.protocol import LabToolContext, LabToolResult, ToolAvailability
from evidrun.lab.tools._base import strict_schema, validate_arguments
from evidrun.lab.tools.read_port import LabReadRepository


class ListRunsTool:
    name = "list_runs"
    availability = ToolAvailability()

    def __init__(self, repository: LabReadRepository) -> None:
        self._repository = repository

    def provider_schema(self) -> Mapping[str, Any]:
        return strict_schema(
            {
                "limit": {"type": "integer", "minimum": 1, "maximum": 100},
                "status": {"type": "string", "nullable": True},
            },
            required=("limit", "status"),
        )

    def execute(self, arguments: Mapping[str, Any], context: LabToolContext) -> LabToolResult:
        validate_arguments(self.name, self.provider_schema(), arguments)
        status = arguments["status"]
        runs = tuple(
            self._repository.list_runs(
                context.scope,
                limit=int(arguments["limit"]),
                status=str(status) if status is not None else None,
            )
        )
        refs = tuple(str(item["run_id"]) for item in runs)
        return LabToolResult(content={"runs": runs}, returned_refs=refs)
