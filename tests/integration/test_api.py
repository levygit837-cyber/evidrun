from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from evidrun.entrypoints.api.app import create_app

ROOT = Path(__file__).resolve().parents[2]


def test_api_requires_desktop_token(tmp_path: Path) -> None:
    app = create_app(
        data_dir=tmp_path, launch_token="desktop-secret", benchmark_root=ROOT / "benchmarks"
    )
    with TestClient(app) as client:
        assert client.get("/api/v1/health").status_code == 401
        response = client.get(
            "/api/v1/health", headers={"Authorization": "Bearer desktop-secret"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_demo_dashboard_api(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, benchmark_root=ROOT / "benchmarks")
    with TestClient(app) as client:
        response = client.post("/api/v1/demo/bootstrap")
        assert response.status_code == 200
        dashboard = client.get("/api/v1/dashboard").json()
        assert dashboard["summary"]["runs"] == 2
        assert dashboard["comparisons"][0]["delta"] == 1


def test_default_provider_api_never_returns_secret(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("EVIDRUN_PROVIDER_API_KEY", "must-not-leak")
    app = create_app(data_dir=tmp_path, benchmark_root=ROOT / "benchmarks")
    with TestClient(app) as client:
        response = client.get("/api/v1/providers/default")
        assert response.status_code == 200
        payload = response.json()
        assert payload["model"] == "deepseek-v4-flash"
        assert payload["reasoning_effort"] == "max"
        assert payload["credential_available"] is True
        assert "must-not-leak" not in response.text
