from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy.exc import IntegrityError
from typer.testing import CliRunner, Result

import evidrun.infrastructure.database.registry as registry_module
from evidrun.contracts import GoalRevision, GoalSpec
from evidrun.contracts.authoring.goal import GoalOutcome
from evidrun.entrypoints.api.app import create_app
from evidrun.entrypoints.cli.app import app as cli_app
from evidrun.infrastructure.database import Database, Repository

SENSITIVE_VALUES = (
    "private-register-goal",
    "DO-NOT-ECHO-TITLE",
    "DO-NOT-ECHO-INSTRUCTION",
    "DO-NOT-ECHO-OUTCOME",
    "DO-NOT-ECHO-OUTCOME-ID",
)
FORBIDDEN_INFRASTRUCTURE_MARKERS = (
    "INSERT",
    "SELECT",
    "sqlite",
    "pysqlite",
    "postgresql",
    "psycopg",
    "asyncpg",
    "mysql",
    "contract_revisions",
    "projects",
)


@dataclass(frozen=True)
class RegisterErrorCase:
    name: str
    code: str
    http_status: int
    cli_exit: int
    project_exists: bool = True
    revision: int = 1
    status: str = "draft"
    existing_content: bool = False
    expected_revision: int | None = None


REGISTER_ERROR_CASES = (
    RegisterErrorCase(
        name="project-not-found",
        code="register.project_not_found",
        http_status=404,
        cli_exit=4,
        project_exists=False,
    ),
    RegisterErrorCase(
        name="revision-not-monotonic",
        code="register.revision_not_monotonic",
        http_status=409,
        cli_exit=5,
        revision=2,
        expected_revision=1,
    ),
    RegisterErrorCase(
        name="immutability-conflict",
        code="register.immutability_conflict",
        http_status=409,
        cli_exit=5,
        existing_content=True,
    ),
    RegisterErrorCase(
        name="initial-status-invalid",
        code="register.initial_status_invalid",
        http_status=422,
        cli_exit=2,
        status="accepted",
    ),
)


def _goal_document(*, project_id: str, revision: int = 1) -> dict[str, object]:
    return GoalRevision(
        logical_id=SENSITIVE_VALUES[0],
        revision=revision,
        project_id=project_id,
        title=SENSITIVE_VALUES[1],
        payload=GoalSpec(
            mode="goal_state",
            instruction=SENSITIVE_VALUES[2],
            outcomes=(
                GoalOutcome(id=SENSITIVE_VALUES[4], description=SENSITIVE_VALUES[3]),
            ),
        ),
    ).semantic_document()


def _prepare_case(data_dir: Path, case: RegisterErrorCase) -> dict[str, object]:
    database = Database(data_dir / "evidrun.db")
    database.create_all()
    repository = Repository(database)
    if case.project_exists:
        workspace = repository.catalog.create_workspace("Register workspace")
        project_id = repository.catalog.create_project(
            workspace.id, "Register project"
        ).id
    else:
        project_id = "prj-missing"
    document = _goal_document(project_id=project_id, revision=case.revision)
    if case.existing_content:
        original = GoalRevision.model_validate(document).model_copy(
            update={"title": "Original title"}
        )
        repository.registry.save_contract_revision(original)
    database.dispose()
    return document


def _invoke_api_and_cli(
    *, data_dir: Path, document_path: Path, document: dict[str, object], status: str
) -> tuple[Response, Result]:
    with TestClient(create_app(data_dir=data_dir)) as client:
        response = client.post(
            "/api/v1/contracts/revisions",
            json={"document": document, "status": status},
        )
    cli_result = CliRunner().invoke(
        cli_app,
        [
            "contract",
            "register",
            str(document_path),
            "--status",
            status,
            "--data-dir",
            str(data_dir),
        ],
    )
    return response, cli_result


def _assert_safe_error(serialized: str) -> None:
    folded = serialized.casefold()
    for marker in (*FORBIDDEN_INFRASTRUCTURE_MARKERS, *SENSITIVE_VALUES):
        assert marker.casefold() not in folded


@pytest.mark.parametrize("case", REGISTER_ERROR_CASES, ids=lambda case: case.name)
def test_register_error_matrix_is_shared_by_api_and_cli(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: RegisterErrorCase,
) -> None:
    logged_exceptions: list[BaseException | None] = []

    def capture_infrastructure_exception(*_: object, **__: object) -> None:
        logged_exceptions.append(sys.exception())

    monkeypatch.setattr(
        registry_module.logger, "exception", capture_infrastructure_exception
    )
    data_dir = tmp_path / "data"
    document = _prepare_case(data_dir, case)
    document_path = tmp_path / "goal.yaml"
    document_path.write_text(
        yaml.safe_dump(document, sort_keys=False), encoding="utf-8"
    )

    response, cli_result = _invoke_api_and_cli(
        data_dir=data_dir,
        document_path=document_path,
        document=document,
        status=case.status,
    )

    assert response.status_code == case.http_status
    api_error = response.json()["detail"]
    assert api_error["code"] == case.code
    assert cli_result.exit_code == case.cli_exit
    cli_error = json.loads(cli_result.stdout)
    assert cli_error["code"] == api_error["code"]
    if case.expected_revision is not None:
        assert api_error["field_path"] == ["revision"]
        for value in (case.expected_revision, case.revision):
            assert str(value) in api_error["message"]
            assert str(value) in cli_error["message"]
    _assert_safe_error(response.text)
    _assert_safe_error(cli_result.stdout)
    if not case.project_exists:
        assert logged_exceptions
        assert all(isinstance(exc, IntegrityError) for exc in logged_exceptions)


def test_identical_revision_is_idempotent_across_api_and_cli(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    database = Database(data_dir / "evidrun.db")
    database.create_all()
    repository = Repository(database)
    workspace = repository.catalog.create_workspace("Register workspace")
    project = repository.catalog.create_project(workspace.id, "Register project")
    revision = GoalRevision.model_validate(_goal_document(project_id=project.id))
    existing = repository.registry.save_contract_revision(revision)
    database.dispose()
    document_path = tmp_path / "goal.yaml"
    document_path.write_text(
        yaml.safe_dump(revision.semantic_document(), sort_keys=False), encoding="utf-8"
    )

    response, cli_result = _invoke_api_and_cli(
        data_dir=data_dir,
        document_path=document_path,
        document=revision.semantic_document(),
        status="draft",
    )

    assert response.status_code == 200
    assert response.json()["id"] == existing.id
    assert cli_result.exit_code == 0
    assert json.loads(cli_result.stdout)["id"] == existing.id
