"""Charger locations CRUD API."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, sessionmaker

from server.models import Charger
from server.schemas import ChargerOut

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


class ChargerIn(BaseModel):
    street: str
    city: str
    state: str
    zipcode: str | None = None
    num_chargers: int | None = None
    lat: float
    lon: float


@router.get("", response_model=list[ChargerOut])
def list_chargers(db: DbDep):
    return db.query(Charger).order_by(Charger.state, Charger.city).all()


@router.post("", response_model=ChargerOut)
def create_charger(body: ChargerIn, db: DbDep):
    charger = Charger(**body.model_dump())
    db.add(charger)
    db.commit()
    db.refresh(charger)
    return charger


@router.put("/{charger_id}", response_model=ChargerOut)
def update_charger(charger_id: int, body: ChargerIn, db: DbDep):
    charger = db.query(Charger).filter_by(id=charger_id).first()
    if not charger:
        raise HTTPException(status_code=404, detail="Charger not found")
    for k, v in body.model_dump().items():
        setattr(charger, k, v)
    db.commit()
    db.refresh(charger)
    return charger


@router.delete("/{charger_id}")
def delete_charger(charger_id: int, db: DbDep):
    charger = db.query(Charger).filter_by(id=charger_id).first()
    if not charger:
        raise HTTPException(status_code=404, detail="Charger not found")
    db.delete(charger)
    db.commit()
    return {"ok": True}
