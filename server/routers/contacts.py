"""Contacts / inbox API endpoints."""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session, sessionmaker

from server.models import AppConfig, Charger, Contact, GeoCache, OutboundEmail, Template
from server.schemas import ContactOut, OutboundEmailOut

router = APIRouter()


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


@router.get("", response_model=list[ContactOut])
def list_contacts(
    db: DbDep,
    status: str | None = Query(default=None),
    limit: int = Query(default=100),
    offset: int = Query(default=0),
):
    q = db.query(Contact).order_by(Contact.received_at.desc())
    if status == "unparsed":
        q = q.filter(Contact.parse_status == "unparsed")
    elif status == "pending":
        pending_ids = db.query(OutboundEmail.contact_id).filter_by(status="pending").subquery()
        q = q.filter(Contact.id.in_(pending_ids))
    else:
        q = q.filter(Contact.parse_status != "unparsed")
    contacts = q.offset(offset).limit(limit).all()

    # Attach latest outbound status for each contact
    contact_ids = [c.id for c in contacts]
    if contact_ids:
        rows = (
            db.query(OutboundEmail.contact_id, OutboundEmail.status)
            .filter(OutboundEmail.contact_id.in_(contact_ids))
            .all()
        )
        # Last-write-wins per contact (rows ordered by insertion; later rows override)
        outbound_by_contact: dict[str, str] = {}
        for cid, s in rows:
            outbound_by_contact[cid] = s
    else:
        outbound_by_contact = {}

    result = []
    for c in contacts:
        out = ContactOut.model_validate(c)
        out.outbound_status = outbound_by_contact.get(c.id)
        result.append(out)
    return result


