from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, cast

from evidrun.lab.protocol import LabToolContext, LabToolResult, ToolAvailability
from evidrun.lab.tools._base import strict_schema, validate_arguments
from evidrun.lab.tools.read_port import LabReadRepository


class AggregateMetricsTool:
    name = "aggregate_metrics"
    availability = ToolAvailability()

    def __init__(self, repository: LabReadRepository) -> None:
        self._repository = repository

    def provider_schema(self) -> Mapping[str, Any]:
        return strict_schema(
            {
                "metric": {
                    "type": "string",
                    "enum": ["grade_score", "run_count", "completion_rate"],
                },
                "group_by": {
                    "type": "string",
                    "enum": ["status", "variant_id", "runner"],
                },
                "run_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 100,
                },
            },
            required=("metric", "group_by", "run_ids"),
        )

    def execute(self, arguments: Mapping[str, Any], context: LabToolContext) -> LabToolResult:
        validate_arguments(self.name, self.provider_schema(), arguments)
        run_ids = tuple(cast(Sequence[str], arguments["run_ids"]))
        groups = tuple(
            self._repository.aggregate_metrics(
                context.scope,
                metric=str(arguments["metric"]),
                group_by=str(arguments["group_by"]),
                run_ids=run_ids,
            )
        )
        if any("sample_size" not in group or int(group["sample_size"]) <= 0 for group in groups):
            raise ValueError("aggregate groups require a positive sample_size")
        return LabToolResult(
            content={"groups": groups},
            requested_refs=run_ids,
            returned_refs=run_ids,
        )
