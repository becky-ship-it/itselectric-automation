import pytest
import server.main
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(server.main, "DB_URL", f"sqlite:///{tmp_path}/test.db")
    with TestClient(server.main.app) as c:
        yield c


def test_list_templates(client):
    resp = client.get("/api/templates")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_template_not_found(client):
    resp = client.get("/api/templates/nonexistent-tmpl")
    assert resp.status_code == 404


def test_create_template(client):
    resp = client.post(
        "/api/templates/test-tmpl",
        json={"subject": "Hello", "body_html": "<p>Hi</p>"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "test-tmpl"
    assert data["subject"] == "Hello"


def test_create_template_conflict(client):
    client.post("/api/templates/dup-tmpl", json={"subject": "A", "body_html": "B"})
    resp = client.post("/api/templates/dup-tmpl", json={"subject": "A", "body_html": "B"})
    assert resp.status_code == 409


def test_get_template_after_create(client):
    client.post("/api/templates/get-test", json={"subject": "S", "body_html": "B"})
    resp = client.get("/api/templates/get-test")
    assert resp.status_code == 200
    assert resp.json()["name"] == "get-test"


def test_update_template(client):
    client.post("/api/templates/upd-tmpl", json={"subject": "Old", "body_html": "Old"})
    resp = client.put("/api/templates/upd-tmpl", json={"subject": "New", "body_html": "New"})
    assert resp.status_code == 200
    assert resp.json()["subject"] == "New"


def test_update_template_not_found(client):
    resp = client.put("/api/templates/ghost", json={"subject": "X", "body_html": "Y"})
    assert resp.status_code == 404


def test_delete_template(client):
    client.post("/api/templates/del-tmpl", json={"subject": "D", "body_html": "D"})
    resp = client.delete("/api/templates/del-tmpl")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_delete_template_not_found(client):
    resp = client.delete("/api/templates/no-such")
    assert resp.status_code == 404
