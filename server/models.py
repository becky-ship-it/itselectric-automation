import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # Gmail message ID
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    address: Mapped[str | None] = mapped_column(String, nullable=True)
    email_primary: Mapped[str | None] = mapped_column(String, nullable=True)
    email_form: Mapped[str | None] = mapped_column(String, nullable=True)
    raw_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    parse_status: Mapped[str] = mapped_column(String, default="unparsed")
    nearest_charger_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("chargers.id"), nullable=True
    )
    distance_miles: Mapped[float | None] = mapped_column(Float, nullable=True)
    geocache_hit: Mapped[bool] = mapped_column(Boolean, default=False)
    hubspot_status: Mapped[str] = mapped_column(String, default="skipped")

    charger: Mapped["Charger | None"] = relationship("Charger", back_populates="contacts")
    outbound_emails: Mapped[list["OutboundEmail"]] = relationship(
        "OutboundEmail", back_populates="contact"
    )


class OutboundEmail(Base):
    __tablename__ = "outbound_emails"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    contact_id: Mapped[str] = mapped_column(String, ForeignKey("contacts.id"))
    template_name: Mapped[str | None] = mapped_column(String, nullable=True)
    routed_template: Mapped[str | None] = mapped_column(String, nullable=True)
    subject: Mapped[str | None] = mapped_column(String, nullable=True)
    body_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending")
    sent_by: Mapped[str] = mapped_column(String, default="manual")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    contact: Mapped["Contact"] = relationship("Contact", back_populates="outbound_emails")


class Charger(Base):
    __tablename__ = "chargers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    street: Mapped[str] = mapped_column(String)
    city: Mapped[str] = mapped_column(String)
    state: Mapped[str] = mapped_column(String)
    zipcode: Mapped[str | None] = mapped_column(String, nullable=True)
    charger_id: Mapped[str | None] = mapped_column(String, nullable=True)
    num_chargers: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)

    contacts: Mapped[list["Contact"]] = relationship("Contact", back_populates="charger")


class Template(Base):
    __tablename__ = "templates"

    name: Mapped[str] = mapped_column(String, primary_key=True)
    subject: Mapped[str] = mapped_column(String, default="")
    # Column name kept as 'body_html' in DB to avoid a schema migration
    body_md: Mapped[str] = mapped_column("body_html", Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class GeoCache(Base):
    __tablename__ = "geocache"

    address: Mapped[str] = mapped_column(String, primary_key=True)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)


class AppConfig(Base):
    __tablename__ = "app_config"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
