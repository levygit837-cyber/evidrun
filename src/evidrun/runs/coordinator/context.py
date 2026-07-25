"""What every execution phase needs, passed explicitly instead of via `self`."""

from __future__ import annotations

from dataclasses import dataclass

from evidrun.contexts import ContextComposer
from evidrun.infrastructure.artifacts.store import ArtifactStore
from evidrun.infrastructure.database import Repository
from evidrun.runs.adapters import RuntimeAdapterCatalog

TERMINAL_RUN_STATUSES = frozenset(
    {"completed", "failed", "cancelled", "budget_exhausted", "guardrail_stopped"}
)
PREPARABLE_RUN_STATUSES = frozenset({"queued", "preparing", "running", "evaluating"})


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    """The collaborators one Run attempt executes against."""

    repository: Repository
    artifact_store: ArtifactStore
    catalog: RuntimeAdapterCatalog
    composer: ContextComposer

    def project_id(self, run_id: str) -> str:
        return self.repository.read_model.project_id_for_run(run_id)
