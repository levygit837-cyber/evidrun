"""The concrete adapters one Run executes: Subjects, graders, tool, and catalog."""

from evidrun.runs.adapters.catalog import (
    EvaluatorAdapter,
    RuntimeAdapterCatalog,
    SubjectAdapter,
)
from evidrun.runs.adapters.grader_cause import ExactCauseGraderAdapter
from evidrun.runs.adapters.grader_read_answer import ExactReadAnswerGraderAdapter
from evidrun.runs.adapters.materializer import ArtifactInputMaterializer
from evidrun.runs.adapters.subject_responses import ResponsesReadAgentAdapter
from evidrun.runs.adapters.subject_scripted import ScriptedLogInvestigatorAdapter
from evidrun.runs.adapters.tool_read_text import ReadArtifactTextToolAdapter
from evidrun.runs.adapters.types import (
    EvaluationOutcome,
    ReadToolResult,
    SubjectBudgetExceeded,
    ToolTraceSink,
)

__all__ = [
    "ArtifactInputMaterializer",
    "EvaluationOutcome",
    "EvaluatorAdapter",
    "ExactCauseGraderAdapter",
    "ExactReadAnswerGraderAdapter",
    "ReadArtifactTextToolAdapter",
    "ReadToolResult",
    "ResponsesReadAgentAdapter",
    "RuntimeAdapterCatalog",
    "ScriptedLogInvestigatorAdapter",
    "SubjectAdapter",
    "SubjectBudgetExceeded",
    "ToolTraceSink",
]
