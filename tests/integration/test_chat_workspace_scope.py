from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from typer.testing import CliRunner

from evidrun.entrypoints.api.app import create_app
from evidrun.entrypoints.cli.app import app as cli_app
from evidrun.entrypoints.cli.commands import runs as run_commands
from evidrun.infrastructure.database import clock as database_clock
from evidrun.infrastructure.database.read_model.queries import ReadModel

ROOT = Path(__file__).resolve().parents[2]


def test_previous_unscoped_chat_listing_contract_is_rejected_by_current_openapi(
    tmp_path: Path,
) -> None:
    fixture_path = (
        ROOT / "tests/integration/fixtures/chat-sessions-unscoped-openapi-v1.json"
    )
    previous = json.loads(fixture_path.read_text(encoding="utf-8"))
    operation = create_app(data_dir=tmp_path / "openapi-data").openapi()["paths"][
        previous["path"]
    ][previous["method"].lower()]
    current_query_parameters = [
        parameter
        for parameter in operation["parameters"]
        if parameter["in"] == "query"
    ]

    assert previous["query_parameters"] == []
    assert current_query_parameters == [
        {
            "name": "workspace_id",
            "in": "query",
            "required": True,
            "schema": {"type": "string", "title": "Workspace Id"},
        }
    ]
    assert current_query_parameters != previous["query_parameters"]
    assert str(previous["response_status"]) in operation["responses"]
    current_response_schema = operation["responses"][str(previous["response_status"])][
        "content"
    ]["application/json"]["schema"]
    assert current_response_schema["type"] == previous["response_shape"]


def test_chat_sessions_are_scoped_without_dashboard_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data_dir = tmp_path / "data"
    app = create_app(data_dir=data_dir)

    with TestClient(app) as client:
        workspace_a = client.post(
            "/api/v1/workspaces", json={"name": "Workspace A"}
        ).json()
        workspace_b = client.post(
            "/api/v1/workspaces", json={"name": "Workspace B"}
        ).json()
        created_a = client.post(
            "/api/v1/chat/sessions",
            json={
                "workspace_id": workspace_a["id"],
                "title": "Sessão A",
                "scope_type": "workspace",
                "scope_id": workspace_a["id"],
            },
        )
        assert created_a.status_code == 200
        session_a = created_a.json()
        assert session_a == {
            "id": session_a["id"],
            "workspace_id": workspace_a["id"],
            "scope_type": "workspace",
            "scope_id": workspace_a["id"],
            "title": "Sessão A",
        }

        created_b = client.post(
            "/api/v1/chat/sessions",
            json={"workspace_id": workspace_b["id"], "title": "Sessão B"},
        )
        assert created_b.status_code == 200
        session_b = created_b.json()
        assert session_b == {
            "id": session_b["id"],
            "workspace_id": workspace_b["id"],
            "scope_type": None,
            "scope_id": None,
            "title": "Sessão B",
        }

        dashboard = client.get("/api/v1/dashboard")
        assert dashboard.status_code == 200
        assert "chats" not in dashboard.json()

        monkeypatch.setattr(
            app.state.repository.read_model,
            "latest_dashboard",
            lambda: (_ for _ in ()).throw(AssertionError("dashboard must not be read")),
        )

        listed_a = client.get(
            "/api/v1/chat/sessions", params={"workspace_id": workspace_a["id"]}
        )
        assert listed_a.status_code == 200
        assert [item["id"] for item in listed_a.json()] == [session_a["id"]]
        assert listed_a.json()[0]["workspace_id"] == workspace_a["id"]

        listed_b = client.get(
            "/api/v1/chat/sessions", params={"workspace_id": workspace_b["id"]}
        )
        assert listed_b.status_code == 200
        assert [item["id"] for item in listed_b.json()] == [session_b["id"]]
        assert session_a["id"] not in {item["id"] for item in listed_b.json()}

        missing_parameter = client.get("/api/v1/chat/sessions")
        assert missing_parameter.status_code == 422

        missing_workspace = client.get(
            "/api/v1/chat/sessions", params={"workspace_id": "ws_missing"}
        )
        assert missing_workspace.status_code == 200
        assert missing_workspace.json() == []

        message = client.post(
            f"/api/v1/chat/sessions/{session_a['id']}/messages",
            json={"role": "human", "content": "Mensagem preservada"},
        )
        assert message.status_code == 200
        assert message.json() == {
            "id": message.json()["id"],
            "session_id": session_a["id"],
            "role": "human",
            "content": "Mensagem preservada",
        }


