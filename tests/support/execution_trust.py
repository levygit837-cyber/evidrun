"""Small adapters that keep integration fixtures on the production trust path."""

from __future__ import annotations

from evidrun.contracts import ExecutionTrustRecord, RunSpec, StudyRevision
from evidrun.infrastructure.database import Repository
from evidrun.runs.preparation import ExecutionPreparationService


def prepare_registered_study(
    repository: Repository, study: StudyRevision
) -> tuple[RunSpec, ExecutionTrustRecord, str]:
    row = repository.registry.save_contract_revision(study)
    preparation = ExecutionPreparationService(repository).prepare(row.id)
    if len(preparation.run_specs) != 1:
        raise ValueError("fixture helper requires a one-RunSpec Study")
    prepared = preparation.run_specs[0]
    return prepared.spec, prepared.execution_trust, prepared.row_id
