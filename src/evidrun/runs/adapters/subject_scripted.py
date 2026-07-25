"""The offline Subject: one deterministic pass over a single materialized input."""

from __future__ import annotations

from collections.abc import Mapping

from evidrun.contracts import SubjectEnvelope
from evidrun.runs.adapters.types import ToolTraceSink
from evidrun.shared.capabilities import capability_ref
from evidrun.shared.ports import SubjectResult
from evidrun.subject_runners import ScriptedLogInvestigator


class ScriptedLogInvestigatorAdapter:
    def __init__(self, runner: ScriptedLogInvestigator | None = None) -> None:
        self.runner = runner or ScriptedLogInvestigator()
        self.name = self.runner.name
        self.ref = capability_ref("evidrun.runner", self.runner.name)

    async def execute(
        self,
        envelope: SubjectEnvelope,
        materialized_inputs: Mapping[str, str],
        trace_sink: ToolTraceSink | None = None,
    ) -> SubjectResult:
        """Run the deterministic investigator; it executes no tools, so no trace."""

        del trace_sink
        if len(materialized_inputs) != 1:
            raise ValueError("scripted runner requires exactly one materialized input")
        context = next(iter(materialized_inputs.values()))
        return await self.runner.execute(envelope.goal.instruction, context)
