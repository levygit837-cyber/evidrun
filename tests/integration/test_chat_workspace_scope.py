"""Os invariantes do ADR 0025 na superfície tipada do Lab Agent.

A rota migrou de `/chat/sessions` para `/lab/sessions` na issue #135, mas a decisão que estes
testes defendem não mudou: listar sessões exige `workspace_id` declarado, Workspace inexistente
devolve lista vazia em vez de `404`, a ordem é determinística, e CLI e API projetam o mesmo
documento. O fixture de OpenAPI continua provando que a forma global anterior não voltou.
"""

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
from evidrun.infrastructure.database.lab import LabAgentStore

ROOT = Path(__file__).resolve().parents[2]
LISTING = "/api/v1/lab/sessions"


def test_previous_unscoped_chat_listing_contract_is_rejected_by_current_openapi(
    tmp_path: Path,
) -> None:
    """A forma global anterior não existe mais em nenhuma rota de listagem de sessão.

    O fixture descreve `GET /api/v1/chat/sessions` sem parâmetro de query. Depois do cutover a
    rota antiga desapareceu, e a atual exige `workspace_id`. Provar as duas coisas juntas é o
    que impede a forma global de voltar por uma rota nova com outro nome.
    """

    fixture_path = (
        ROOT / "tests/integration/fixtures/chat-sessions-unscoped-openapi-v1.json"
    )
    previous = json.loads(fixture_path.read_text(encoding="utf-8"))
    paths = create_app(data_dir=tmp_path / "openapi-data").openapi()["paths"]

    assert previous["query_parameters"] == []
    assert previous["path"] not in paths

    operation = paths[LISTING][previous["method"].lower()]
    current_query_parameters = [
        parameter for parameter in operation["parameters"] if parameter["in"] == "query"
    ]
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


def test_sessions_are_scoped_without_dashboard_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = create_app(data_dir=tmp_path / "data")

    with TestClient(app) as client:
        workspace_a = client.post(
            "/api/v1/workspaces", json={"name": "Workspace A"}
        ).json()
        workspace_b = client.post(
            "/api/v1/workspaces", json={"name": "Workspace B"}
        ).json()
        project_a = client.post(
            "/api/v1/projects",
            json={"workspace_id": workspace_a["id"], "name": "Projeto A"},
        ).json()

        created_a = client.post(
            LISTING,
            json={
                "workspace_id": workspace_a["id"],
                "title": "Sessão A",
                "project_id": project_a["id"],
            },
        )
        assert created_a.status_code == 200
        session_a = created_a.json()
        assert session_a == {
            "id": session_a["id"],
            "workspace_id": workspace_a["id"],
            "project_id": project_a["id"],
            "focus_kind": None,
            "focus_id": None,
            "form": "project",
            "title": "Sessão A",
            "created_at": session_a["created_at"],
        }

        created_b = client.post(
            LISTING, json={"workspace_id": workspace_b["id"], "title": "Sessão B"}
        )
        assert created_b.status_code == 200
        session_b = created_b.json()
        assert session_b["form"] == "general"
        assert (session_b["project_id"], session_b["focus_kind"]) == (None, None)

        dashboard = client.get("/api/v1/dashboard")
        assert dashboard.status_code == 200
        assert "chats" not in dashboard.json()

        # A listagem consulta as sessões diretamente. Derivá-la do dashboard reintroduziria a
        # leitura global que o ADR 0025 recusa, então ler o dashboard aqui é um defeito.
        monkeypatch.setattr(
            app.state.repository.read_model,
            "latest_dashboard",
            lambda: (_ for _ in ()).throw(AssertionError("dashboard must not be read")),
        )

        listed_a = client.get(LISTING, params={"workspace_id": workspace_a["id"]})
        assert listed_a.status_code == 200
        assert [item["id"] for item in listed_a.json()] == [session_a["id"]]

        listed_b = client.get(LISTING, params={"workspace_id": workspace_b["id"]})
        assert listed_b.status_code == 200
        assert [item["id"] for item in listed_b.json()] == [session_b["id"]]
        assert session_a["id"] not in {item["id"] for item in listed_b.json()}

        assert client.get(LISTING).status_code == 422

        # Workspace inexistente devolve vazio, igual a Workspace existente sem sessões. Um
        # `404` transformaria a rota de conteúdo em oráculo de existência de Workspace.
        missing_workspace = client.get(LISTING, params={"workspace_id": "ws_missing"})
        assert missing_workspace.status_code == 200
        assert missing_workspace.json() == []

        message = client.post(
            f"{LISTING}/{session_a['id']}/messages",
            json={"workspace_id": workspace_a["id"], "content": "Mensagem preservada"},
        )
        assert message.status_code == 200
        assert message.json()["role"] == "human"
        assert message.json()["content"] == "Mensagem preservada"


