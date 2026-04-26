import json

import pytest
import server.models  # noqa: F401
from server.db import Base
from server.models import AppConfig, Charger, GeoCache, Template
from server.seed import (
    DEFAULT_CHARGERS_CSV,
    seed_chargers,
    seed_config,
    seed_decision_tree_from_yaml,
    seed_geocache,
    seed_templates_from_yaml,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


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


def test_seed_decision_tree_from_yaml_inserts_when_absent(session, tmp_path):
    yaml_file = tmp_path / "tree.yaml"
    yaml_file.write_text(
        "condition:\n  field: distance_miles\n  op: lte\n  value: 5\n"
        "then:\n  template: close\nelse:\n  template: far\n"
    )
    count = seed_decision_tree_from_yaml(session, str(yaml_file))
    assert count == 1
    row = session.query(AppConfig).filter_by(key="__decision_tree_json__").first()
    assert row is not None
    tree = json.loads(row.value)
    assert tree["condition"]["field"] == "distance_miles"


def test_seed_decision_tree_from_yaml_skips_when_present(session, tmp_path):
    yaml_file = tmp_path / "tree.yaml"
    yaml_file.write_text("template: new\n")
    session.add(AppConfig(
        key="__decision_tree_json__", value=json.dumps({"template": "already_here"})
    ))
    session.flush()
    count = seed_decision_tree_from_yaml(session, str(yaml_file))
    assert count == 0
    row = session.query(AppConfig).filter_by(key="__decision_tree_json__").first()
    assert json.loads(row.value) == {"template": "already_here"}


def test_seed_decision_tree_from_yaml_missing_file(session, tmp_path):
    count = seed_decision_tree_from_yaml(session, str(tmp_path / "nonexistent.yaml"))
    assert count == 0
    assert session.query(AppConfig).filter_by(key="__decision_tree_json__").first() is None


def test_seed_templates_does_not_overwrite_existing(session, tmp_path):
    session.add(Template(name="tell_me_more_general", subject="Existing", body_md="<p>keep</p>"))
    session.commit()
    tree_yaml = tmp_path / "tree.yaml"
    tree_yaml.write_text(
        "condition:\n  field: x\n  op: eq\n  value: y\n"
        "then:\n  template: tell_me_more_general\nelse:\n  template: waitlist\n"
    )
    seed_templates_from_yaml(session, str(tree_yaml))
    t = session.query(Template).filter_by(name="tell_me_more_general").first()
    assert t.subject == "Existing"
