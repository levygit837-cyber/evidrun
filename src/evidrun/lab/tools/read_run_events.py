from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from evidrun.lab.protocol import LabToolContext, LabToolResult, ToolAvailability
from evidrun.lab.tools._base import strict_schema, validate_arguments
from evidrun.lab.tools.read_port import LabReadRepository


class ReadRunEventsTool:
    name = "read_run_events"
    availability = ToolAvailability()

    def __init__(self, repository: LabReadRepository) -> None:
        self._repository = repository

    def provider_schema(self) -> Mapping[str, Any]:
        return strict_schema(
            {
                "run_id": {"type": "string"},
                "after_sequence": {"type": "integer", "minimum": 0},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100},
            },
            required=("run_id", "after_sequence", "limit"),
        )

    def execute(self, arguments: Mapping[str, Any], context: LabToolContext) -> LabToolResult:
        validate_arguments(self.name, self.provider_schema(), arguments)
        run_id = str(arguments["run_id"])
        events = tuple(
            self._repository.read_run_events(
                context.scope,
                run_id,
                after_sequence=int(arguments["after_sequence"]),
                limit=int(arguments["limit"]),
            )
        )
        refs = tuple(str(item["event_id"]) for item in events)
        return LabToolResult(
            content={"events": events},
            requested_refs=(run_id,),
            returned_refs=refs,
        )