@router.get("/{contact_id}")
def get_contact(contact_id: str, db: DbDep):
    from src.itselectric.email_layout import render_email

    contact = db.query(Contact).filter_by(id=contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    outbound = db.query(OutboundEmail).filter_by(contact_id=contact_id).all()

    from src.itselectric.geo import extract_state_from_address

    class _SafeDict(dict):
        def __missing__(self, key: str) -> str:
            return f'{{{key}}}'

    charger_city = None
    if contact.nearest_charger_id:
        from server.models import Charger
        ch = db.query(Charger).filter_by(id=contact.nearest_charger_id).first()
        charger_city = ch.city if ch else None

    _vars = _SafeDict(
        name=contact.name or "",
        address=contact.address or "",
        city=charger_city or "",
        state=extract_state_from_address(contact.address or "") or "",
    )

    rendered = []
    for e in outbound:
        out = OutboundEmailOut.model_validate(e)
        tmpl = db.query(Template).filter_by(name=e.template_name).first() if e.template_name else None
        body_md = (tmpl.body_md if tmpl else None) or e.body_html or ""
        out.body_html = render_email(body_md.format_map(_vars))
        rendered.append(out)

    return {
        "contact": ContactOut.model_validate(contact),
        "outbound_emails": rendered,
    }


@router.delete("/{contact_id}")
def delete_contact(contact_id: str, db: DbDep):
    contact = db.query(Contact).filter_by(id=contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    db.query(OutboundEmail).filter_by(contact_id=contact_id).delete()
    db.delete(contact)
    db.commit()
    return {"ok": True}


@router.post("/{contact_id}/skip")
def skip_contact(contact_id: str, db: DbDep):
    outbound = db.query(OutboundEmail).filter_by(contact_id=contact_id, status="pending").first()
    if not outbound:
        raise HTTPException(status_code=404, detail="No pending email for contact")
    outbound.status = "skipped"
    db.commit()
    return {"ok": True}


@router.post("/{contact_id}/send")
def send_contact_email(
    contact_id: str,
    db: DbDep,
    template_override: str | None = Query(default=None),
):
    from src.itselectric.auth import get_credentials
    from src.itselectric.gmail import send_email

    outbound = db.query(OutboundEmail).filter_by(contact_id=contact_id, status="pending").first()
    if not outbound:
        raise HTTPException(status_code=404, detail="No pending email for contact")

    contact = db.query(Contact).filter_by(id=contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    from src.itselectric.email_layout import render_email

    class _SafeDict(dict):
        def __missing__(self, key: str) -> str:
            return f'{{{key}}}'

    def _substitute(md: str) -> str:
        driver_state = None
        if contact.address:
            from src.itselectric.geo import extract_state_from_address
            driver_state = extract_state_from_address(contact.address)
        charger_city = None
        if contact.nearest_charger_id:
            from server.models import Charger
            ch = db.query(Charger).filter_by(id=contact.nearest_charger_id).first()
            charger_city = ch.city if ch else None
        return md.format_map(_SafeDict(
            name=contact.name or "",
            address=contact.address or "",
            city=charger_city or "",
            state=driver_state or "",
        ))

    subject = outbound.subject or ""

    if template_override:
        tmpl = db.query(Template).filter_by(name=template_override).first()
        if tmpl:
            outbound.template_name = template_override
            subject = tmpl.subject
            body = render_email(_substitute(tmpl.body_md))
        else:
            body = outbound.body_html or ""
    elif outbound.template_name:
        tmpl = db.query(Template).filter_by(name=outbound.template_name).first()
        body = render_email(_substitute(tmpl.body_md)) if tmpl else (outbound.body_html or "")
    else:
        body = outbound.body_html or ""

    try:
        creds = get_credentials()
        ok = send_email(creds, contact.email_primary, subject, body)
    except Exception as e:
        outbound.status = "failed"
        outbound.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))

    if ok:
        outbound.status = "sent"
        outbound.sent_at = datetime.now(timezone.utc)
        outbound.sent_by = "manual"
    else:
        outbound.status = "failed"
        outbound.error_message = "Gmail API returned failure"
    db.commit()

    # Background: append to Sheets (non-fatal)
    spread_row = db.query(AppConfig).filter_by(key="spreadsheet_id").first()
    if spread_row and spread_row.value:
        charger = (
            db.query(Charger).filter_by(id=contact.nearest_charger_id).first()
            if contact.nearest_charger_id
            else None
        )
        row = (
            contact.received_at.strftime("%Y-%m-%d %H:%M:%S UTC") if contact.received_at else "",
            contact.name or "",
            contact.address or "",
            contact.email_primary or "",
            contact.email_form or "",
            contact.raw_body or "",
            f"{charger.street}, {charger.city}, {charger.state}" if charger else "",
            str(contact.distance_miles) if contact.distance_miles else "",
            contact.hubspot_status or "",
            outbound.template_name or "",
        )
        try:
            from src.itselectric.sheets import append_rows

            append_rows(creds, spread_row.value, "Sheet1", [row], 5000)
        except Exception:
            pass

    return {"ok": ok, "status": outbound.status}


@router.post("/send-batch")
def send_batch(db: DbDep):
    from src.itselectric.auth import get_credentials
    from src.itselectric.gmail import send_email

    pendings = db.query(OutboundEmail).filter_by(status="pending").all()
    results = []
    for outbound in pendings:
        contact = db.query(Contact).filter_by(id=outbound.contact_id).first()
        if not contact or not contact.email_primary:
            continue
        try:
            creds = get_credentials()
            from src.itselectric.email_layout import render_email as _render
            from src.itselectric.geo import extract_state_from_address

            class _SD(dict):
                def __missing__(self, key: str) -> str:
                    return f'{{{key}}}'

            charger_city = None
            if contact.nearest_charger_id:
                ch = db.query(Charger).filter_by(id=contact.nearest_charger_id).first()
                charger_city = ch.city if ch else None
            _vars = _SD(
                name=contact.name or "",
                address=contact.address or "",
                city=charger_city or "",
                state=extract_state_from_address(contact.address or "") or "",
            )

            tmpl_body = outbound.body_html or ""
            if outbound.template_name:
                tmpl_obj = db.query(Template).filter_by(name=outbound.template_name).first()
                if tmpl_obj:
                    tmpl_body = _render(tmpl_obj.body_md.format_map(_vars))
            ok = send_email(
                creds, contact.email_primary, outbound.subject or "", tmpl_body
            )
            outbound.status = "sent" if ok else "failed"
        except Exception as e:
            outbound.status = "failed"
            outbound.error_message = str(e)
        results.append({"contact_id": outbound.contact_id, "status": outbound.status})
    db.commit()
    sent_count = sum(1 for r in results if r["status"] == "sent")
    return {"sent": sent_count, "results": results}


class ContactFixIn(BaseModel):
    name: str
    email: str
    address: str


@router.post("/{contact_id}/fix", response_model=ContactOut)
def fix_contact(contact_id: str, body: ContactFixIn, db: DbDep):
    """Manually set fields on an unparsed (or any) contact, then geocode + route it."""
    contact = db.query(Contact).filter_by(id=contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    contact.name = body.name
    contact.email_primary = body.email
    contact.address = body.address
    contact.parse_status = "parsed"

    # Geocode and find nearest charger
    from src.itselectric.geo import extract_state_from_address, find_nearest_charger, geocode_address
    from server.models import GeoCache

    chargers_rows = db.query(Charger).all()
    chargers = [
        {"db_id": c.id, "name": c.street, "city": c.city, "state": c.state,
         "lat": c.lat, "lon": c.lon}
        for c in chargers_rows
    ]

    cached = db.query(GeoCache).filter_by(address=body.address).first()
    if cached:
        coords = (cached.lat, cached.lon)
    else:
        coords = geocode_address(body.address)
        if coords:
            db.add(GeoCache(address=body.address, lat=coords[0], lon=coords[1]))
            db.flush()
    nearest_charger_row = None
    dist_float = None
    charger_city = None
    driver_state = extract_state_from_address(body.address)

    if coords:
        lat, lon = coords
        result = find_nearest_charger(lat, lon, chargers)
        if result:
            nearest_dict, dist_float = result
            nearest_charger_row = db.query(Charger).filter_by(id=nearest_dict["db_id"]).first()
            contact.nearest_charger_id = nearest_charger_row.id if nearest_charger_row else None
            contact.distance_miles = dist_float
            charger_city = nearest_dict["city"]

    # Re-run decision tree routing
    import json
    _tree_row = db.query(AppConfig).filter_by(key="__decision_tree_json__").first()
    decision_tree = json.loads(_tree_row.value) if _tree_row else None

    if decision_tree and nearest_charger_row and dist_float is not None:
        from src.itselectric.decision_tree import evaluate as evaluate_tree

        ctx = {
            "driver_state": driver_state,
            "charger_state": nearest_charger_row.state,
            "charger_city": charger_city,
            "distance_miles": dist_float,
        }
        try:
            template_name = evaluate_tree(decision_tree, ctx)
        except (KeyError, ValueError):
            template_name = None

        if template_name:
            tmpl = db.query(Template).filter_by(name=template_name).first()
            subject = tmpl.subject if tmpl else ""
            md = tmpl.body_md if tmpl else ""

            class _SD(dict):
                def __missing__(self, key: str) -> str:
                    return f'{{{key}}}'

            md = md.format_map(_SD(
                name=body.name,
                address=body.address,
                city=charger_city or "",
                state=driver_state or "",
            ))
            # Replace any existing pending outbound, or create new
            existing = db.query(OutboundEmail).filter_by(contact_id=contact_id, status="pending").first()
            if existing:
                existing.template_name = template_name
                existing.routed_template = template_name
                existing.subject = subject
                existing.body_html = md
            else:
                db.add(OutboundEmail(
                    contact_id=contact_id,
                    template_name=template_name,
                    routed_template=template_name,
                    subject=subject,
                    body_html=md,
                    status="pending",
                ))

    db.commit()
    out = ContactOut.model_validate(contact)
    latest = db.query(OutboundEmail).filter_by(contact_id=contact_id).order_by(OutboundEmail.id.desc()).first()
    out.outbound_status = latest.status if latest else None
    return out
