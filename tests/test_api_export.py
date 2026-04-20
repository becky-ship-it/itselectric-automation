import pytest
import server.main
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(server.main, "DB_URL", f"sqlite:///{tmp_path}/test.db")
    with TestClient(server.main.app) as c:
        yield c


_SNAPSHOT = {
    "contacts": [],
    "outbound_emails": [],
    "chargers": [
        {
            "street": "99 New St",
            "city": "Albany",
            "state": "NY",
            "lat": 42.65,
            "lon": -73.75,
            "zipcode": None,
            "charger_id": None,
            "num_chargers": None,
        }
    ],
    "templates": [],
    "geocache": [],
}


def test_snapshot_export_returns_json(client):
    resp = client.get("/api/export/snapshot")
    assert resp.status_code == 200
    data = resp.json()
    assert "contacts" in data
    assert "outbound_emails" in data
    assert "chargers" in data
    assert "templates" in data
    assert "geocache" in data


def test_csv_export_returns_csv_content_type(client):
    resp = client.get("/api/export/csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")


def test_snapshot_import_preview_returns_diff(client):
    resp = client.post("/api/import/snapshot", json=_SNAPSHOT)
    assert resp.status_code == 200
    body = resp.json()
    assert "preview" in body
    assert "import_id" in body
    assert body["preview"]["new_chargers"] == 1


def test_snapshot_import_confirm_applies_changes(client):
    preview = client.post("/api/import/snapshot", json=_SNAPSHOT)
    import_id = preview.json()["import_id"]
    confirm = client.post(f"/api/import/snapshot/confirm/{import_id}")
    assert confirm.status_code == 200
    assert confirm.json()["ok"] is True

    chargers = client.get("/api/chargers").json()
    assert any(c["city"] == "Albany" for c in chargers)


def test_snapshot_import_confirm_unknown_id(client):
    resp = client.post("/api/import/snapshot/confirm/no-such-id")
    assert resp.status_code == 404
