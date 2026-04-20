"""Contacts / inbox API endpoints."""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, sessionmaker

from server.models import AppConfig, Charger, Contact, OutboundEmail, Template
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
    return q.offset(offset).limit(limit).all()


@router.get("/{contact_id}")
def get_contact(contact_id: str, db: DbDep):
    contact = db.query(Contact).filter_by(id=contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    outbound = db.query(OutboundEmail).filter_by(contact_id=contact_id).all()
    return {
        "contact": ContactOut.model_validate(contact),
        "outbound_emails": [OutboundEmailOut.model_validate(e) for e in outbound],
    }


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

    subject = outbound.subject or ""

    if template_override:
        tmpl = db.query(Template).filter_by(name=template_override).first()
        if tmpl:
            outbound.template_name = template_override
            subject = tmpl.subject
            body = render_email(tmpl.body_md)
        else:
            body = outbound.body_html or ""
    elif outbound.template_name:
        tmpl = db.query(Template).filter_by(name=outbound.template_name).first()
        body = render_email(tmpl.body_md) if tmpl else (outbound.body_html or "")
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

            tmpl_body = outbound.body_html or ""
            if outbound.template_name:
                tmpl_obj = db.query(Template).filter_by(name=outbound.template_name).first()
                if tmpl_obj:
                    tmpl_body = _render(tmpl_obj.body_md)
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
