from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from evidrun.lab.protocol import LabToolContext, LabToolResult, ToolAvailability
from evidrun.lab.tools._base import strict_schema, validate_arguments
from evidrun.lab.tools.read_repository import LabReadRepository


class ReadRunTool:
    name = "read_run"
    availability = ToolAvailability()

    def __init__(self, repository: LabReadRepository) -> None:
        self._repository = repository

    def provider_schema(self) -> Mapping[str, Any]:
        return strict_schema({"run_id": {"type": "string"}}, required=("run_id",))

    def execute(self, arguments: Mapping[str, Any], context: LabToolContext) -> LabToolResult:
        validate_arguments(self.name, self.provider_schema(), arguments)
        run_id = str(arguments["run_id"])
        content = self._repository.read_run(context.scope, run_id)
        return LabToolResult(content=content, requested_refs=(run_id,), returned_refs=(run_id,))
