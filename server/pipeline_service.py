"""Pipeline orchestration: fetch → parse → geocode → route → write DB."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from sqlalchemy.orm import Session

from server.models import AppConfig, Charger, Contact, GeoCache, OutboundEmail, Template
from src.itselectric.auth import get_credentials
from src.itselectric.decision_tree import evaluate as evaluate_tree
from src.itselectric.extract import extract_parsed
from src.itselectric.geo import extract_state_from_address, find_nearest_charger, geocode_address
from src.itselectric.gmail import body_to_plain, fetch_messages, get_body_from_payload


def _chargers_from_db(session: Session) -> list[dict]:
    rows = session.query(Charger).all()
    return [
        {
            "name": f"{r.street}, {r.city}, {r.state}",
            "city": r.city,
            "state": r.state,
            "lat": r.lat,
            "lon": r.lon,
            "db_id": r.id,
        }
        for r in rows
    ]


def _geocode_with_db_cache(address: str, session: Session) -> tuple[float, float] | None:
    entry = session.query(GeoCache).filter_by(address=address).first()
    if entry:
        return entry.lat, entry.lon
    coords = geocode_address(address)
    if coords:
        existing = session.query(GeoCache).filter_by(address=address).first()
        if not existing:
            session.add(GeoCache(address=address, lat=coords[0], lon=coords[1]))
            session.flush()
    return coords


def _get_config(session: Session, key: str, default: str = "") -> str:
    row = session.query(AppConfig).filter_by(key=key).first()
    return row.value if row else default


def run_pipeline(
    session: Session,
    geocache_path: str = "geocache.json",
    decision_tree: dict | None = None,
    auto_send: bool = False,
    label: str | None = None,
    max_messages: int | None = None,
    log: Callable[[str], None] = print,
    fixture_messages: list[dict] | None = None,
) -> list[str]:
    """
    Run the full pipeline. Returns list of contact IDs processed.
    If fixture_messages is provided, uses those instead of fetching from Gmail.
    """
    if label is None:
        label = _get_config(session, "label", "INBOX")
    if max_messages is None:
        max_messages = int(_get_config(session, "max_messages", "100"))

    chargers = _chargers_from_db(session)
    creds = get_credentials()

    if fixture_messages is not None:
        messages = fixture_messages
    else:
        log("Fetching emails from Gmail...")
        messages = fetch_messages(creds, label, max_messages)
        log(f"Fetched {len(messages)} message(s).")

    processed: list[str] = []

    for msg in messages:
        msg_id = msg.get("id", "")

        if session.query(Contact).filter_by(id=msg_id).first():
            log(f"Skipping already-processed message {msg_id}")
            continue

        mime_type, body_text = get_body_from_payload(msg.get("payload", {}))
        plain = body_to_plain(mime_type, body_text) if body_text else ""

        received_str = msg.get("internalDate")
        received_at = None
        if received_str:
            try:
                received_at = datetime.fromtimestamp(int(received_str) / 1000, tz=timezone.utc)
            except (ValueError, TypeError):
                pass

        parsed = extract_parsed(plain)

        contact = Contact(
            id=msg_id,
            received_at=received_at,
            raw_body=plain,
            parse_status="parsed" if parsed else "unparsed",
        )

        nearest_charger_row = None
        dist_float = None
        driver_state = None
        charger_city = None

        if parsed:
            contact.name = parsed["name"]
            contact.address = parsed["address"]
            contact.email_primary = parsed["email_1"]
            contact.email_form = parsed["email_2"]

            log(f"  Processing: {parsed['name']} / {parsed['address']}")

            coords = _geocode_with_db_cache(parsed["address"], session)
            if coords:
                lat, lon = coords
                result = find_nearest_charger(lat, lon, chargers)
                if result:
                    nearest_charger_dict, dist_float = result
                    nearest_charger_row = session.query(Charger).filter_by(
                        id=nearest_charger_dict["db_id"]
                    ).first()
                    contact.nearest_charger_id = (
                        nearest_charger_row.id if nearest_charger_row else None
                    )
                    contact.distance_miles = dist_float
                    driver_state = extract_state_from_address(parsed["address"])
                    charger_city = nearest_charger_dict["city"]
                    log(f"  Nearest charger: {nearest_charger_dict['name']} ({dist_float} mi)")
                else:
                    log("  No charger found.")
            else:
                log(f"  Could not geocode: {parsed['address']!r}")

        session.add(contact)
        session.flush()

        if parsed and decision_tree and nearest_charger_row and dist_float is not None:
            ctx = {
                "driver_state": driver_state,
                "charger_state": nearest_charger_row.state,
                "charger_city": charger_city,
                "distance_miles": dist_float,
            }
            try:
                template_name = evaluate_tree(decision_tree, ctx)
            except (KeyError, ValueError) as e:
                log(f"  Decision tree error: {e}")
                template_name = None

            if template_name:
                tmpl = session.query(Template).filter_by(name=template_name).first()
                subject = tmpl.subject if tmpl else ""
                body = tmpl.body_html if tmpl else ""
                try:
                    body = body.format_map(
                        {
                            "name": parsed["name"],
                            "address": parsed["address"],
                            "city": charger_city or "",
                            "state": driver_state or "",
                        }
                    )
                except KeyError:
                    pass
                outbound = OutboundEmail(
                    contact_id=msg_id,
                    template_name=template_name,
                    routed_template=template_name,
                    subject=subject,
                    body_html=body,
                    status="pending",
                )
                session.add(outbound)
                log(f"  → Queued email: {template_name}")

        processed.append(msg_id)

    session.commit()
    log(f"Done. Processed {len(processed)} new message(s).")
    return processed
