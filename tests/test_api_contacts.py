
import pytest
import server.main
from fastapi.testclient import TestClient
from server.db import get_engine, get_session
from server.models import Charger, Contact, OutboundEmail, Template


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_url = f"sqlite:///{tmp_path}/test.db"
    monkeypatch.setattr(server.main, "DB_URL", db_url)
    with TestClient(server.main.app) as c:
        c.db_url = db_url  # type: ignore[attr-defined]
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


def test_get_contact_fills_contact_city_placeholder(client):
    """{contact_city} in a template resolves to the contact's own city."""
    engine = get_engine(client.db_url)  # type: ignore[attr-defined]
    with get_session(engine) as session:
        session.add(
            Charger(street="1 Main St", city="Brooklyn", state="NY", lat=40.6943, lon=-73.9249)
        )
        session.flush()
        charger_id = session.query(Charger).filter_by(street="1 Main St").first().id
        session.add(
            Contact(
                id="msg_city_test",
                name="Jane Smith",
                address="1 Atlantic Ave, Queens, NY 11201",
                parse_status="parsed",
                nearest_charger_id=charger_id,
            )
        )
        session.add(
            Template(name="tmpl_city_test", subject="Hi", body_md="Hi from {contact_city}")
        )
        session.add(
            OutboundEmail(
                contact_id="msg_city_test",
                template_name="tmpl_city_test",
                subject="Hi",
                body_html="",
                status="pending",
            )
        )

    resp = client.get("/api/contacts/msg_city_test")
    assert resp.status_code == 200
    body = resp.json()["outbound_emails"][0]["body_html"]
    assert "Queens" in body
