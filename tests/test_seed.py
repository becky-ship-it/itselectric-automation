import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import server.models  # noqa: F401
from server.db import Base
from server.models import AppConfig, Charger, GeoCache, Template
from server.seed import (
    DEFAULT_CHARGERS_CSV,
    seed_chargers,
    seed_config,
    seed_geocache,
    seed_templates_from_yaml,
)


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    s = factory()
    yield s
    s.close()


def test_seed_chargers_loads_all_from_csv(session):
    seed_chargers(session, DEFAULT_CHARGERS_CSV)
    count = session.query(Charger).count()
    assert count > 0


def test_seed_chargers_is_idempotent(session):
    seed_chargers(session, DEFAULT_CHARGERS_CSV)
    first = session.query(Charger).count()
    seed_chargers(session, DEFAULT_CHARGERS_CSV)
    assert session.query(Charger).count() == first


def test_seed_geocache_imports_json(session, tmp_path):
    cache = {"123 Main St, Boston MA": [42.36, -71.06]}
    cache_file = tmp_path / "geocache.json"
    cache_file.write_text(json.dumps(cache))
    seed_geocache(session, str(cache_file))
    entry = session.query(GeoCache).filter_by(address="123 Main St, Boston MA").first()
    assert entry is not None
    assert abs(entry.lat - 42.36) < 0.001


def test_seed_geocache_skips_missing_file(session):
    seed_geocache(session, "/nonexistent/geocache.json")
    assert session.query(GeoCache).count() == 0


def test_seed_config_writes_defaults(session):
    seed_config(session, {"label": "Follow Up", "max_messages": 50})
    assert session.query(AppConfig).filter_by(key="label").first().value == "Follow Up"
    assert session.query(AppConfig).filter_by(key="max_messages").first().value == "50"


def test_seed_config_is_idempotent(session):
    seed_config(session, {"label": "INBOX"})
    seed_config(session, {"label": "INBOX"})
    assert session.query(AppConfig).filter_by(key="label").count() == 1


def test_seed_templates_from_yaml_creates_rows(session, tmp_path):
    tree_yaml = tmp_path / "tree.yaml"
    tree_yaml.write_text(
        "condition:\n  field: distance_miles\n  op: lte\n  value: 5\n"
        "then:\n  template: tell_me_more_general\nelse:\n  template: waitlist\n"
    )
    seed_templates_from_yaml(session, str(tree_yaml))
    names = {t.name for t in session.query(Template).all()}
    assert "tell_me_more_general" in names
    assert "waitlist" in names


def test_seed_templates_does_not_overwrite_existing(session, tmp_path):
    session.add(Template(name="tell_me_more_general", subject="Existing", body_html="<p>keep</p>"))
    session.commit()
    tree_yaml = tmp_path / "tree.yaml"
    tree_yaml.write_text(
        "condition:\n  field: x\n  op: eq\n  value: y\n"
        "then:\n  template: tell_me_more_general\nelse:\n  template: waitlist\n"
    )
    seed_templates_from_yaml(session, str(tree_yaml))
    t = session.query(Template).filter_by(name="tell_me_more_general").first()
    assert t.subject == "Existing"
