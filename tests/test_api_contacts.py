from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import server.main


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(server.main, "DB_URL", f"sqlite:///{tmp_path}/test.db")
    with TestClient(server.main.app) as c:
        yield c


def test_list_contacts_empty(client):
    resp = client.get("/api/contacts")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_list_contacts_status_filter(client):
    resp = client.get("/api/contacts?status=unparsed")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_contact_not_found(client):
    resp = client.get("/api/contacts/does-not-exist")
    assert resp.status_code == 404


def test_skip_contact_not_found(client):
    resp = client.post("/api/contacts/does-not-exist/skip")
    assert resp.status_code == 404


def test_send_contact_not_found(client):
    resp = client.post("/api/contacts/does-not-exist/send")
    assert resp.status_code == 404


def test_send_batch_empty(client):
    resp = client.post("/api/contacts/send-batch")
    assert resp.status_code == 200
    data = resp.json()
    assert "sent" in data
    assert data["sent"] == 0
