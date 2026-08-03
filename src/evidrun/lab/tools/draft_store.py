"""Adapter mínimo sobre registry/read-model, sem superfície de decisão."""

from __future__ import annotations

from evidrun.contracts.base import RevisionEnvelope
from evidrun.contracts.registry import ContractResolver
from evidrun.infrastructure.database.read_model import ReadModel
from evidrun.infrastructure.database.registry import ContractRegistryStore
from evidrun.lab.tools.propose_draft import DraftRevisionRecord

__all__ = ["DatabaseDraftStore"]


class DatabaseDraftStore:
    """Expõe somente as operações necessárias a draft e pedido de aprovação."""

    def __init__(self, registry: ContractRegistryStore, read_model: ReadModel) -> None:
        self._registry = registry
        self._read_model = read_model
        self._validated: set[tuple[str, int, str, str]] = set()

    def contract_registry(self, project_id: str | None = None) -> ContractResolver:
        return self._registry.contract_registry(project_id)

    def record_draft_validation(self, key: tuple[str, int, str, str]) -> None:
        self._validated.add(key)

    def consume_draft_validation(self, key: tuple[str, int, str, str]) -> bool:
        if key not in self._validated:
            return False
        self._validated.remove(key)
        return True

    def get_contract_revision_record(self, revision_id: str) -> DraftRevisionRecord:
        found = next(
            (
                item
                for item in self._read_model.list_contract_revisions()
                if item["id"] == revision_id
            ),
            None,
        )
        if found is None:
            raise KeyError(revision_id)
        return DraftRevisionRecord(
            id=str(found["id"]),
            status=str(found["status"]),
            digest=str(found["digest"]),
            project_id=str(found["project_id"]),
            decision=str(found["decision"]) if found["decision"] is not None else None,
        )

    def save_contract_revision(
        self, revision: RevisionEnvelope, *, status: str = "draft"
    ) -> DraftRevisionRecord:
        row = self._registry.save_contract_revision(revision, status=status)
        return self.get_contract_revision_record(row.id)

    def get_contract_revision(self, revision_id: str) -> RevisionEnvelope:
        return self._read_model.get_contract_revision(revision_id)
