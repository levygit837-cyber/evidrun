"""In-memory contract revision store with its authority and immutability rules.

This is not a compiler: it holds revisions and their human decisions, and answers
`resolve()` only for revisions that were accepted. It lives beside the compiler
because both speak the same vocabulary, but a registry is a different module with
a different job.

Two invariants live here and are load-bearing:

- a revision is immutable, and its number is monotonic per logical id;
- acceptance by `repository_fixture` is restricted to the legacy import path. Any
  other caller fails closed, because a fixture is not human authority.
"""

from __future__ import annotations

from typing import Protocol

from evidrun.contracts.authority import (
    HumanAttestationVerifier,
    UnavailableHumanAttestationVerifier,
)
from evidrun.contracts.base import (
    ContractRef,
    ContractType,
    RevisionDecisionRecord,
    RevisionEnvelope,
)

RevisionKey = tuple[ContractType, str, int]


class ContractResolver(Protocol):
    def resolve(self, reference: ContractRef) -> RevisionEnvelope: ...


class InMemoryContractRegistry(ContractResolver):
    def __init__(
        self,
        human_attestation_verifier: HumanAttestationVerifier | None = None,
        *,
        allow_repository_fixture: bool = False,
    ) -> None:
        self._revisions: dict[RevisionKey, RevisionEnvelope] = {}
        self._decisions: dict[RevisionKey, RevisionDecisionRecord] = {}
        self._human_attestation_verifier = (
            human_attestation_verifier or UnavailableHumanAttestationVerifier()
        )
        self._allow_repository_fixture = allow_repository_fixture

    @staticmethod
    def _key(reference: ContractRef | RevisionEnvelope) -> RevisionKey:
        ref = reference if isinstance(reference, ContractRef) else reference.ref
        return (ref.contract_type, ref.logical_id, ref.revision)

    def add(self, revision: RevisionEnvelope) -> None:
        """Store a revision, rejecting a rewrite or a gap in the revision number."""

        key = self._key(revision)
        existing = self._revisions.get(key)
        if existing is not None:
            if (
                existing.digest != revision.digest
                or existing.semantic_document() != revision.semantic_document()
            ):
                raise ValueError(
                    "an immutable contract revision already exists with different content"
                )
            return
        self._require_monotonic(revision)
        self._revisions[key] = revision

    def decide(self, decision: RevisionDecisionRecord) -> None:
        """Record a decision, verifying human authority before anything else."""

        self._authorize(decision)
        key = self._key(decision.revision_ref)
        revision = self._revisions.get(key)
        if revision is None or revision.digest != decision.revision_ref.digest:
            raise ValueError("decision references an unknown or mismatched revision")
        existing = self._decisions.get(key)
        if existing is None and decision.decision == "superseded":
            raise ValueError("only an accepted revision can be superseded")
        if existing is not None and self._conflicts(existing, decision):
            raise ValueError("contract revision already has a conflicting decision")
        self._decisions[key] = decision

    def add_accepted(
        self, revision: RevisionEnvelope, decision: RevisionDecisionRecord
    ) -> None:
        self.add(revision)
        self.decide(decision)

    def resolve(self, reference: ContractRef) -> RevisionEnvelope:
        """Return the revision only when it exists, matches, and was accepted."""

        key = self._key(reference)
        revision = self._revisions.get(key)
        if revision is None:
            raise KeyError(
                f"contract revision not found: {reference.logical_id}@{reference.revision}"
            )
        if revision.digest != reference.digest:
            raise ValueError("contract reference digest mismatch")
        decision = self._decisions.get(key)
        if decision is None or decision.decision != "accepted":
            raise ValueError("only accepted contract revisions can be resolved")
        return revision

    def revisions(self) -> tuple[RevisionEnvelope, ...]:
        return tuple(self._revisions.values())

    def decisions(self) -> tuple[RevisionDecisionRecord, ...]:
        return tuple(self._decisions.values())

    def _authorize(self, decision: RevisionDecisionRecord) -> None:
        """Verified human authority, or the narrow legacy fixture path. Nothing else."""

        if decision.authority.kind == "verified_human":
            self._human_attestation_verifier.verify(
                decision.authority.attestation,
                expected_subject_digest=decision.human_subject_digest(),
            )
        elif not self._allow_repository_fixture:
            raise PermissionError(
                "repository fixture acceptance is restricted to the legacy import path"
            )

    def _require_monotonic(self, revision: RevisionEnvelope) -> None:
        prior_revisions = [
            candidate.revision
            for candidate in self._revisions.values()
            if candidate.ref.contract_type == revision.ref.contract_type
            and candidate.logical_id == revision.logical_id
        ]
        expected = max(prior_revisions, default=0) + 1
        if revision.revision != expected:
            raise ValueError(
                f"contract revision must be monotonic; expected {expected}, "
                f"received {revision.revision}"
            )

    @staticmethod
    def _conflicts(
        existing: RevisionDecisionRecord, decision: RevisionDecisionRecord
    ) -> bool:
        """Accepted may become superseded; every other transition conflicts."""

        if existing.decision == decision.decision:
            return False
        return not (
            existing.decision == "accepted" and decision.decision == "superseded"
        )
