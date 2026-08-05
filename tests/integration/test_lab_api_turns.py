from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from evidrun.entrypoints.api.app import create_app
from evidrun.infrastructure.providers import ProviderRequestError
from evidrun.lab.session import LabAgentSessionService
from evidrun.lab.tools.registry import AdmissionCapabilityCatalog


class FakeProvider:
    def __init__(self, responses: list[Mapping[str, Any] | Exception]) -> None:
        self.responses = responses
        self.requests: list[Mapping[str, Any]] = []

    async def invoke(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        self.requests.append(request)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _answer(text: str = "Resposta final.") -> Mapping[str, Any]:
    return {"id": "resp_answer", "output_text": text, "output": []}


def _call(name: str, arguments: Mapping[str, Any], call_id: str = "call_1") -> Mapping[str, Any]:
    return {
        "id": f"resp_{call_id}",
        "output": [
            {
                "type": "function_call",
                "call_id": call_id,
                "name": name,
                "arguments": json.dumps(arguments),
            }
        ],
    }


def _install_provider(app: Any, provider: FakeProvider) -> None:
    app.state.lab_agent._provider = provider


def _session(client: TestClient, *, workspace_id: str, project_id: str | None = None) -> str:
    response = client.post(
        "/api/v1/lab/sessions",
        json={"workspace_id": workspace_id, "project_id": project_id, "title": "Turno"},
    )
    assert response.status_code == 200
    return str(response.json()["id"])


def _frames(response: Any) -> list[dict[str, Any]]:
    frames: list[dict[str, Any]] = []
    for block in response.text.strip().split("\n\n"):
        lines = block.splitlines()
        assert lines[0].startswith("event: ")
        payload = json.loads(lines[1].removeprefix("data: "))
        assert lines[0] == f"event: {payload['type']}"
        frames.append(payload)
    return frames


def test_stream_expoe_inicio_e_fim_da_mesma_leitura(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path)
    provider = FakeProvider([_call("list_projects", {}), _answer("Encontrei o Project.")])
    _install_provider(app, provider)

    with TestClient(app) as client:
        workspace = client.post("/api/v1/workspaces", json={"name": "Workspace"}).json()
        client.post(
            "/api/v1/projects",
            json={"workspace_id": workspace["id"], "name": "Project"},
        )
        session_id = _session(client, workspace_id=workspace["id"])
        response = client.post(
            f"/api/v1/lab/sessions/{session_id}/turns",
            json={"workspace_id": workspace["id"], "content": "Liste os Projects."},
        )

    assert response.status_code == 200
    events = _frames(response)
    tools = [event for event in events if event["type"] == "tool"]
    assert tools[0] == {
        "type": "tool",
        "source": "live",
        "id": "call_1",
        "name": "list_projects",
        "status": "running",
        "argumentsSummary": "{}",
    }
    assert tools[1]["id"] == tools[0]["id"]
    assert tools[1]["status"] == "completed"


def test_turno_sem_tool_persiste_resposta_do_agente(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path)
    _install_provider(app, FakeProvider([_answer("Resposta persistida.")]))

    with TestClient(app) as client:
        workspace = client.post("/api/v1/workspaces", json={"name": "Workspace"}).json()
        session_id = _session(client, workspace_id=workspace["id"])
        response = client.post(
            f"/api/v1/lab/sessions/{session_id}/turns",
            json={"workspace_id": workspace["id"], "content": "Responda."},
        )
        messages = client.get(
            f"/api/v1/lab/sessions/{session_id}/messages",
            params={"workspace_id": workspace["id"]},
        ).json()

    events = _frames(response)
    assert [(event["type"], event.get("label")) for event in events] == [
        ("status", "working"),
        ("message", None),
        ("status", "answered"),
        ("done", None),
    ]
    assert [(item["role"], item["content"]) for item in messages] == [
        ("human", "Responda."),
        ("agent", "Resposta persistida."),
    ]


def test_falha_do_provider_e_sanitizada_no_stream(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path)
    _install_provider(
        app,
        FakeProvider(
            [ProviderRequestError("https://provider.invalid: segredo RuntimeError")]
        ),
    )

    with TestClient(app) as client:
        workspace = client.post("/api/v1/workspaces", json={"name": "Workspace"}).json()
        session_id = _session(client, workspace_id=workspace["id"])
        response = client.post(
            f"/api/v1/lab/sessions/{session_id}/turns",
            json={"workspace_id": workspace["id"], "content": "Responda."},
        )

    events = _frames(response)
    assert [event["type"] for event in events] == ["status", "error", "status", "done"]
    assert events[1]["message"] == "O provider não devolveu uma resposta utilizável."
    assert events[2]["label"] == "provider_failed"
    assert "provider.invalid" not in response.text
    assert "RuntimeError" not in response.text
    assert "segredo" not in response.text


def test_recusa_terminal_carrega_codigo_e_remediacao(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path)
    rejected = _call("list_runs", {"limit": 1, "status": None})
    _install_provider(app, FakeProvider([rejected, rejected]))

    with TestClient(app) as client:
        workspace = client.post("/api/v1/workspaces", json={"name": "Workspace"}).json()
        session_id = _session(client, workspace_id=workspace["id"])
        response = client.post(
            f"/api/v1/lab/sessions/{session_id}/turns",
            json={"workspace_id": workspace["id"], "content": "Liste runs."},
        )

    events = _frames(response)
    error = next(event for event in events if event["type"] == "error")
    assert error["code"] == "catalog.tool_not_offered"
    assert error["remediation"]


def test_sessao_de_outro_workspace_falha_antes_do_stream(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path)
    _install_provider(app, FakeProvider([_answer()]))

    with TestClient(app) as client:
        first = client.post("/api/v1/workspaces", json={"name": "A"}).json()
        second = client.post("/api/v1/workspaces", json={"name": "B"}).json()
        session_id = _session(client, workspace_id=first["id"])
        response = client.post(
            f"/api/v1/lab/sessions/{session_id}/turns",
            json={"workspace_id": second["id"], "content": "Responda."},
        )

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["detail"]["code"] == "scope.target_not_visible"


def test_cancelamento_preserva_draft_registrado_sem_completar_turno(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path)
    repository = app.state.repository
    workspace = repository.catalog.create_workspace("Workspace")
    project = repository.catalog.create_project(workspace.id, "Project")
    session = repository.lab.create_session(
        workspace_id=workspace.id,
        project_id=project.id,
        title="Turno",
    )
    document = {
        "contract_type": "goal",
        "logical_id": "goal-cancelado",
        "revision": 1,
        "title": "Goal preservado",
        "payload": {
            "mode": "goal_state",
            "instruction": "Preservar o draft já registrado.",
            "outcomes": [
                {"id": "preservado", "description": "O draft permanece registrado."}
            ],
        },
    }
    provider = FakeProvider(
        [
            _call(
                "validate_draft",
                {"contract_type": "goal", "document": document},
                "call_validate",
            ),
            _call(
                "propose_draft",
                {
                    "contract_type": "goal",
                    "document": document,
                    "informed_by": [],
                },
                "call_propose",
            ),
        ]
    )
    service = LabAgentSessionService(
        repository,
        provider,
        profile=app.state.settings.default_provider,
        capability_source=AdmissionCapabilityCatalog(
            app.state.runtime_kernel.catalog.capability_envelope()
        ),
    )

    def draft_ja_registrado() -> bool:
        return any(
            item["logical_id"] == "goal-cancelado"
            for item in repository.read_model.list_contract_revisions()
        )

    async def collect() -> list[Mapping[str, Any]]:
        return [
            event
            async for event in service.run_turn(
                session_id=session.id,
                workspace_id=workspace.id,
                content="Valide e registre o draft.",
                cancelled=draft_ja_registrado,
            )
        ]

    events = asyncio.run(collect())
    drafts = [
        item
        for item in repository.read_model.list_contract_revisions()
        if item["logical_id"] == "goal-cancelado"
    ]
    assert len(drafts) == 1
    assert drafts[0]["status"] == "draft"
    assert [event.get("label") for event in events if event["type"] == "status"] == [
        "working",
        "cancelled",
    ]
    assert not any(event["type"] == "message" for event in events)
