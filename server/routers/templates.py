"""Email templates CRUD API."""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session, sessionmaker

from server.models import Template
from server.schemas import TemplateIn, TemplateOut

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


class PreviewIn(BaseModel):
    body_md: str


@router.post("/preview", response_class=HTMLResponse)
def preview_template(body: PreviewIn):
    from src.itselectric.email_layout import render_email
    return render_email(body.body_md)


@router.get("", response_model=list[TemplateOut])
def list_templates(db: DbDep):
    return db.query(Template).order_by(Template.name).all()


@router.get("/{name}", response_model=TemplateOut)
def get_template(name: str, db: DbDep):
    tmpl = db.query(Template).filter_by(name=name).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return tmpl


@router.post("/{name}", response_model=TemplateOut)
def create_template(name: str, body: TemplateIn, db: DbDep):
    if db.query(Template).filter_by(name=name).first():
        raise HTTPException(status_code=409, detail="Template already exists")
    tmpl = Template(
        name=name,
        subject=body.subject,
        body_md=body.body_md,
        updated_at=datetime.now(timezone.utc),
    )
    db.add(tmpl)
    db.commit()
    db.refresh(tmpl)
    return tmpl


@router.put("/{name}", response_model=TemplateOut)
def update_template(name: str, body: TemplateIn, db: DbDep):
    tmpl = db.query(Template).filter_by(name=name).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    tmpl.subject = body.subject
    tmpl.body_md = body.body_md
    tmpl.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(tmpl)
    return tmpl


@router.delete("/{name}")
def delete_template(name: str, db: DbDep):
    tmpl = db.query(Template).filter_by(name=name).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(tmpl)
    db.commit()
    return {"ok": True}
