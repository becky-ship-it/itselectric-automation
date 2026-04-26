from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ChargerOut(BaseModel):
    id: int
    street: str
    city: str
    state: str
    zipcode: str | None
    num_chargers: int | None
    lat: float
    lon: float

    model_config = {"from_attributes": True}


class TemplateOut(BaseModel):
    name: str
    subject: str
    body_md: str
    updated_at: datetime

    model_config = {"from_attributes": True}


class TemplateIn(BaseModel):
    subject: str
    body_md: str


class ContactOut(BaseModel):
    id: str
    received_at: datetime | None
    name: str | None
    address: str | None
    email_primary: str | None
    email_form: str | None
    raw_body: str | None
    parse_status: str
    nearest_charger_id: int | None
    distance_miles: float | None
    geocache_hit: bool
    hubspot_status: str | None
    outbound_status: str | None = None

    model_config = {"from_attributes": True}


class OutboundEmailOut(BaseModel):
    id: str
    contact_id: str
    template_name: str | None
    routed_template: str | None
    subject: str | None
    body_html: str | None
    sent_at: datetime | None
    status: str
    sent_by: str
    error_message: str | None

    model_config = {"from_attributes": True}


class ConfigOut(BaseModel):
    data: dict[str, Any]


class PipelineStatusOut(BaseModel):
    status: str
    last_run_at: datetime | None
    run_id: str | None
