"""Configuration and decision tree API endpoints."""

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, sessionmaker

from server.models import AppConfig

router = APIRouter()

_DECISION_TREE_KEY = "__decision_tree_json__"

_ALLOWED_CONFIG_KEYS = {
    "label",
    "max_messages",
    "body_length",
    "spreadsheet_id",
    "sheet",
    "content_limit",
    "hubspot_access_token",
    "google_doc_id",
    "auto_send",
}


def get_db():
    from server.db import get_engine
    from server.main import DB_URL

    engine = get_engine(DB_URL)
    s = sessionmaker(bind=engine)()
    try:
        yield s
    finally:
        s.close()


DbDep = Annotated[Session, Depends(get_db)]


@router.get("/config")
def get_config(db: DbDep):
    rows = db.query(AppConfig).filter(AppConfig.key.in_(_ALLOWED_CONFIG_KEYS)).all()
    return {"data": {r.key: r.value for r in rows}}


@router.put("/config")
def put_config(body: dict[str, Any], db: DbDep):
    for key, value in body.items():
        if key not in _ALLOWED_CONFIG_KEYS:
            continue
        row = db.query(AppConfig).filter_by(key=key).first()
        if row:
            row.value = str(value)
        else:
            db.add(AppConfig(key=key, value=str(value)))
    db.commit()
    rows = db.query(AppConfig).filter(AppConfig.key.in_(_ALLOWED_CONFIG_KEYS)).all()
    return {"data": {r.key: r.value for r in rows}}


@router.get("/decision-tree")
def get_decision_tree(db: DbDep):
    row = db.query(AppConfig).filter_by(key=_DECISION_TREE_KEY).first()
    if not row:
        return None
    return json.loads(row.value)


@router.put("/decision-tree")
def put_decision_tree(body: dict[str, Any], db: DbDep):
    row = db.query(AppConfig).filter_by(key=_DECISION_TREE_KEY).first()
    serialized = json.dumps(body)
    if row:
        row.value = serialized
    else:
        db.add(AppConfig(key=_DECISION_TREE_KEY, value=serialized))
    db.commit()
    return body


@router.post("/decision-tree/test")
def test_decision_tree(db: DbDep):
    """Dry-run current decision tree against fixture emails."""
    from src.itselectric.decision_tree import evaluate
    from src.itselectric.extract import extract_parsed
    from src.itselectric.fixture import load_fixture_messages
    from src.itselectric.geo import extract_state_from_address, find_nearest_charger
    from src.itselectric.gmail import body_to_plain, get_body_from_payload

    from server.models import Charger, GeoCache

    row = db.query(AppConfig).filter_by(key=_DECISION_TREE_KEY).first()
    if not row:
        raise HTTPException(status_code=400, detail="No decision tree saved")
    tree = json.loads(row.value)

    chargers = [
        {
            "name": f"{c.street}, {c.city}, {c.state}",
            "city": c.city,
            "state": c.state,
            "lat": c.lat,
            "lon": c.lon,
        }
        for c in db.query(Charger).all()
    ]

    try:
        messages = load_fixture_messages("tests/fixtures/emails")
    except FileNotFoundError:
        return {"results": [], "error": "fixture directory not found"}

    results = []
    for msg in messages:
        mime, body = get_body_from_payload(msg.get("payload", {}))
        plain = body_to_plain(mime, body) if body else ""
        parsed = extract_parsed(plain)
        if not parsed:
            results.append({"id": msg.get("id", ""), "parsed": False, "template": None})
            continue

        cache = db.query(GeoCache).filter_by(address=parsed["address"]).first()
        if cache:
            coords: tuple[float, float] | None = (cache.lat, cache.lon)
        else:
            from src.itselectric.geo import geocode_address

            coords = geocode_address(parsed["address"])

        if not coords:
            results.append({"id": msg.get("id", ""), "parsed": True, "template": "geocode_failed"})
            continue

        result = find_nearest_charger(coords[0], coords[1], chargers)
        if not result:
            results.append({"id": msg.get("id", ""), "parsed": True, "template": "no_charger"})
            continue

        charger, dist = result
        ctx = {
            "driver_state": extract_state_from_address(parsed["address"]),
            "charger_state": charger["state"],
            "charger_city": charger["city"],
            "distance_miles": dist,
        }
        try:
            template = evaluate(tree, ctx)
        except (KeyError, ValueError) as e:
            template = f"error:{e}"

        results.append(
            {
                "id": msg.get("id", ""),
                "name": parsed["name"],
                "address": parsed["address"],
                "parsed": True,
                "template": template,
            }
        )

    return {"results": results}