def test_sessions_use_deterministic_created_at_and_id_order(
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
                LISTING, json={"workspace_id": workspace["id"], "title": title}
            ).json()
            for title in ("Antiga", "Empate B", "Empate A")
        ]
        response = client.get(LISTING, params={"workspace_id": workspace["id"]})

    assert response.status_code == 200
    # Mais recente primeiro; `id` ascendente desempata timestamps iguais, para que o resultado
    # seja reproduzível sem depender da ordem de inserção.
    newest_tie = sorted((sessions[1]["id"], sessions[2]["id"]))
    assert [item["id"] for item in response.json()] == [*newest_tie, sessions[0]["id"]]


def test_storage_failure_maps_to_http_503_and_cli_3(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Falha de driver é indisponibilidade, não fronteira errada.

    Se a listagem traduzisse o erro de storage para uma recusa de escopo, o caller concluiria
    que o Workspace não existe e pararia de tentar. O detalhe do driver também não pode
    aparecer na resposta: ele descreve o schema interno.
    """

    app = create_app(data_dir=tmp_path / "api-storage-data")
    session = app.state.repository.unit_of_work.database.session()

    def fail_scalars(*_args: object, **_kwargs: object) -> None:
        raise SQLAlchemyError("SELECT secret_chat_path: driver detail")

    monkeypatch.setattr(session, "scalars", fail_scalars)
    monkeypatch.setattr(
        app.state.repository.unit_of_work.database, "session", lambda: session
    )
    with TestClient(app) as client:
        response = client.get(LISTING, params={"workspace_id": "ws_unavailable"})

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "scope.storage_unavailable"
    assert "SELECT" not in response.text
    assert "secret_chat_path" not in response.text

    cli_session = app.state.repository.unit_of_work.database.session_factory()
    monkeypatch.setattr(cli_session, "scalars", fail_scalars)
    fake_database = SimpleNamespace(dispose=lambda: None)
    fake_unit_of_work = SimpleNamespace(session=lambda: cli_session)
    fake_repository = SimpleNamespace(lab=LabAgentStore(fake_unit_of_work))
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


def test_list_cli_matches_workspace_scoped_api(tmp_path: Path) -> None:
    """CLI e API devolvem o documento idêntico, porque a projeção é uma só.

    Duas projeções divergiriam no primeiro campo novo, e a CLI passaria a afirmar uma forma de
    sessão que a API não reconhece.
    """

    data_dir = tmp_path / "data"
    app = create_app(data_dir=data_dir)

    with TestClient(app) as client:
        workspace = client.post(
            "/api/v1/workspaces", json={"name": "Workspace CLI"}
        ).json()
        client.post(LISTING, json={"workspace_id": workspace["id"], "title": "Sessão CLI"})
        api_list = client.get(LISTING, params={"workspace_id": workspace["id"]})
        assert api_list.status_code == 200

    cli_list = CliRunner().invoke(
        cli_app,
        ["chat", "list", "--workspace-id", workspace["id"], "--data-dir", str(data_dir)],
    )
    assert cli_list.exit_code == 0, cli_list.output
    assert json.loads(cli_list.stdout) == api_list.json()

    missing_workspace = CliRunner().invoke(
        cli_app, ["chat", "list", "--data-dir", str(data_dir)]
    )
    assert missing_workspace.exit_code == 2
