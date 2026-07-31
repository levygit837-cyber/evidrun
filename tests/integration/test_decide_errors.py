"""Decide-phase refusals: every one names itself and persists nothing.

The four conditions this phase can refuse are human authority unavailable, an unknown
revision, a conflicting previous decision, and the repository-fixture path used outside
the dedicated legacy import. Fail-closed behaviour is asserted alongside each code:
naming a refusal must never promote an authority capability.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from evidrun.contracts import GoalRevision, GoalSpec, RevisionDecisionRecord
from evidrun.contracts.authoring.goal import GoalOutcome
from evidrun.contracts.base import RepositoryFixtureDecisionAuthority
from evidrun.contracts.triage import TriageErrorCode, TriageRejected
from evidrun.entrypoints.api.app import create_app
from evidrun.entrypoints.cli.app import app as cli_app
from evidrun.infrastructure.database import Database, Repository
from evidrun.shared.types import sha256_json, utc_now
from tests.support.human_attestation import (
    TestHumanAttestationVerifier,
    accepted_decision,
    decision_for,
)


def _goal(project_id: str, logical_id: str = "decide-goal") -> GoalRevision:
    return GoalRevision(
        logical_id=logical_id,
        revision=1,
        project_id=project_id,
        title="Decide phase goal",
        payload=GoalSpec(
            mode="goal_state",
            instruction="Produce one auditable answer.",
            outcomes=(GoalOutcome(id="answer", description="An answer exists."),),
        ),
    )


def _repository(tmp_path: Path, *, verified: bool) -> tuple[Database, Repository]:
    database = Database(tmp_path / "decide.db")
    database.create_all()
    verifier = TestHumanAttestationVerifier() if verified else None
    return database, Repository(database, human_attestation_verifier=verifier)


def test_a_fixture_authority_never_decides_outside_the_legacy_import(
    tmp_path: Path,
) -> None:
    database, repository = _repository(tmp_path, verified=True)
    try:
        workspace = repository.catalog.create_workspace("Decide workspace")
        project = repository.catalog.create_project(workspace.id, "Decide project")
        revision = _goal(project.id)
        row = repository.registry.save_contract_revision(revision, status="proposed")
        fixture_decision = RevisionDecisionRecord(
            revision_ref=revision.ref,
            decision="accepted",
            authority=RepositoryFixtureDecisionAuthority(
                fixture_digest=sha256_json(revision.ref.model_dump(mode="json")),
            ),
            rationale="A fixture is not human authority.",
            decided_at_utc=utc_now(),
        )

        with pytest.raises(TriageRejected) as forbidden:
            repository.registry.decide_contract_revision(fixture_decision)

        assert (
            forbidden.value.error.code
            == TriageErrorCode.DECIDE_REPOSITORY_FIXTURE_FORBIDDEN
        )
        stored = repository.read_model.list_contract_revisions()
        assert next(item for item in stored if item["id"] == row.id)["status"] == "proposed"
    finally:
        database.dispose()


def test_a_conflicting_second_decision_is_refused_by_name(tmp_path: Path) -> None:
    database, repository = _repository(tmp_path, verified=True)
    try:
        workspace = repository.catalog.create_workspace("Conflict workspace")
        project = repository.catalog.create_project(workspace.id, "Conflict project")
        revision = _goal(project.id, logical_id="decide-conflict-goal")
        row = repository.registry.save_contract_revision(revision, status="proposed")
        repository.registry.decide_contract_revision(accepted_decision(revision))

        rejected = decision_for(revision, decision="rejected")
        with pytest.raises(TriageRejected) as conflict:
            repository.registry.decide_contract_revision(rejected)

        assert conflict.value.error.code == TriageErrorCode.DECIDE_DECISION_CONFLICT
        stored = repository.read_model.list_contract_revisions()
        assert next(item for item in stored if item["id"] == row.id)["status"] == "accepted"
    finally:
        database.dispose()


def test_an_unknown_revision_is_refused_before_any_authority_check(
    tmp_path: Path,
) -> None:
    """`not_found` precedes authority: an absent revision never reaches the verifier."""

    database, repository = _repository(tmp_path, verified=False)
    try:
        workspace = repository.catalog.create_workspace("Absent workspace")
        project = repository.catalog.create_project(workspace.id, "Absent project")
        unregistered = _goal(project.id, logical_id="never-registered-goal")

        with pytest.raises(TriageRejected) as absent:
            repository.registry.decide_contract_revision(
                accepted_decision(unregistered)
            )

        assert absent.value.error.code == TriageErrorCode.DECIDE_REVISION_NOT_FOUND
    finally:
        database.dispose()


def test_the_legacy_decide_route_answers_not_found_before_unavailable(
    tmp_path: Path,
) -> None:
    application = create_app(data_dir=tmp_path)
    with TestClient(application) as client:
        absent = client.post(
            "/api/v1/contracts/revisions/contract-absent/decisions",
            json={"decision": "accepted", "rationale": "No such revision exists."},
        )

    assert absent.status_code == 404
    assert absent.json()["detail"]["code"] == "decide.revision_not_found"
    application.state.repository.database.dispose()


def test_api_and_cli_agree_that_an_absent_revision_is_not_found(tmp_path: Path) -> None:
    """Both borders name the same refusal before any authority ceremony starts."""

    application = create_app(data_dir=tmp_path)
    with TestClient(application) as client:
        response = client.post(
            "/api/v1/contracts/revisions/contract-absent/decisions",
            json={"decision": "accepted", "rationale": "No such revision exists."},
        )

    result = CliRunner().invoke(
        cli_app,
        [
            "authority",
            "accept",
            "contract-absent",
            "--credential-id",
            "hcred-absent",
            "--reason",
            "No such revision exists.",
            "--data-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 4
    assert "Traceback" not in result.output
    assert json.loads(result.stdout) == response.json()["detail"]
    application.state.repository.database.dispose()
