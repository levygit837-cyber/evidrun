from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from evidrun.authority.authenticator import MemoryAuthenticator
from evidrun.authority.policy import AuthorityMode
from evidrun.authority.repository import (
    AuthorityRepository,
    ChallengeUnavailable,
    CredentialUnavailable,
)
from evidrun.authority.service import HumanAuthorityService
from evidrun.authority.subject import RevisionDecisionSubject
from evidrun.authority.verifier import LocalWebAuthnVerifier
from evidrun.contracts.authoring import GoalConstraint, GoalOutcome, GoalRevision, GoalSpec
from evidrun.contracts.authority import HumanAttestationUnavailable
from evidrun.infrastructure.artifacts.store import ArtifactStore, MemoryKeyProvider
from evidrun.infrastructure.database import Database, Repository


class AuthorityHarness:
    def __init__(self, tmp_path: Path) -> None:
        self.database = Database(tmp_path / "authority.db")
        self.database.create_all()
        self.artifacts = ArtifactStore(
            tmp_path / "artifacts", key_provider=MemoryKeyProvider()
        )
        self.authority_repository = AuthorityRepository(self.database)
        self.verifier = LocalWebAuthnVerifier(self.authority_repository, self.artifacts)
        self.repository = Repository(
            self.database, human_attestation_verifier=self.verifier
        )
        self.service = HumanAuthorityService(
            repository=self.authority_repository,
            authenticator=MemoryAuthenticator(),
            artifacts=self.artifacts,
        )

    def project(self) -> str:
        workspace = self.repository.catalog.create_workspace("Authority WS")
        project = self.repository.catalog.create_project(workspace.id, "Authority Project")
        return project.id

    def goal_revision(self, project_id: str) -> GoalRevision:
        return GoalRevision(
            logical_id="authority-goal",
            revision=1,
            project_id=project_id,
            title="Authority goal",
            payload=GoalSpec(
                mode="goal_state",
                instruction="Produce one terminal answer.",
                outcomes=(
                    GoalOutcome(id="answer", description="Produce a terminal answer."),
                ),
                constraints=(
                    GoalConstraint(
                        id="no-external",
                        rule="must_not",
                        description="Access external resources.",
                    ),
                ),
            ),
        )

    def dispose(self) -> None:
        self.database.dispose()


@pytest.fixture
def harness(tmp_path: Path) -> Iterator[AuthorityHarness]:
    built = AuthorityHarness(tmp_path)
    yield built
    built.dispose()


def _subject(revision: GoalRevision) -> RevisionDecisionSubject:
    return RevisionDecisionSubject(
        revision_ref=revision.ref,
        decision="accepted",
        rationale="Reviewed the exact revision content.",
    )


def test_verified_human_accepts_a_revision(harness: AuthorityHarness) -> None:
    project_id = harness.project()
    revision = harness.goal_revision(project_id)
    harness.repository.registry.save_contract_revision(revision, status="proposed")
    credential = harness.service.enroll(
        principal_id="alice",
        display_name="Alice",
        relying_party_id="evidrun.local",
        origin="https://evidrun.local",
    )
    subject = _subject(revision)
    attestation = harness.service.confirm_with_local_authenticator(
        mode=AuthorityMode.PRIVILEGED,
        subject=subject,
        credential_id=credential.credential_id,
        project_id=project_id,
    )
    row = harness.repository.registry.decide_contract_revision(subject.build_decision(attestation))
    assert row.decision == "accepted"
    assert row.actor_type == "verified_human"
    assert row.actor_id == "alice"

    # Registry replay re-verifies every decision; must remain valid and idempotent.
    registry = harness.repository.registry.contract_registry(project_id)
    assert registry is not None


def test_replayed_challenge_is_rejected(harness: AuthorityHarness) -> None:
    project_id = harness.project()
    revision = harness.goal_revision(project_id)
    harness.repository.registry.save_contract_revision(revision, status="proposed")
    credential = harness.service.enroll(
        principal_id="alice",
        display_name="Alice",
        relying_party_id="evidrun.local",
        origin="https://evidrun.local",
    )
    subject = _subject(revision)
    challenge = harness.service.begin_confirmation(
        mode=AuthorityMode.PRIVILEGED,
        subject=subject,
        credential_id=credential.credential_id,
    )
    assertion = harness.service.sign_locally(
        credential_id=credential.credential_id, challenge=challenge
    )
    harness.service.complete_confirmation(
        subject=subject,
        credential_id=credential.credential_id,
        challenge=challenge,
        assertion=assertion,
        project_id=project_id,
    )
    with pytest.raises(ChallengeUnavailable):
        harness.service.complete_confirmation(
            subject=subject,
            credential_id=credential.credential_id,
            challenge=challenge,
            assertion=assertion,
            project_id=project_id,
        )


