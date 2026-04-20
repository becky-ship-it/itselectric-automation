import pytest
from fastapi.testclient import TestClient

import server.main


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(server.main, "DB_URL", f"sqlite:///{tmp_path}/test.db")
    with TestClient(server.main.app) as c:
        yield c


_CHARGER = {
    "street": "123 Main St",
    "city": "Portland",
    "state": "OR",
    "zipcode": "97201",
    "num_chargers": 4,
    "lat": 45.523064,
    "lon": -122.676483,
}


def test_list_chargers(client):
    resp = client.get("/api/chargers")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_create_charger(client):
    resp = client.post("/api/chargers", json=_CHARGER)
    assert resp.status_code == 200
    data = resp.json()
    assert data["city"] == "Portland"
    assert "id" in data


def test_update_charger(client):
    create = client.post("/api/chargers", json=_CHARGER)
    charger_id = create.json()["id"]
    updated = {**_CHARGER, "city": "Seattle", "state": "WA"}
    resp = client.put(f"/api/chargers/{charger_id}", json=updated)
    assert resp.status_code == 200
    assert resp.json()["city"] == "Seattle"


def test_update_charger_not_found(client):
    resp = client.put("/api/chargers/99999", json=_CHARGER)
    assert resp.status_code == 404


def test_delete_charger(client):
    create = client.post("/api/chargers", json=_CHARGER)
    charger_id = create.json()["id"]
    resp = client.delete(f"/api/chargers/{charger_id}")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_delete_charger_not_found(client):
    resp = client.delete("/api/chargers/99999")
    assert resp.status_code == 404
