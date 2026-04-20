from unittest.mock import patch

from fastapi.testclient import TestClient

from server.main import app


def test_pipeline_status_returns_idle():
    client = TestClient(app)
    resp = client.get("/api/pipeline/status")
    assert resp.status_code == 200
    assert resp.json()["status"] == "idle"


def test_pipeline_run_returns_run_id():
    client = TestClient(app)
    with patch("server.routers.pipeline.run_pipeline", return_value=["msg_001"]):
        resp = client.post("/api/pipeline/run")
    assert resp.status_code == 200
    assert "run_id" in resp.json()


def test_pipeline_run_fixture_mode_passes_fixture_messages():
    client = TestClient(app)
    captured = {}

    def _fake_run(session, **kwargs):
        captured["fixture_messages"] = kwargs.get("fixture_messages")
        return []

    with patch("server.routers.pipeline.run_pipeline", side_effect=_fake_run):
        resp = client.post("/api/pipeline/run?fixture=true")

    assert resp.status_code == 200
    assert captured.get("fixture_messages") is not None


def test_pipeline_status_fields_present():
    client = TestClient(app)
    resp = client.get("/api/pipeline/status")
    data = resp.json()
    assert "status" in data
    assert "last_run_at" in data
    assert "run_id" in data
