from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from evidrun.contracts.lab_agent.errors import HTTP_STATUS_BY_CODE, LabAgentErrorCode
from evidrun.entrypoints.api.app import create_app
from evidrun.infrastructure.database import clock
from evidrun.infrastructure.database.models import ContractRevisionRow

ROOT = Path(__file__).resolve().parents[2]

@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    app = create_app(data_dir=tmp_path, benchmark_root=ROOT / "benchmarks")
    with TestClient(app) as built:
        yield built


def _workspace(client: TestClient, name: str) -> dict[str, Any]:
    response = client.post("/api/v1/workspaces", json={"name": name})
    assert response.status_code == 201
    return response.json()


def _project(client: TestClient, workspace_id: str, name: str) -> dict[str, Any]:
    response = client.post(
        "/api/v1/projects", json={"workspace_id": workspace_id, "name": name}
    )
    assert response.status_code == 201
    return response.json()


def _study(client: TestClient, project_id: str, study_id: str) -> str:
    with client.app.state.repository.unit_of_work.session() as session:
        session.add(
            ContractRevisionRow(
                id=study_id,
                contract_type="study",
                logical_id=study_id,
                revision=1,
                project_id=project_id,
                title="Study do foco",
                status="draft",
                document_json='{"schema_version":"1"}',
                digest="a" * 64,
                created_at=clock.utc_now(),
            )
        )
        session.commit()
    return study_id


def _create_session(client: TestClient, **payload: Any) -> dict[str, Any]:
    response = client.post("/api/v1/lab/sessions", json=payload)
    assert response.status_code == 200
    return response.json()


def test_as_tres_formas_de_sessao_sao_derivadas_do_scope(client: TestClient) -> None:
    workspace = _workspace(client, "Laboratório")
    project = _project(client, workspace["id"], "Projeto")
    study_id = _study(client, project["id"], "study_focus")

    general = _create_session(client, workspace_id=workspace["id"], title="Geral")
    project_session = _create_session(
        client,
        workspace_id=workspace["id"],
        project_id=project["id"],
        title="Projeto",
    )
    focused = _create_session(
        client,
        workspace_id=workspace["id"],
        project_id=project["id"],
        focus_kind="study",
        focus_id=study_id,
        title="Foco",
    )

    assert general["form"] == "general"
    assert project_session["form"] == "project"
    assert focused["form"] == "focused"
    assert focused == {
        "id": focused["id"],
        "workspace_id": workspace["id"],
        "project_id": project["id"],
        "focus_kind": "study",
        "focus_id": study_id,
        "form": "focused",
        "title": "Foco",
        "created_at": focused["created_at"],
    }


@pytest.mark.parametrize(
    "scope",
    [
        {"focus_kind": "study"},
        {"focus_id": "study_focus"},
        {"focus_kind": "study", "focus_id": "study_focus"},
    ],
)
def test_combinacao_invalida_de_scope_tem_codigo_estavel(
    client: TestClient, scope: dict[str, str]
) -> None:
    workspace = _workspace(client, f"Laboratório {len(scope)}")
    response = client.post(
        "/api/v1/lab/sessions",
        json={"workspace_id": workspace["id"], "title": "Inválida", **scope},
    )

    code = LabAgentErrorCode.SCHEMA_ARGUMENT_SET_INVALID
    assert response.status_code == HTTP_STATUS_BY_CODE[code]
    assert response.json()["detail"]["code"] == code.value


def test_focus_kind_fora_do_vocabulario_fechado_e_recusado(client: TestClient) -> None:
    workspace = _workspace(client, "Laboratório")
    project = _project(client, workspace["id"], "Projeto")

    response = client.post(
        "/api/v1/lab/sessions",
        json={
            "workspace_id": workspace["id"],
            "project_id": project["id"],
            "focus_kind": "experiment",
            "focus_id": "exp_1",
            "title": "Inválida",
        },
    )

    code = LabAgentErrorCode.SCHEMA_ARGUMENT_SET_INVALID
    assert response.status_code == HTTP_STATUS_BY_CODE[code]
    assert response.json()["detail"]["code"] == code.value


def test_listagem_e_isolada_por_workspace(client: TestClient) -> None:
    first_workspace = _workspace(client, "Laboratório A")
    second_workspace = _workspace(client, "Laboratório B")
    own = _create_session(client, workspace_id=first_workspace["id"], title="Própria")
    _create_session(client, workspace_id=second_workspace["id"], title="Outra")

    response = client.get(
        "/api/v1/lab/sessions", params={"workspace_id": first_workspace["id"]}
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [own["id"]]


def test_sessao_de_outro_workspace_e_inexistente_sao_indistinguiveis(
    client: TestClient,
) -> None:
    first_workspace = _workspace(client, "Laboratório A")
    second_workspace = _workspace(client, "Laboratório B")
    foreign = _create_session(client, workspace_id=second_workspace["id"], title="Outra")

    foreign_response = client.get(
        f"/api/v1/lab/sessions/{foreign['id']}",
        params={"workspace_id": first_workspace["id"]},
    )
    absent_response = client.get(
        "/api/v1/lab/sessions/chat_inexistente",
        params={"workspace_id": first_workspace["id"]},
    )
    code = LabAgentErrorCode.SCOPE_TARGET_NOT_VISIBLE

    assert (
        foreign_response.status_code
        == absent_response.status_code
        == HTTP_STATUS_BY_CODE[code]
    )
    assert foreign_response.json() == absent_response.json()
    assert foreign_response.json()["detail"]["code"] == code.value


def test_mensagem_da_api_e_humana_e_cliente_nao_forja_papel(client: TestClient) -> None:
    workspace = _workspace(client, "Laboratório")
    session = _create_session(client, workspace_id=workspace["id"], title="Geral")
    route = f"/api/v1/lab/sessions/{session['id']}/messages"

    first = client.post(
        route, json={"workspace_id": workspace["id"], "content": "Primeira"}
    )
    second = client.post(
        route, json={"workspace_id": workspace["id"], "content": "Segunda"}
    )
    forged = client.post(
        route,
        json={
            "workspace_id": workspace["id"],
            "content": "Forjada",
            "role": "agent",
        },
    )

    assert first.status_code == second.status_code == 200
    assert (first.json()["role"], first.json()["sequence"]) == ("human", 1)
    assert (second.json()["role"], second.json()["sequence"]) == ("human", 2)
    assert forged.status_code == 422


def test_transcript_e_devolvido_na_ordem_da_sequencia(client: TestClient) -> None:
    workspace = _workspace(client, "Laboratório")
    session = _create_session(client, workspace_id=workspace["id"], title="Geral")
    route = f"/api/v1/lab/sessions/{session['id']}/messages"
    for content in ("Um", "Dois", "Três"):
        assert client.post(
            route, json={"workspace_id": workspace["id"], "content": content}
        ).status_code == 200

    response = client.get(route, params={"workspace_id": workspace["id"]})

    assert response.status_code == 200
    assert [item["sequence"] for item in response.json()] == [1, 2, 3]
    assert [item["content"] for item in response.json()] == ["Um", "Dois", "Três"]
