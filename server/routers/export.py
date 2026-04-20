"""Export and import API endpoints."""

import csv
import io
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, sessionmaker

from server.models import Charger, Contact, GeoCache, OutboundEmail, Template

router = APIRouter()

_pending_imports: dict[str, dict] = {}


def get_db():
    from server.db import get_engine
    from server.main import DB_URL

    s = sessionmaker(bind=get_engine(DB_URL))()
    try:
        yield s
    finally:
        s.close()


DbDep = Annotated[Session, Depends(get_db)]


@router.get("/export/snapshot")
def export_snapshot(db: DbDep):
    def _contact(c: Contact):
        return {
            "id": c.id,
            "received_at": c.received_at.isoformat() if c.received_at else None,
            "name": c.name,
            "address": c.address,
            "email_primary": c.email_primary,
            "email_form": c.email_form,
            "raw_body": c.raw_body,
            "parse_status": c.parse_status,
            "nearest_charger_id": c.nearest_charger_id,
            "distance_miles": c.distance_miles,
            "hubspot_status": c.hubspot_status,
        }

    def _outbound(e: OutboundEmail):
        return {
            "id": e.id,
            "contact_id": e.contact_id,
            "template_name": e.template_name,
            "routed_template": e.routed_template,
            "subject": e.subject,
            "body_html": e.body_html,
            "sent_at": e.sent_at.isoformat() if e.sent_at else None,
            "status": e.status,
            "sent_by": e.sent_by,
            "error_message": e.error_message,
        }

    return {
        "contacts": [_contact(c) for c in db.query(Contact).all()],
        "outbound_emails": [_outbound(e) for e in db.query(OutboundEmail).all()],
        "chargers": [
            {
                "street": c.street,
                "city": c.city,
                "state": c.state,
                "zipcode": c.zipcode,
                "charger_id": c.charger_id,
                "num_chargers": c.num_chargers,
                "lat": c.lat,
                "lon": c.lon,
            }
            for c in db.query(Charger).all()
        ],
        "templates": [
            {"name": t.name, "subject": t.subject, "body_md": t.body_md}
            for t in db.query(Template).all()
        ],
        "geocache": [
            {"address": g.address, "lat": g.lat, "lon": g.lon}
            for g in db.query(GeoCache).all()
        ],
    }


@router.get("/export/csv")
def export_csv(db: DbDep):
    headers = [
        "Sent Date",
        "Name",
        "Address",
        "Email 1",
        "Email 2",
        "Content",
        "Nearest Charger",
        "Distance (mi)",
        "HubSpot Contact",
        "Email Sent",
    ]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)

    for c in db.query(Contact).order_by(Contact.received_at.desc()).all():
        charger = (
            db.query(Charger).filter_by(id=c.nearest_charger_id).first()
            if c.nearest_charger_id
            else None
        )
        outbound = (
            db.query(OutboundEmail)
            .filter_by(contact_id=c.id)
            .order_by(OutboundEmail.created_at.desc())
            .first()
        )
        writer.writerow(
            [
                c.received_at.strftime("%Y-%m-%d %H:%M:%S UTC") if c.received_at else "",
                c.name or "",
                c.address or "",
                c.email_primary or "",
                c.email_form or "",
                (c.raw_body or "")[:5000],
                f"{charger.street}, {charger.city}, {charger.state}" if charger else "",
                str(c.distance_miles) if c.distance_miles else "",
                c.hubspot_status or "",
                outbound.template_name if outbound else "",
            ]
        )

    output.seek(0)
    return StreamingResponse(
        iter([output.read()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=itselectric_export.csv"},
    )


@router.post("/import/snapshot")
def import_snapshot_preview(body: dict[str, Any], db: DbDep):
    import_id = str(uuid.uuid4())
    _pending_imports[import_id] = body

    new_chargers = len(
        [
            c
            for c in body.get("chargers", [])
            if not db.query(Charger)
            .filter_by(street=c["street"], city=c["city"], state=c["state"])
            .first()
        ]
    )
    new_contacts = len(
        [
            c
            for c in body.get("contacts", [])
            if not db.query(Contact).filter_by(id=c["id"]).first()
        ]
    )
    new_templates = len(
        [
            t
            for t in body.get("templates", [])
            if not db.query(Template).filter_by(name=t["name"]).first()
        ]
    )

    return {
        "import_id": import_id,
        "preview": {
            "new_chargers": new_chargers,
            "new_contacts": new_contacts,
            "new_templates": new_templates,
        },
    }


@router.post("/import/snapshot/confirm/{import_id}")
def import_snapshot_confirm(import_id: str, db: DbDep):
    body = _pending_imports.pop(import_id, None)
    if not body:
        raise HTTPException(status_code=404, detail="Import not found or already confirmed")

    for c in body.get("chargers", []):
        if (
            not db.query(Charger)
            .filter_by(street=c["street"], city=c["city"], state=c["state"])
            .first()
        ):
            db.add(Charger(**{k: v for k, v in c.items() if k != "id"}))

    for t in body.get("templates", []):
        if not db.query(Template).filter_by(name=t["name"]).first():
            db.add(
                Template(
                    name=t["name"],
                    subject=t.get("subject", ""),
                    body_md=t.get("body_md", ""),
                )
            )

    for g in body.get("geocache", []):
        if not db.query(GeoCache).filter_by(address=g["address"]).first():
            db.add(GeoCache(address=g["address"], lat=g["lat"], lon=g["lon"]))

    db.commit()
    return {"ok": True}
