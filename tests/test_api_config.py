import pytest
from fastapi.testclient import TestClient

import server.main


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(server.main, "DB_URL", f"sqlite:///{tmp_path}/test.db")
    with TestClient(server.main.app) as c:
        yield c


def test_get_config(client):
    resp = client.get("/api/config")
    assert resp.status_code == 200
    assert "data" in resp.json()


def test_put_config_allowed_key(client):
    resp = client.put("/api/config", json={"label": "test-label"})
    assert resp.status_code == 200
    assert resp.json()["data"]["label"] == "test-label"


def test_put_config_disallowed_key_ignored(client):
    resp = client.put("/api/config", json={"secret_key": "hacker"})
    assert resp.status_code == 200
    assert "secret_key" not in resp.json()["data"]


def test_get_decision_tree_none(client):
    resp = client.get("/api/decision-tree")
    assert resp.status_code == 200


def test_put_and_get_decision_tree(client):
    tree = {"type": "leaf", "template": "driver_in_state"}
    put = client.put("/api/decision-tree", json=tree)
    assert put.status_code == 200
    assert put.json()["type"] == "leaf"

    get = client.get("/api/decision-tree")
    assert get.status_code == 200
    assert get.json()["template"] == "driver_in_state"


def test_decision_tree_test_no_tree(client):
    # clear the tree
    client.put("/api/decision-tree", json={"type": "leaf", "template": "x"})
    resp = client.post("/api/decision-tree/test")
    assert resp.status_code in (200, 400)
