"""Small adapters that keep integration fixtures on the production trust path."""

from __future__ import annotations

from datetime import UTC, datetime

from evidrun.contracts import (
    ExecutionRevisionSet,
    ExecutionTrustRecord,
    RunSpec,
    StudyRevision,
)
from evidrun.infrastructure.database import Repository
from evidrun.runs.preparation import ExecutionPreparationService


def unpersisted_unverified_trust(
    spec: RunSpec, *, project_id: str = "test-project"
) -> ExecutionTrustRecord:
    """Build the narrow trust input used by pure admission unit tests."""

    revision_set = ExecutionRevisionSet(
        project_id=project_id,
        study_ref=spec.study_ref,
        revision_refs=(spec.study_ref,),
    )
    return ExecutionTrustRecord(
        trust_id=f"trust_test_{spec.digest[:16]}",
        kind="unverified_revision_set",
        project_id=project_id,
        study_ref=spec.study_ref,
        revision_refs=revision_set.revision_refs,
        revision_set_digest=revision_set.revision_set_digest,
        run_spec_digest=spec.digest,
        created_at_utc=datetime(2026, 1, 1, tzinfo=UTC),
    )


def prepare_registered_study(
    repository: Repository, study: StudyRevision
) -> tuple[RunSpec, ExecutionTrustRecord, str]:
    row = repository.registry.save_contract_revision(study)
    preparation = ExecutionPreparationService(repository).prepare(row.id)
    if len(preparation.run_specs) != 1:
        raise ValueError("fixture helper requires a one-RunSpec Study")
    prepared = preparation.run_specs[0]
    return prepared.spec, prepared.execution_trust, prepared.row_id
