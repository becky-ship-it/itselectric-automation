import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from server.db import Base, get_engine, get_session  # noqa: F401


def test_engine_creates_sqlite_in_memory():
    engine = get_engine("sqlite:///:memory:")
    assert engine is not None


def test_session_factory_yields_session():
    engine = get_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with get_session(engine) as session:
        assert isinstance(session, Session)


def test_tables_created_on_metadata_create_all():
    import server.models  # noqa: F401 — registers all models with Base.metadata

    engine = get_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "contacts" in tables
    assert "outbound_emails" in tables
    assert "chargers" in tables
    assert "templates" in tables
    assert "geocache" in tables
    assert "app_config" in tables
