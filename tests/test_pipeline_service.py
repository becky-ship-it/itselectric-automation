import base64
from unittest.mock import MagicMock, patch

import pytest
import server.models  # noqa: F401
from server.db import Base
from server.models import Charger, Contact, OutboundEmail, Template
from server.pipeline_service import run_pipeline
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def _b64(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).decode()


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    session = factory()
    session.add(Charger(street="1 Main St", city="Brooklyn", state="NY", lat=40.6943, lon=-73.9249))
    session.add(Template(name="tell_me_more_general", subject="Hi!", body_md="<p>Hi {name}</p>"))
    session.commit()
    yield session
    session.close()


FIXTURE_EMAIL = {
    "id": "msg_001",
    "internalDate": "1704067200000",
    "payload": {
        "mimeType": "text/plain",
        "body": {
            "data": _b64(
                "[plain]: it's electric Jane Smith "
                "The user has an address of 1 Atlantic Ave Brooklyn NY 11201 "
                "and has an email of jane@example.com\n"
                "Email address submitted in form\njane@example.com"
            )
        },
    },
}


def test_run_pipeline_creates_contact_row(db_session):
    with (
        patch("server.pipeline_service.fetch_messages", return_value=[FIXTURE_EMAIL]),
        patch("server.pipeline_service.get_credentials", return_value=MagicMock()),
        patch(
            "server.pipeline_service.geocode_address",
            return_value=(40.6929, -73.9958),
        ),
    ):
        run_pipeline(db_session, decision_tree=None, auto_send=False, log=lambda m: None)

    contact = db_session.query(Contact).filter_by(id="msg_001").first()
    assert contact is not None
    assert contact.name == "Jane Smith"
    assert contact.parse_status == "parsed"


def test_run_pipeline_creates_outbound_email_row(db_session):
    tree = {
        "condition": {"field": "distance_miles", "op": "lte", "value": 999},
        "then": {"template": "tell_me_more_general"},
        "else": {"template": None},
    }
    with (
        patch("server.pipeline_service.fetch_messages", return_value=[FIXTURE_EMAIL]),
        patch("server.pipeline_service.get_credentials", return_value=MagicMock()),
        patch("server.pipeline_service.geocode_address", return_value=(40.6929, -73.9958)),
    ):
        run_pipeline(db_session, decision_tree=tree, auto_send=False, log=lambda m: None)

    email = db_session.query(OutboundEmail).first()
    assert email is not None
    assert email.status == "pending"
    assert email.routed_template == "tell_me_more_general"


def test_run_pipeline_skips_duplicate_message(db_session):
    db_session.add(Contact(id="msg_001", parse_status="parsed", name="Jane"))
    db_session.commit()

    with (
        patch("server.pipeline_service.fetch_messages", return_value=[FIXTURE_EMAIL]),
        patch("server.pipeline_service.get_credentials", return_value=MagicMock()),
    ):
        run_pipeline(db_session, decision_tree=None, auto_send=False, log=lambda m: None)

    assert db_session.query(Contact).filter_by(id="msg_001").count() == 1


def test_run_pipeline_unparsed_email_creates_unparsed_row(db_session):
    unparsed_msg = {
        "id": "msg_002",
        "internalDate": "1704067200000",
        "payload": {
            "mimeType": "text/plain",
            "body": {"data": _b64("[plain]: just a random question")},
        },
    }
    with (
        patch("server.pipeline_service.fetch_messages", return_value=[unparsed_msg]),
        patch("server.pipeline_service.get_credentials", return_value=MagicMock()),
    ):
        run_pipeline(db_session, decision_tree=None, auto_send=False, log=lambda m: None)

    contact = db_session.query(Contact).filter_by(id="msg_002").first()
    assert contact is not None
    assert contact.parse_status == "unparsed"


def test_run_pipeline_uses_fixture_messages_when_provided(db_session):
    with patch("server.pipeline_service.get_credentials", return_value=MagicMock()):
        run_pipeline(
            db_session,
            decision_tree=None,
            fixture_messages=[FIXTURE_EMAIL],
            log=lambda m: None,
        )

    assert db_session.query(Contact).filter_by(id="msg_001").count() == 1
