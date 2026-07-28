from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace

import pytest
import yaml
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from typer.testing import CliRunner

from evidrun.contracts import GoalRevision, GoalSpec
from evidrun.contracts.authoring.goal import GoalOutcome
from evidrun.contracts.scope import ScopeErrorCode
from evidrun.entrypoints.api.app import create_app
from evidrun.entrypoints.cli.app import app as cli_app
from evidrun.entrypoints.cli.commands import scopes as scope_commands
from evidrun.infrastructure.database import Database, Repository
from evidrun.infrastructure.database.scope_errors import (
    ScopeRejected,
    ScopeStorageUnavailable,
)


def test_workspace_api_cli_parity_normalization_and_conflicts(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    app = create_app(data_dir=data_dir)
    runner = CliRunner()

    with TestClient(app) as client:
        created = client.post(
            "/api/v1/workspaces", json={"name": "  \uff2cab\t Principal "}
        )
        assert created.status_code == 201
        document = created.json()
        assert set(document) == {"id", "name", "created_at"}
        assert document["name"] == "Lab Principal"

        api_list = client.get("/api/v1/workspaces")
        assert api_list.status_code == 200
        assert api_list.json() == [document]

        conflict = client.post("/api/v1/workspaces", json={"name": "lab   principal"})
        assert conflict.status_code == 409
        assert conflict.json()["detail"]["code"] == "workspace.name_conflict"

        invalid = client.post("/api/v1/workspaces", json={"name": " \t "})
        assert invalid.status_code == 422
        assert invalid.json()["detail"]["code"] == "workspace.name_invalid"

        undeclared = client.post(
            "/api/v1/workspaces",
            json={"name": "No side effect", "authority": "human", "sandbox": True},
        )
        assert undeclared.status_code == 422
        assert client.get("/api/v1/workspaces").json() == [document]

    listed = runner.invoke(
        cli_app, ["workspace", "list", "--data-dir", str(data_dir)]
    )
    assert listed.exit_code == 0, listed.output
    assert json.loads(listed.stdout) == [document]

    cli_conflict = runner.invoke(
        cli_app,
        ["workspace", "create", "LAB PRINCIPAL", "--data-dir", str(data_dir)],
    )
    assert cli_conflict.exit_code == 5
    assert json.loads(cli_conflict.stdout)["code"] == "workspace.name_conflict"

    cli_invalid = runner.invoke(
        cli_app, ["workspace", "create", " ", "--data-dir", str(data_dir)]
    )
    assert cli_invalid.exit_code == 2
    assert json.loads(cli_invalid.stdout)["code"] == "workspace.name_invalid"


def test_project_api_cli_parity_scoping_and_direct_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data_dir = tmp_path / "data"
    app = create_app(data_dir=data_dir)
    runner = CliRunner()

    with TestClient(app) as client:
        first_workspace = client.post(
            "/api/v1/workspaces", json={"name": "Workspace A"}
        ).json()
        second_workspace = client.post(
            "/api/v1/workspaces", json={"name": "Workspace B"}
        ).json()
        first_project = client.post(
            "/api/v1/projects",
            json={"workspace_id": first_workspace["id"], "name": " \uff23ontexto\tLongo "},
        )
        assert first_project.status_code == 201
        project_document = first_project.json()
        assert set(project_document) == {"id", "workspace_id", "name", "created_at"}
        assert project_document["name"] == "Contexto Longo"

        conflict = client.post(
            "/api/v1/projects",
            json={"workspace_id": first_workspace["id"], "name": "contexto  longo"},
        )
        assert conflict.status_code == 409
        assert conflict.json()["detail"]["code"] == "project.name_conflict"

        invalid = client.post(
            "/api/v1/projects",
            json={"workspace_id": first_workspace["id"], "name": " \t "},
        )
        assert invalid.status_code == 422
        assert invalid.json()["detail"]["code"] == "project.name_invalid"

        undeclared = client.post(
            "/api/v1/projects",
            json={
                "workspace_id": first_workspace["id"],
                "name": "No side effect",
                "lab_agent": {"create": True},
            },
        )
        assert undeclared.status_code == 422

        homonym = client.post(
            "/api/v1/projects",
            json={"workspace_id": second_workspace["id"], "name": "CONTEXTO LONGO"},
        )
        assert homonym.status_code == 201
        assert homonym.json()["id"] != project_document["id"]

        missing_parent = client.post(
            "/api/v1/projects", json={"workspace_id": "ws_missing", "name": "Project"}
        )
        assert missing_parent.status_code == 404
        assert missing_parent.json()["detail"]["code"] == "project.workspace_not_found"

        filtered = client.get(
            "/api/v1/projects", params={"workspace_id": first_workspace["id"]}
        )
        assert filtered.status_code == 200
        assert filtered.json() == [project_document]

        monkeypatch.setattr(
            app.state.repository.read_model,
            "latest_dashboard",
            lambda: (_ for _ in ()).throw(AssertionError("dashboard must not be read")),
        )
        assert client.get("/api/v1/workspaces").status_code == 200
        assert client.get("/api/v1/projects").status_code == 200

        missing_filter = client.get(
            "/api/v1/projects", params={"workspace_id": "ws_missing"}
        )
        assert missing_filter.status_code == 404
        assert missing_filter.json()["detail"]["code"] == "project.workspace_not_found"

    cli_list = runner.invoke(
        cli_app,
        [
            "project",
            "list",
            "--workspace-id",
            first_workspace["id"],
            "--data-dir",
            str(data_dir),
        ],
    )
    assert cli_list.exit_code == 0, cli_list.output
    assert json.loads(cli_list.stdout) == [project_document]

    cli_conflict = runner.invoke(
        cli_app,
        [
            "project",
            "create",
            first_workspace["id"],
            "CONTEXTO LONGO",
            "--data-dir",
            str(data_dir),
        ],
    )
    assert cli_conflict.exit_code == 5
    assert json.loads(cli_conflict.stdout)["code"] == "project.name_conflict"

    cli_invalid = runner.invoke(
        cli_app,
        [
            "project",
            "create",
            first_workspace["id"],
            " ",
            "--data-dir",
            str(data_dir),
        ],
    )
    assert cli_invalid.exit_code == 2
    assert json.loads(cli_invalid.stdout)["code"] == "project.name_invalid"

    cli_missing = runner.invoke(
        cli_app,
        [
            "project",
            "list",
            "--workspace-id",
            "ws_missing",
            "--data-dir",
            str(data_dir),
        ],
    )
    assert cli_missing.exit_code == 4
    assert json.loads(cli_missing.stdout)["code"] == "project.workspace_not_found"


def test_concurrent_equivalent_scope_creations_are_one_success_one_conflict(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "race.db")
    database.create_all()
    repository = Repository(database)
    workspace_barrier = Barrier(2)

    def create_workspace(name: str) -> str:
        workspace_barrier.wait()
        try:
            return repository.catalog.create_workspace(name).id
        except ScopeRejected as exc:
            return exc.error.code.value

    with ThreadPoolExecutor(max_workers=2) as pool:
        workspace_results = list(
            pool.map(create_workspace, ("\uff32ace Name", "race name"))
        )

    assert workspace_results.count("workspace.name_conflict") == 1
    workspace_id = next(item for item in workspace_results if item != "workspace.name_conflict")
    project_barrier = Barrier(2)

    def create_project(name: str) -> str:
        project_barrier.wait()
        try:
            return repository.catalog.create_project(workspace_id, name).id
        except ScopeRejected as exc:
            return exc.error.code.value

    with ThreadPoolExecutor(max_workers=2) as pool:
        project_results = list(pool.map(create_project, ("\uff30roject", "project")))

    assert project_results.count("project.name_conflict") == 1
    assert len(repository.read_model.list_workspaces()) == 1
    assert len(repository.read_model.list_projects(workspace_id)) == 1
    database.dispose()


def test_unclassified_storage_failure_is_safe_and_typed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = Database(tmp_path / "storage.db")
    database.create_all()
    repository = Repository(database)
    session = database.session()

    def fail_commit() -> None:
        raise OperationalError(
            "INSERT INTO workspaces secret_database_path", {}, RuntimeError("driver detail")
        )

    monkeypatch.setattr(session, "commit", fail_commit)
    monkeypatch.setattr(database, "session", lambda: session)

    with pytest.raises(ScopeStorageUnavailable) as raised:
        repository.catalog.create_workspace("Storage failure")

    payload = raised.value.error.model_dump_json()
    assert raised.value.error.code is ScopeErrorCode.STORAGE_UNAVAILABLE
    assert "INSERT" not in payload
    assert "secret_database_path" not in payload
    assert "driver" not in payload
    database.dispose()


def test_storage_unavailable_maps_to_http_503_and_cli_3(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = create_app(data_dir=tmp_path / "api-data")
    with TestClient(app) as client:
        monkeypatch.setattr(
            app.state.repository.catalog,
            "create_workspace",
            lambda _name: (_ for _ in ()).throw(ScopeStorageUnavailable()),
        )
        response = client.post("/api/v1/workspaces", json={"name": "Unavailable"})
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "scope.storage_unavailable"
        assert "SQL" not in response.text

    fake_database = SimpleNamespace(dispose=lambda: None)
    fake_catalog = SimpleNamespace(
        create_workspace=lambda _name: (_ for _ in ()).throw(ScopeStorageUnavailable())
    )
    fake_repository = SimpleNamespace(catalog=fake_catalog)
    monkeypatch.setattr(
        scope_commands,
        "components",
        lambda _data_dir: (SimpleNamespace(), fake_database, fake_repository),
    )
    result = CliRunner().invoke(
        cli_app,
        ["workspace", "create", "Unavailable", "--data-dir", str(tmp_path / "cli-data")],
    )
    assert result.exit_code == 3
    assert json.loads(result.stdout)["code"] == "scope.storage_unavailable"
    assert "SQL" not in result.stdout


def _goal_document(project_id: str, logical_id: str) -> GoalRevision:
    return GoalRevision(
        logical_id=logical_id,
        revision=1,
        project_id=project_id,
        title="First public contract",
        payload=GoalSpec(
            mode="goal_state",
            instruction="Produce one auditable response.",
            outcomes=(GoalOutcome(id="response", description="A response exists."),),
        ),
    )


def test_empty_database_reaches_first_contract_through_api_and_cli(tmp_path: Path) -> None:
    api_data = tmp_path / "api-data"
    app = create_app(data_dir=api_data)
    with TestClient(app) as client:
        workspace = client.post("/api/v1/workspaces", json={"name": "API Workspace"}).json()
        project = client.post(
            "/api/v1/projects",
            json={"workspace_id": workspace["id"], "name": "API Project"},
        ).json()
        revision = _goal_document(project["id"], "api-first-goal")
        registered = client.post(
            "/api/v1/contracts/revisions",
            json={"document": revision.semantic_document(), "status": "proposed"},
        )
        assert registered.status_code == 200
        assert registered.json()["digest"] == revision.digest

        missing_revision = _goal_document("prj_missing", "api-missing-project")
        missing = client.post(
            "/api/v1/contracts/revisions",
            json={"document": missing_revision.semantic_document(), "status": "proposed"},
        )
        assert missing.status_code == 404
        assert missing.json()["detail"]["code"] == "register.project_not_found"
        assert "SQL" not in missing.text

    cli_data = tmp_path / "cli-data"
    runner = CliRunner()
    workspace_result = runner.invoke(
        cli_app,
        ["workspace", "create", "CLI Workspace", "--data-dir", str(cli_data)],
    )
    assert workspace_result.exit_code == 0, workspace_result.output
    workspace = json.loads(workspace_result.stdout)
    project_result = runner.invoke(
        cli_app,
        [
            "project",
            "create",
            workspace["id"],
            "CLI Project",
            "--data-dir",
            str(cli_data),
        ],
    )
    assert project_result.exit_code == 0, project_result.output
    project = json.loads(project_result.stdout)
    revision = _goal_document(project["id"], "cli-first-goal")
    document_path = tmp_path / "first-goal.yaml"
    document_path.write_text(
        yaml.safe_dump(revision.semantic_document(), sort_keys=False), encoding="utf-8"
    )
    registered = runner.invoke(
        cli_app,
        [
            "contract",
            "register",
            str(document_path),
            "--status",
            "proposed",
            "--data-dir",
            str(cli_data),
        ],
    )
    assert registered.exit_code == 0, registered.output
    assert json.loads(registered.stdout)["digest"] == revision.digest
