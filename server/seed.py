"""One-time database seeding from existing config files."""

import csv
import json
from pathlib import Path

import yaml  # type: ignore
from sqlalchemy.orm import Session

from server.models import AppConfig, Charger, GeoCache, Template

DEFAULT_CHARGERS_CSV = Path(__file__).parent.parent / "src/itselectric/data/chargers.csv"


def seed_chargers(session: Session, csv_path=DEFAULT_CHARGERS_CSV) -> int:
    """Import chargers.csv into chargers table. Skips rows already present by street+city+state."""
    count = 0
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lat = float(row["LAT_OVERRIDE"] or row["LAT"])
            lon = float(row["LONG_OVERRIDE"] or row["LONG"])
            existing = (
                session.query(Charger)
                .filter_by(
                    street=row["STREET"].strip(),
                    city=row["CITY"].strip().title(),
                    state=row["STATE"].strip().upper(),
                )
                .first()
            )
            if existing:
                continue
            session.add(
                Charger(
                    street=row["STREET"].strip(),
                    city=row["CITY"].strip().title(),
                    state=row["STATE"].strip().upper(),
                    zipcode=row.get("ZIPCODE", "").strip() or None,
                    charger_id=row.get("CHARGERID", "").strip() or None,
                    num_chargers=int(row["NUM_OF_CHARGERS"]) if row.get("NUM_OF_CHARGERS") else None,
                    lat=lat,
                    lon=lon,
                )
            )
            count += 1
    session.flush()
    return count


def seed_geocache(session: Session, json_path: str) -> int:
    """Import geocache.json into geocache table. Silently skips missing file."""
    try:
        with open(json_path) as f:
            cache = json.load(f)
    except FileNotFoundError:
        return 0
    count = 0
    for address, coords in cache.items():
        if session.query(GeoCache).filter_by(address=address).first():
            continue
        lat, lon = coords[0], coords[1]
        session.add(GeoCache(address=address, lat=lat, lon=lon))
        count += 1
    session.flush()
    return count


def seed_config(session: Session, config: dict) -> None:
    """Write config key-value pairs into app_config. Does not overwrite existing keys."""
    for key, value in config.items():
        if session.query(AppConfig).filter_by(key=key).first():
            continue
        session.add(AppConfig(key=key, value=str(value)))
    session.flush()


def _collect_template_names(node: dict) -> set[str]:
    """Recursively collect all non-null template names from a decision tree dict."""
    if "template" in node:
        name = node["template"]
        return {name} if name else set()
    names: set[str] = set()
    for branch in ("then", "else"):
        if branch in node:
            names |= _collect_template_names(node[branch])
    return names


def seed_templates_from_yaml(session: Session, yaml_path: str) -> int:
    """Create placeholder Template rows for all names in a decision tree YAML.
    Does not overwrite existing templates."""
    try:
        with open(yaml_path) as f:
            tree = yaml.safe_load(f)
    except FileNotFoundError:
        return 0
    names = _collect_template_names(tree)
    count = 0
    for name in sorted(names):
        if session.query(Template).filter_by(name=name).first():
            continue
        session.add(Template(name=name, subject="", body_html=""))
        count += 1
    session.flush()
    return count