def test_completion_subject_must_match_the_issued_challenge(
    harness: AuthorityHarness,
) -> None:
    project_id = harness.project()
    revision = harness.goal_revision(project_id)
    harness.repository.registry.save_contract_revision(revision, status="proposed")
    credential = harness.service.enroll(
        principal_id="alice",
        display_name="Alice",
        relying_party_id="evidrun.local",
        origin="https://evidrun.local",
    )
    subject_a = RevisionDecisionSubject(
        revision_ref=revision.ref,
        decision="accepted",
        rationale="Low-stakes approval the human actually confirmed.",
    )
    subject_b = RevisionDecisionSubject(
        revision_ref=revision.ref,
        decision="rejected",
        rationale="A different decision the human never confirmed.",
    )
    challenge = harness.service.begin_confirmation(
        mode=AuthorityMode.PRIVILEGED,
        subject=subject_a,
        credential_id=credential.credential_id,
    )
    assertion = harness.service.sign_locally(
        credential_id=credential.credential_id, challenge=challenge
    )
    with pytest.raises(ChallengeUnavailable, match="confirmed intent"):
        harness.service.complete_confirmation(
            subject=subject_b,
            credential_id=credential.credential_id,
            challenge=challenge,
            assertion=assertion,
            project_id=project_id,
        )


def test_revoked_credential_cannot_confirm(harness: AuthorityHarness) -> None:
    project_id = harness.project()
    revision = harness.goal_revision(project_id)
    harness.repository.registry.save_contract_revision(revision, status="proposed")
    credential = harness.service.enroll(
        principal_id="alice",
        display_name="Alice",
        relying_party_id="evidrun.local",
        origin="https://evidrun.local",
    )
    harness.authority_repository.revoke_credential(credential.credential_id)
    with pytest.raises(CredentialUnavailable):
        harness.service.begin_confirmation(
            mode=AuthorityMode.PRIVILEGED,
            subject=_subject(revision),
            credential_id=credential.credential_id,
        )


def test_default_repository_fails_closed(tmp_path: Path) -> None:
    database = Database(tmp_path / "closed.db")
    database.create_all()
    repository = Repository(database)  # no verifier installed
    authority_repository = AuthorityRepository(database)
    artifacts = ArtifactStore(tmp_path / "artifacts", key_provider=MemoryKeyProvider())
    service = HumanAuthorityService(
        repository=authority_repository,
        authenticator=MemoryAuthenticator(),
        artifacts=artifacts,
    )
    workspace = repository.catalog.create_workspace("WS")
    project = repository.catalog.create_project(workspace.id, "Project")
    revision = GoalRevision(
        logical_id="closed-goal",
        revision=1,
        project_id=project.id,
        title="Closed goal",
        payload=GoalSpec(
            mode="goal_state",
            instruction="Produce one terminal answer.",
            outcomes=(GoalOutcome(id="answer", description="Produce a terminal answer."),),
            constraints=(
                GoalConstraint(
                    id="no-external", rule="must_not", description="Access external resources."
                ),
            ),
        ),
    )
    repository.registry.save_contract_revision(revision, status="proposed")
    credential = service.enroll(
        principal_id="alice",
        display_name="Alice",
        relying_party_id="evidrun.local",
        origin="https://evidrun.local",
    )
    subject = RevisionDecisionSubject(
        revision_ref=revision.ref,
        decision="accepted",
        rationale="Reviewed the exact revision content.",
    )
    attestation = service.confirm_with_local_authenticator(
        mode=AuthorityMode.PRIVILEGED,
        subject=subject,
        credential_id=credential.credential_id,
        project_id=project.id,
    )
    with pytest.raises(HumanAttestationUnavailable):
        repository.registry.decide_contract_revision(subject.build_decision(attestation))
    database.dispose()
