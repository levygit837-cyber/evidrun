"""The one closed tool the Subject may call: bounded line reads from its envelope.

Every rejection here is a `PermissionError` on purpose. The tool cannot reach a
path, a URL, or an artifact the SubjectEnvelope did not list, so an argument
outside the closed schema is an authority failure, not a validation nicety.
"""

from __future__ import annotations

from collections.abc import Mapping

from evidrun.contracts import SubjectEnvelope, capability_ref
from evidrun.runs.adapters.types import ReadToolResult
from evidrun.shared.types import canonical_json


class ReadArtifactTextToolAdapter:
    """Read bounded line ranges from artifacts already admitted to SubjectEnvelope."""

    name = "read_text"
    ref = capability_ref("evidrun.tool", "read-artifact-text-v1")
    allowed_permission = "read:subject_artifacts"
    authority_constraint = "subject-envelope-only"
    max_lines_per_call = 80

    @property
    def provider_schema(self) -> dict[str, object]:
        return {
            "type": "function",
            "name": self.name,
            "description": (
                "Read a bounded range of numbered lines from one text input explicitly "
                "listed in the SubjectEnvelope. It cannot access paths, URLs, or other artifacts."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "input_id": {
                        "type": "string",
                        "description": "Exact SubjectEnvelope input id.",
                    },
                    "start_line": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "One-based first line to read.",
                    },
                    "max_lines": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": self.max_lines_per_call,
                        "description": "Maximum number of lines to return.",
                    },
                },
                "required": ["input_id", "start_line", "max_lines"],
                "additionalProperties": False,
            },
            "strict": True,
        }

    def execute(
        self,
        *,
        envelope: SubjectEnvelope,
        materialized_inputs: Mapping[str, str],
        arguments: Mapping[str, object],
    ) -> ReadToolResult:
        if set(arguments) != {"input_id", "start_line", "max_lines"}:
            raise PermissionError("tool arguments do not match the closed read schema")
        input_id = arguments.get("input_id")
        start_line = arguments.get("start_line")
        max_lines = arguments.get("max_lines")
        if not isinstance(input_id, str) or input_id not in materialized_inputs:
            raise PermissionError("requested input is outside the SubjectEnvelope")
        start_line, max_lines = self._allowed_range(start_line, max_lines)
        binding = next((item for item in envelope.inputs if item.id == input_id), None)
        if binding is None:
            raise PermissionError("requested input is outside the SubjectEnvelope")
        lines = materialized_inputs[input_id].splitlines()
        selected = lines[start_line - 1 : start_line - 1 + max_lines]
        numbered: list[dict[str, int | str]] = [
            {"line": start_line + index, "text": text} for index, text in enumerate(selected)
        ]
        return ReadToolResult(
            output=canonical_json(
                {
                    "input_id": input_id,
                    "start_line": start_line,
                    "returned_lines": len(numbered),
                    "total_lines": len(lines),
                    "truncated": start_line - 1 + len(numbered) < len(lines),
                    "lines": numbered,
                }
            ),
            evidence="\n".join(str(item["text"]) for item in numbered),
            classification=binding.source.classification,
        )

    def _allowed_range(self, start_line: object, max_lines: object) -> tuple[int, int]:
        """Return both bounds as real positive ints, or refuse the call.

        Returning the values instead of asserting keeps the caller's types narrowed.
        `bool` is an `int` in Python but is not an accepted line number here.
        """

        if (
            isinstance(start_line, int)
            and not isinstance(start_line, bool)
            and start_line >= 1
            and isinstance(max_lines, int)
            and not isinstance(max_lines, bool)
            and 1 <= max_lines <= self.max_lines_per_call
        ):
            return start_line, max_lines
        raise PermissionError("requested line range is outside the read tool limits")
