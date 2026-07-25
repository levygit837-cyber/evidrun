"""Run execution, one module per phase of an attempt.

`RunExecutionCoordinator` is the composition root: it holds the collaborators an
attempt runs against and delegates each phase to its module. It owns no phase logic
of its own, which is why the transactional boundaries live where the work does.

Where atomicity is the point, it stays inside the aggregate that guarantees it:
`prepare` calls one fenced `prepare_run_execution` transaction, and every write
carries the lease fence from `lease.py`.
"""

from __future__ import annotations

from evidrun.contexts import ContextComposer
from evidrun.contracts import RunExecutionAttempt, RunExecutionJob
from evidrun.infrastructure.artifacts.store import ArtifactStore
from evidrun.infrastructure.database import Repository
from evidrun.runs.adapters import ArtifactInputMaterializer, RuntimeAdapterCatalog
from evidrun.runs.coordinator.attempt import execute_attempt
from evidrun.runs.coordinator.context import (
    PREPARABLE_RUN_STATUSES,
    TERMINAL_RUN_STATUSES,
    ExecutionContext,
)
from evidrun.runs.coordinator.terminal import reject

__all__ = [
    "PREPARABLE_RUN_STATUSES",
    "TERMINAL_RUN_STATUSES",
    "ExecutionContext",
    "RunExecutionCoordinator",
]


class RunExecutionCoordinator:
    """Composition root for one runtime: wiring plus delegation, no phase logic."""

    def __init__(
        self,
        repository: Repository,
        artifact_store: ArtifactStore,
        catalog: RuntimeAdapterCatalog | None = None,
    ) -> None:
        self.repository = repository
        self.artifact_store = artifact_store
        self.catalog = catalog or RuntimeAdapterCatalog()
        if self.catalog.materializer is None:
            self.catalog.materializer = ArtifactInputMaterializer(artifact_store)
        self.catalog.project_id_for_spec = repository.read_model.project_id_for_run_spec
        self.admission_service = self.catalog.admission_service()
        self.composer = ContextComposer()
        self.context = ExecutionContext(
            repository=repository,
            artifact_store=artifact_store,
            catalog=self.catalog,
            composer=self.composer,
        )

    def enqueue(
        self,
        *,
        run_spec_id: str,
        admission_id: str,
        idempotency_key: str,
        retry_of: str | None = None,
        experiment_revision_id: str | None = None,
    ) -> tuple[str, RunExecutionJob]:
        run, job = self.repository.enqueue.enqueue_run(
            run_spec_id=run_spec_id,
            admission_id=admission_id,
            idempotency_key=idempotency_key,
            retry_of=retry_of,
            experiment_revision_id=experiment_revision_id,
        )
        return run.id, job

    async def execute_attempt(
        self, job: RunExecutionJob, attempt: RunExecutionAttempt
    ) -> None:
        await execute_attempt(self.context, job, attempt)

    def reject_attempt(
        self,
        job: RunExecutionJob,
        attempt: RunExecutionAttempt,
        *,
        reason_code: str,
    ) -> None:
        reject(self.context, job, attempt, reason_code=reason_code)
