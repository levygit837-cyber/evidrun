from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from evidrun.entrypoints.api.app import create_app
from evidrun.entrypoints.cli.app import app as cli_app


def test_previous_unscoped_chat_listing_contract_is_versioned() -> None:
    fixture_path = Path(
        "tests/integration/fixtures/chat-sessions-unscoped-openapi-v1.json"
    )
    previous = json.loads(fixture_path.read_text(encoding="utf-8"))

    assert previous == {
        "method": "GET",
        "path": "/api/v1/chat/sessions",
        "query_parameters": [],
        "response_status": 200,
        "response_shape": "array",
    }


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
        session_a = client.post(
            "/api/v1/chat/sessions",
            json={"workspace_id": workspace_a["id"], "title": "Sessão A"},
        ).json()
        session_b = client.post(
            "/api/v1/chat/sessions",
            json={"workspace_id": workspace_b["id"], "title": "Sessão B"},
        ).json()

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
