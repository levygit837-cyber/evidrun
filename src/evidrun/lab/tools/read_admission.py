from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from evidrun.lab.protocol import LabToolContext, LabToolResult, ToolAvailability
from evidrun.lab.tools._base import strict_schema, validate_arguments
from evidrun.lab.tools.read_repository import LabReadRepository


class ReadAdmissionTool:
    name = "read_admission"
    availability = ToolAvailability()

    def __init__(self, repository: LabReadRepository) -> None:
        self._repository = repository

    def provider_schema(self) -> Mapping[str, Any]:
        return strict_schema({"admission_id": {"type": "string"}}, required=("admission_id",))

    def execute(self, arguments: Mapping[str, Any], context: LabToolContext) -> LabToolResult:
        validate_arguments(self.name, self.provider_schema(), arguments)
        admission_id = str(arguments["admission_id"])
        content = self._repository.read_admission(context.scope, admission_id)
        return LabToolResult(
            content=content,
            requested_refs=(admission_id,),
            returned_refs=(admission_id,),
        )
