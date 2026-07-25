from __future__ import annotations

from evidrun.contracts.authority import (
    HumanAttestationVerifier,
    UnavailableHumanAttestationVerifier,
)
from evidrun.infrastructure.database.catalog import CatalogStore
from evidrun.infrastructure.database.engine import Database
from evidrun.infrastructure.database.evaluation import CheckpointStore, EvaluationStore
from evidrun.infrastructure.database.ledger.store import LedgerStore
from evidrun.infrastructure.database.queue.enqueue import EnqueueStore
from evidrun.infrastructure.database.queue.lease import LeaseStore
from evidrun.infrastructure.database.queue.preparation import PreparationStore
from evidrun.infrastructure.database.read_model import ReadModel
from evidrun.infrastructure.database.registry import ContractRegistryStore
from evidrun.infrastructure.database.unit_of_work import UnitOfWork

__all__ = ["Repository"]


class Repository:
    """Composition root over the persistence aggregates.

    It owns no query of its own. Each aggregate is reachable as an attribute and
    every one of them shares the single `UnitOfWork`, so an operation whose
    atomicity spans aggregates passes the live session down to its collaborators
    instead of opening a second one. That is what keeps `claim_next_job` and
    `prepare_run_execution` at one transaction each after the decomposition.
    """

    def __init__(
        self,
        database: Database,
        human_attestation_verifier: HumanAttestationVerifier | None = None,
    ):
        self.database = database
        self.human_attestation_verifier = (
            human_attestation_verifier or UnavailableHumanAttestationVerifier()
        )
        self.unit_of_work = UnitOfWork(database)
        self.read_model = ReadModel(self.unit_of_work)
        self.catalog = CatalogStore(self.unit_of_work)
        self.registry = ContractRegistryStore(
            self.unit_of_work, self.human_attestation_verifier
        )
        self.ledger = LedgerStore(self.unit_of_work)
        self.evaluation = EvaluationStore(
            self.unit_of_work, self.human_attestation_verifier
        )
        self.checkpoints = CheckpointStore(self.unit_of_work)
        self.enqueue = EnqueueStore(self.unit_of_work)
        self.lease = LeaseStore(self.unit_of_work)
        self.preparation = PreparationStore(self.unit_of_work)
