from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from evidrun.lab.protocol import LabToolContext, LabToolResult, ToolAvailability
from evidrun.lab.tools._base import strict_schema, validate_arguments
from evidrun.lab.tools.read_repository import LabReadRepository


class ReadContractRevisionTool:
    name = "read_contract_revision"
    availability = ToolAvailability()

    def __init__(self, repository: LabReadRepository) -> None:
        self._repository = repository

    def provider_schema(self) -> Mapping[str, Any]:
        return strict_schema({"revision_ref": {"type": "string"}}, required=("revision_ref",))

    def execute(self, arguments: Mapping[str, Any], context: LabToolContext) -> LabToolResult:
        validate_arguments(self.name, self.provider_schema(), arguments)
        reference = str(arguments["revision_ref"])
        content = self._repository.read_contract_revision(context.scope, reference)
        return LabToolResult(
            content=content, requested_refs=(reference,), returned_refs=(reference,)
        )