def test_chat_sessions_use_deterministic_created_at_and_id_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = create_app(data_dir=tmp_path / "ordered-data")
    timestamps = iter(
        [
            datetime(2026, 1, 1, tzinfo=UTC),
            datetime(2025, 1, 1, tzinfo=UTC),
            datetime(2026, 2, 1, tzinfo=UTC),
            datetime(2026, 2, 1, tzinfo=UTC),
        ]
    )
    monkeypatch.setattr(database_clock, "utc_now", lambda: next(timestamps))

    with TestClient(app) as client:
        workspace = client.post(
            "/api/v1/workspaces", json={"name": "Workspace ordenado"}
        ).json()
        sessions = [
            client.post(
                "/api/v1/chat/sessions",
                json={"workspace_id": workspace["id"], "title": title},
            ).json()
            for title in ("Antiga", "Empate B", "Empate A")
        ]
        response = client.get(
            "/api/v1/chat/sessions", params={"workspace_id": workspace["id"]}
        )

    assert response.status_code == 200
    newest_tie = sorted((sessions[1]["id"], sessions[2]["id"]))
    assert [item["id"] for item in response.json()] == [*newest_tie, sessions[0]["id"]]


def test_chat_storage_failure_maps_to_http_503_and_cli_3(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = create_app(data_dir=tmp_path / "api-storage-data")
    session = app.state.repository.unit_of_work.database.session()

    def fail_scalars(*_args: object, **_kwargs: object) -> None:
        raise SQLAlchemyError("SELECT secret_chat_path: driver detail")

    monkeypatch.setattr(session, "scalars", fail_scalars)
    monkeypatch.setattr(
        app.state.repository.unit_of_work.database, "session", lambda: session
    )
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/chat/sessions", params={"workspace_id": "ws_unavailable"}
        )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "scope.storage_unavailable"
    assert "SELECT" not in response.text
    assert "secret_chat_path" not in response.text

    cli_session = app.state.repository.unit_of_work.database.session_factory()
    monkeypatch.setattr(cli_session, "scalars", fail_scalars)
    fake_database = SimpleNamespace(dispose=lambda: None)
    fake_unit_of_work = SimpleNamespace(session=lambda: cli_session)
    fake_read_model = ReadModel(fake_unit_of_work)
    fake_repository = SimpleNamespace(read_model=fake_read_model)
    monkeypatch.setattr(
        run_commands,
        "components",
        lambda _data_dir: (SimpleNamespace(), fake_database, fake_repository),
    )
    result = CliRunner().invoke(
        cli_app,
        [
            "chat",
            "list",
            "--workspace-id",
            "ws_unavailable",
            "--data-dir",
            str(tmp_path / "cli-storage-data"),
        ],
    )

    assert result.exit_code == 3
    assert json.loads(result.stdout)["code"] == "scope.storage_unavailable"
    assert "SELECT" not in result.stdout
    assert "secret_chat_path" not in result.stdout


def test_chat_list_cli_matches_workspace_scoped_api(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    app = create_app(data_dir=data_dir)

    with TestClient(app) as client:
        workspace = client.post(
            "/api/v1/workspaces", json={"name": "Workspace CLI"}
        ).json()
        client.post(
            "/api/v1/chat/sessions",
            json={"workspace_id": workspace["id"], "title": "Sessão CLI"},
        )
        api_list = client.get(
            "/api/v1/chat/sessions", params={"workspace_id": workspace["id"]}
        )
        assert api_list.status_code == 200

    cli_list = CliRunner().invoke(
        cli_app,
        [
            "chat",
            "list",
            "--workspace-id",
            workspace["id"],
            "--data-dir",
            str(data_dir),
        ],
    )
    assert cli_list.exit_code == 0, cli_list.output
    assert json.loads(cli_list.stdout) == api_list.json()

    missing_workspace = CliRunner().invoke(
        cli_app, ["chat", "list", "--data-dir", str(data_dir)]
    )
    assert missing_workspace.exit_code == 2
