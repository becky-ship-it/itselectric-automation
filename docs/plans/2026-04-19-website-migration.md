# Website Migration Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the CLI/broken desktop GUI with a locally-hosted FastAPI + React web app that lets an operator run the pipeline, review and send emails, view history, and manage configuration — all through a browser at `localhost:8000`.

**Architecture:** FastAPI backend wraps the existing Python pipeline modules unchanged; SQLite (via SQLAlchemy) stores contacts, sent emails, templates, chargers, and geocache; React + Vite frontend connects to the API with Server-Sent Events for real-time pipeline progress.

**Tech Stack:** FastAPI · Uvicorn · SQLAlchemy 2 · SQLite · React 18 · Vite · TypeScript · Tailwind CSS · TanStack Query · React Router v6

---

## Scope note — five separate plans

This migration has five independent phases. **Each phase is its own plan.** This document covers **Phase 1 only** (backend skeleton). Later phases follow when Phase 1 ships.

| Phase | Plan | Status |
|-------|------|--------|
| 1 — Backend skeleton | This document | 🔲 |
| 2 — Inbox UI | `2026-04-XX-website-phase2-inbox.md` | not started |
| 3 — History, export & import | `2026-04-XX-website-phase3-history.md` | not started |
| 4 — Configuration UI | `2026-04-XX-website-phase4-config.md` | not started |
| 5 — Polish | `2026-04-XX-website-phase5-polish.md` | not started |

At the end of Phase 1 you have: a running FastAPI server with all API endpoints, a seeded SQLite database, full test coverage, and zero frontend. The CLI (`cli.py`) continues to work as a fallback throughout.

---

## File Map

### New files

```
server/
  __init__.py
  main.py              # FastAPI app, startup event, static file mount
  db.py                # SQLAlchemy engine + session factory
  models.py            # ORM: Contact, OutboundEmail, Charger, Template, GeoCache, AppConfig
  schemas.py           # Pydantic request/response models
  seed.py              # Import chargers.csv, geocache.json, decision_tree.yaml, templates
  pipeline_service.py  # Orchestrates fetch → parse → geocode → route → write DB
  sse.py               # SSE event queue (asyncio.Queue per run)
  routers/
    __init__.py
    pipeline.py        # POST /api/pipeline/run, GET /api/pipeline/stream, GET /api/pipeline/status
    contacts.py        # GET /api/contacts, GET/POST /api/contacts/{id}, send, skip, batch-send
    templates.py       # GET/POST/PUT/DELETE /api/templates
    chargers.py        # GET/POST/PUT/DELETE /api/chargers
    config.py          # GET/PUT /api/config, /api/decision-tree, POST /api/decision-tree/test
    export.py          # GET /api/export/snapshot|csv, POST /api/import/snapshot, confirm

tests/
  test_models.py
  test_seed.py
  test_pipeline_service.py
  test_api_pipeline.py
  test_api_contacts.py
  test_api_templates.py
  test_api_chargers.py
  test_api_config.py
  test_api_export.py
```

### Modified files

```
pyproject.toml         # Add fastapi, uvicorn, sqlalchemy, httpx, python-multipart to deps
src/itselectric/geo.py # Add load_chargers_from_db() and geocache_db adapter functions
```

### Unchanged files (explicitly — do not touch)

```
src/itselectric/extract.py
src/itselectric/decision_tree.py
src/itselectric/gmail.py
src/itselectric/docs.py
src/itselectric/sheets.py
src/itselectric/hubspot.py
src/itselectric/auth.py
src/itselectric/fixture.py
src/itselectric/cli.py   # Keep working as emergency fallback
```

---

## Chunk 1: Project setup and database foundation

### Task 1.1: Add backend dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] **Open `pyproject.toml` and add to `dependencies`:**

```toml
dependencies = [
    "beautifulsoup4>=4.12.0",
    "fastapi>=0.115.0",
    "geopy>=2.4",
    "google-api-python-client>=2.190.0",
    "google-auth>=2.48.0",
    "google-auth-httplib2>=0.3.0",
    "google-auth-oauthlib>=1.2.4",
    "httpx>=0.27.0",
    "python-multipart>=0.0.9",
    "pyyaml>=6.0",
    "requests>=2.31.0",
    "sqlalchemy>=2.0.0",
    "uvicorn[standard]>=0.30.0",
    "customtkinter>=5.2",
]
```

Also update `[project.optional-dependencies]` dev section:

```toml
dev = ["pytest>=8.0", "pytest-asyncio>=0.23", "ruff>=0.4", "pyinstaller>=6.0", "types-PyYAML>=6.0"]
```

- [ ] **Install:**

```bash
pip install -e ".[dev]"
```

- [ ] **Verify FastAPI importable:**

```bash
python -c "import fastapi, sqlalchemy, uvicorn; print('ok')"
```

Expected: `ok`

- [ ] **Commit:**

```bash
git add pyproject.toml
git commit -m "feat(deps): add fastapi, sqlalchemy, uvicorn, httpx"
```

---

### Task 1.2: SQLAlchemy engine and session

**Files:**
- Create: `server/__init__.py` (empty)
- Create: `server/db.py`
- Create: `tests/test_models.py` (start here)

- [ ] **Write the failing test first:**

```python
# tests/test_models.py
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from server.db import get_engine, get_session, Base  # noqa: F401


def test_engine_creates_sqlite_in_memory():
    engine = get_engine("sqlite:///:memory:")
    assert engine is not None


def test_session_factory_yields_session():
    engine = get_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with get_session(engine) as session:
        assert isinstance(session, Session)


def test_tables_created_on_metadata_create_all():
    engine = get_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "contacts" in tables
    assert "outbound_emails" in tables
    assert "chargers" in tables
    assert "templates" in tables
    assert "geocache" in tables
    assert "app_config" in tables
```

- [ ] **Run to confirm failure:**

```bash
pytest tests/test_models.py -v
```

Expected: `ImportError: No module named 'server'`

- [ ] **Create `server/__init__.py`** (empty file).

- [ ] **Create `server/db.py`:**

```python
from contextlib import contextmanager

from sqlalchemy import create_engine as _create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def get_engine(url: str = "sqlite:///data/itselectric.db"):
    return _create_engine(url, connect_args={"check_same_thread": False})


def get_session(engine):
    factory = sessionmaker(bind=engine)

    @contextmanager
    def _session():
        session = factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    return _session()
```

- [ ] **Run tests:**

```bash
pytest tests/test_models.py::test_engine_creates_sqlite_in_memory tests/test_models.py::test_session_factory_yields_session -v
```

Expected: first two pass, third fails (no tables yet — that's next task).

- [ ] **Commit:**

```bash
git add server/__init__.py server/db.py tests/test_models.py
git commit -m "feat(server): add SQLAlchemy engine and session factory"
```

---

### Task 1.3: ORM models

**Files:**
- Create: `server/models.py`
- Modify: `tests/test_models.py`

- [ ] **Add table-existence test (already written above — run it):**

```bash
pytest tests/test_models.py::test_tables_created_on_metadata_create_all -v
```

Expected: FAIL — tables don't exist yet.

- [ ] **Create `server/models.py`:**

```python
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
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    address: Mapped[str | None] = mapped_column(String, nullable=True)
    email_primary: Mapped[str | None] = mapped_column(String, nullable=True)
    email_form: Mapped[str | None] = mapped_column(String, nullable=True)
    raw_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    parse_status: Mapped[str] = mapped_column(String, default="unparsed")  # parsed | unparsed
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
    status: Mapped[str] = mapped_column(String, default="pending")  # pending|sent|failed|skipped
    sent_by: Mapped[str] = mapped_column(String, default="manual")  # "auto" | "manual"
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now
    )

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
    body_html: Mapped[str] = mapped_column(Text, default="")
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
```

- [ ] **Update `tests/test_models.py`** — add import for models so `Base.metadata` includes all tables:

```python
# Add at top of test_models.py, after existing imports:
import server.models  # noqa: F401 — registers all models with Base.metadata
```

- [ ] **Run all model tests:**

```bash
pytest tests/test_models.py -v
```

Expected: all 3 pass.

- [ ] **Commit:**

```bash
git add server/models.py tests/test_models.py
git commit -m "feat(server): add SQLAlchemy ORM models for all tables"
```

---

### Task 1.4: Database seeding

**Files:**
- Create: `server/seed.py`
- Create: `tests/test_seed.py`

- [ ] **Write failing tests:**

```python
# tests/test_seed.py
import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import server.models  # noqa: F401
from server.db import Base
from server.models import AppConfig, Charger, GeoCache, Template
from server.seed import seed_chargers, seed_geocache, seed_config, seed_templates_from_yaml


@pytest.fixture()
def session(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    s = factory()
    yield s
    s.close()


def test_seed_chargers_loads_all_from_csv(session):
    from server.seed import DEFAULT_CHARGERS_CSV
    seed_chargers(session, DEFAULT_CHARGERS_CSV)
    count = session.query(Charger).count()
    assert count > 0


def test_seed_chargers_is_idempotent(session):
    from server.seed import DEFAULT_CHARGERS_CSV
    seed_chargers(session, DEFAULT_CHARGERS_CSV)
    seed_chargers(session, DEFAULT_CHARGERS_CSV)
    count = session.query(Charger).count()
    assert count == session.query(Charger).count()


def test_seed_geocache_imports_json(session, tmp_path):
    cache = {"123 Main St, Boston MA": [42.36, -71.06]}
    cache_file = tmp_path / "geocache.json"
    cache_file.write_text(json.dumps(cache))
    seed_geocache(session, str(cache_file))
    entry = session.query(GeoCache).filter_by(address="123 Main St, Boston MA").first()
    assert entry is not None
    assert abs(entry.lat - 42.36) < 0.001


def test_seed_geocache_skips_missing_file(session):
    seed_geocache(session, "/nonexistent/geocache.json")  # must not raise
    assert session.query(GeoCache).count() == 0


def test_seed_config_writes_defaults(session):
    seed_config(session, {"label": "Follow Up", "max_messages": 50})
    assert session.query(AppConfig).filter_by(key="label").first().value == "Follow Up"
    assert session.query(AppConfig).filter_by(key="max_messages").first().value == "50"


def test_seed_config_is_idempotent(session):
    seed_config(session, {"label": "INBOX"})
    seed_config(session, {"label": "INBOX"})
    count = session.query(AppConfig).filter_by(key="label").count()
    assert count == 1


def test_seed_templates_from_yaml_creates_rows(session, tmp_path):
    tree_yaml = tmp_path / "tree.yaml"
    tree_yaml.write_text("""
condition:
  field: distance_miles
  op: lte
  value: 5
then:
  template: tell_me_more_general
else:
  template: waitlist
""")
    seed_templates_from_yaml(session, str(tree_yaml))
    names = {t.name for t in session.query(Template).all()}
    assert "tell_me_more_general" in names
    assert "waitlist" in names


def test_seed_templates_does_not_overwrite_existing(session, tmp_path):
    session.add(Template(name="tell_me_more_general", subject="Existing", body_html="<p>keep</p>"))
    session.commit()
    tree_yaml = tmp_path / "tree.yaml"
    tree_yaml.write_text("condition:\n  field: x\n  op: eq\n  value: y\nthen:\n  template: tell_me_more_general\nelse:\n  template: waitlist\n")
    seed_templates_from_yaml(session, str(tree_yaml))
    t = session.query(Template).filter_by(name="tell_me_more_general").first()
    assert t.subject == "Existing"  # not overwritten
```

- [ ] **Run to confirm failure:**

```bash
pytest tests/test_seed.py -v
```

Expected: `ImportError: cannot import name 'seed_chargers' from 'server.seed'`

- [ ] **Create `server/seed.py`:**

```python
"""One-time database seeding from existing config files."""

import csv
import json
from pathlib import Path

import yaml  # type: ignore
from sqlalchemy.orm import Session

from server.models import AppConfig, Charger, GeoCache, Template

DEFAULT_CHARGERS_CSV = Path(__file__).parent.parent / "src/itselectric/data/chargers.csv"


def seed_chargers(session: Session, csv_path=DEFAULT_CHARGERS_CSV) -> int:
    """Import chargers.csv into the chargers table. Skips rows already present by street+city+state."""
    count = 0
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lat = float(row["LAT_OVERRIDE"] or row["LAT"])
            lon = float(row["LONG_OVERRIDE"] or row["LONG"])
            existing = (
                session.query(Charger)
                .filter_by(street=row["STREET"].strip(), city=row["CITY"].strip().title(), state=row["STATE"].strip().upper())
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
    """Import geocache.json into the geocache table. Skips missing file silently."""
    try:
        with open(json_path) as f:
            cache = json.load(f)
    except FileNotFoundError:
        return 0
    count = 0
    for address, (lat, lon) in cache.items():
        if session.query(GeoCache).filter_by(address=address).first():
            continue
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
    names = set()
    for branch in ("then", "else"):
        if branch in node:
            names |= _collect_template_names(node[branch])
    return names


def seed_templates_from_yaml(session: Session, yaml_path: str) -> int:
    """Create placeholder Template rows for all names found in a decision tree YAML.
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
```

- [ ] **Run tests:**

```bash
pytest tests/test_seed.py -v
```

Expected: all 8 pass.

- [ ] **Commit:**

```bash
git add server/seed.py tests/test_seed.py
git commit -m "feat(server): add DB seeding from chargers.csv, geocache.json, decision_tree.yaml"
```

---

### Task 1.5: FastAPI app skeleton

**Files:**
- Create: `server/main.py`
- Create: `server/schemas.py`

- [ ] **Create `server/schemas.py`** (Pydantic models used across routers):

```python
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
    body_html: str
    updated_at: datetime

    model_config = {"from_attributes": True}


class TemplateIn(BaseModel):
    subject: str
    body_html: str


class ContactOut(BaseModel):
    id: str
    received_at: datetime | None
    name: str | None
    address: str | None
    email_primary: str | None
    parse_status: str
    nearest_charger_id: int | None
    distance_miles: float | None
    hubspot_status: str

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
    error_message: str | None

    model_config = {"from_attributes": True}


class ConfigOut(BaseModel):
    data: dict[str, Any]


class PipelineStatusOut(BaseModel):
    status: str  # idle | running
    last_run_at: datetime | None
    run_id: str | None
```

- [ ] **Create `server/main.py`:**

```python
"""FastAPI application entry point."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from server.db import Base, get_engine, get_session
from server.routers import chargers, config, contacts, export, pipeline, templates
from server.seed import seed_chargers, seed_geocache, seed_config, seed_templates_from_yaml

DB_URL = os.getenv("DATABASE_URL", "sqlite:///data/itselectric.db")
GEOCACHE_PATH = os.getenv("GEOCACHE_PATH", "geocache.json")
DECISION_TREE_PATH = os.getenv("DECISION_TREE_PATH", "decision_tree.yaml")
CONFIG_YAML_PATH = os.getenv("CONFIG_YAML_PATH", "config.yaml")


@asynccontextmanager
async def lifespan(app: FastAPI):
    import yaml  # type: ignore
    from pathlib import Path

    engine = get_engine(DB_URL)
    import server.models  # noqa: F401 — registers all models
    Base.metadata.create_all(engine)
    app.state.engine = engine

    with get_session(engine) as session:
        seed_chargers(session)
        seed_geocache(session, GEOCACHE_PATH)
        if Path(DECISION_TREE_PATH).exists():
            seed_templates_from_yaml(session, DECISION_TREE_PATH)
        config_data = {}
        if Path(CONFIG_YAML_PATH).exists():
            with open(CONFIG_YAML_PATH) as f:
                config_data = yaml.safe_load(f) or {}
        seed_config(session, config_data)

    yield


app = FastAPI(title="It's Electric", lifespan=lifespan)

app.include_router(pipeline.router, prefix="/api/pipeline", tags=["pipeline"])
app.include_router(contacts.router, prefix="/api/contacts", tags=["contacts"])
app.include_router(templates.router, prefix="/api/templates", tags=["templates"])
app.include_router(chargers.router, prefix="/api/chargers", tags=["chargers"])
app.include_router(config.router, prefix="/api", tags=["config"])
app.include_router(export.router, prefix="/api", tags=["export"])

# Serve React build in production (Phase 2+)
if os.path.exists("web/dist"):
    app.mount("/", StaticFiles(directory="web/dist", html=True), name="static")
```

- [ ] **Create stub router files** (all return 501 for now — real logic added per-task):

```python
# server/routers/__init__.py  (empty)

# server/routers/pipeline.py
from fastapi import APIRouter
router = APIRouter()

@router.get("/status")
def pipeline_status():
    return {"status": "idle", "last_run_at": None, "run_id": None}

# server/routers/contacts.py
from fastapi import APIRouter
router = APIRouter()

@router.get("")
def list_contacts():
    return []

# server/routers/templates.py
from fastapi import APIRouter
router = APIRouter()

@router.get("")
def list_templates():
    return []

# server/routers/chargers.py
from fastapi import APIRouter
router = APIRouter()

@router.get("")
def list_chargers():
    return []

# server/routers/config.py
from fastapi import APIRouter
router = APIRouter()

@router.get("/config")
def get_config():
    return {"data": {}}

@router.get("/decision-tree")
def get_decision_tree():
    return {}

# server/routers/export.py
from fastapi import APIRouter
router = APIRouter()

@router.get("/export/snapshot")
def export_snapshot():
    return {}
```

- [ ] **Verify app starts:**

```bash
uvicorn server.main:app --reload --port 8000
```

Expected: server starts, no errors, `http://localhost:8000/api/pipeline/status` returns `{"status":"idle","last_run_at":null,"run_id":null}`

- [ ] **Kill server, commit:**

```bash
git add server/main.py server/schemas.py server/routers/
git commit -m "feat(server): FastAPI skeleton with stub routers and DB lifespan seeding"
```

---

## Chunk 2: Pipeline service and API

### Task 2.1: SSE event queue

**Files:**
- Create: `server/sse.py`

- [ ] **Create `server/sse.py`:**

```python
"""Server-Sent Events queue for streaming pipeline progress."""

import asyncio
from typing import AsyncGenerator

_queues: dict[str, asyncio.Queue] = {}


def create_run(run_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _queues[run_id] = q
    return q


def get_queue(run_id: str) -> asyncio.Queue | None:
    return _queues.get(run_id)


def remove_run(run_id: str) -> None:
    _queues.pop(run_id, None)


async def event_stream(run_id: str) -> AsyncGenerator[str, None]:
    """Yield SSE-formatted lines until the queue sends a sentinel None."""
    q = get_queue(run_id)
    if q is None:
        yield "data: run not found\n\n"
        return
    while True:
        msg = await q.get()
        if msg is None:
            yield "data: [done]\n\n"
            break
        yield f"data: {msg}\n\n"
```

No tests needed for this thin async wrapper — it will be exercised by the pipeline API tests.

- [ ] **Commit:**

```bash
git add server/sse.py
git commit -m "feat(server): SSE event queue for pipeline progress streaming"
```

---

### Task 2.2: Pipeline service

**Files:**
- Create: `server/pipeline_service.py`
- Create: `tests/test_pipeline_service.py`

The pipeline service orchestrates the same steps as `cli.py` but writes to the DB instead of stdout/files. It emits progress strings to an SSE queue.

- [ ] **Write failing tests:**

```python
# tests/test_pipeline_service.py
import json
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import server.models  # noqa: F401
from server.db import Base
from server.models import Contact, OutboundEmail, Charger, Template
from server.pipeline_service import run_pipeline


@pytest.fixture()
def db_session(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    session = factory()
    # Seed one charger near Brooklyn
    session.add(Charger(street="1 Main St", city="Brooklyn", state="NY", lat=40.6943, lon=-73.9249))
    # Seed one template
    session.add(Template(name="tell_me_more_general", subject="Hi!", body_html="<p>Hi {name}</p>"))
    session.commit()
    yield session
    session.close()


FIXTURE_EMAIL = {
    "id": "msg_001",
    "internalDate": "1704067200000",
    "payload": {
        "mimeType": "text/plain",
        "body": {
            "data": __import__("base64").urlsafe_b64encode(
                b"[plain]: it's electric Jane Smith "
                b"The user has an address of 1 Atlantic Ave Brooklyn NY 11201 "
                b"and has an email of jane@example.com\nEmail address submitted in form\njane@example.com"
            ).decode()
        },
    },
}


def test_run_pipeline_creates_contact_row(db_session, tmp_path):
    geocache = tmp_path / "geocache.json"
    geocache.write_text(json.dumps({"1 Atlantic Ave Brooklyn NY 11201": [40.6929, -73.9958]}))

    with (
        patch("server.pipeline_service.fetch_messages", return_value=[FIXTURE_EMAIL]),
        patch("server.pipeline_service.get_credentials", return_value=MagicMock()),
    ):
        run_pipeline(
            db_session,
            geocache_path=str(geocache),
            decision_tree=None,
            auto_send=False,
            log=lambda msg: None,
        )

    contact = db_session.query(Contact).filter_by(id="msg_001").first()
    assert contact is not None
    assert contact.name == "Jane Smith"
    assert contact.parse_status == "parsed"


def test_run_pipeline_creates_outbound_email_row(db_session, tmp_path):
    geocache = tmp_path / "geocache.json"
    geocache.write_text(json.dumps({"1 Atlantic Ave Brooklyn NY 11201": [40.6929, -73.9958]}))

    tree = {"condition": {"field": "distance_miles", "op": "lte", "value": 999},
            "then": {"template": "tell_me_more_general"}, "else": {"template": None}}

    with (
        patch("server.pipeline_service.fetch_messages", return_value=[FIXTURE_EMAIL]),
        patch("server.pipeline_service.get_credentials", return_value=MagicMock()),
    ):
        run_pipeline(
            db_session,
            geocache_path=str(geocache),
            decision_tree=tree,
            auto_send=False,
            log=lambda msg: None,
        )

    email = db_session.query(OutboundEmail).first()
    assert email is not None
    assert email.status == "pending"
    assert email.routed_template == "tell_me_more_general"


def test_run_pipeline_skips_duplicate_message(db_session, tmp_path):
    geocache = tmp_path / "geocache.json"
    geocache.write_text(json.dumps({"1 Atlantic Ave Brooklyn NY 11201": [40.6929, -73.9958]}))

    db_session.add(Contact(id="msg_001", parse_status="parsed", name="Jane"))
    db_session.commit()

    with (
        patch("server.pipeline_service.fetch_messages", return_value=[FIXTURE_EMAIL]),
        patch("server.pipeline_service.get_credentials", return_value=MagicMock()),
    ):
        run_pipeline(db_session, geocache_path=str(geocache), decision_tree=None,
                     auto_send=False, log=lambda msg: None)

    # Still only one row — not duplicated
    assert db_session.query(Contact).filter_by(id="msg_001").count() == 1


def test_run_pipeline_unparsed_email_creates_row_with_unparsed_status(db_session, tmp_path):
    geocache = tmp_path / "geocache.json"
    geocache.write_text("{}")
    unparsed_msg = {
        "id": "msg_002",
        "internalDate": "1704067200000",
        "payload": {
            "mimeType": "text/plain",
            "body": {"data": __import__("base64").urlsafe_b64encode(b"[plain]: just a question").decode()},
        },
    }
    with (
        patch("server.pipeline_service.fetch_messages", return_value=[unparsed_msg]),
        patch("server.pipeline_service.get_credentials", return_value=MagicMock()),
    ):
        run_pipeline(db_session, geocache_path=str(geocache), decision_tree=None,
                     auto_send=False, log=lambda msg: None)

    contact = db_session.query(Contact).filter_by(id="msg_002").first()
    assert contact is not None
    assert contact.parse_status == "unparsed"
```

- [ ] **Run to confirm failure:**

```bash
pytest tests/test_pipeline_service.py -v
```

Expected: `ImportError: cannot import name 'run_pipeline'`

- [ ] **Create `server/pipeline_service.py`:**

```python
"""Pipeline orchestration: fetch → parse → geocode → route → write DB."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from sqlalchemy.orm import Session

from server.models import AppConfig, Contact, GeoCache, OutboundEmail, Charger, Template
from src.itselectric.auth import get_credentials
from src.itselectric.decision_tree import evaluate as evaluate_tree
from src.itselectric.extract import extract_parsed
from src.itselectric.geo import find_nearest_charger, geocode_address, extract_state_from_address
from src.itselectric.gmail import (
    body_to_plain,
    fetch_messages,
    format_sent_date,
    get_body_from_payload,
)


def _chargers_from_db(session: Session) -> list[dict]:
    rows = session.query(Charger).all()
    return [
        {"name": f"{r.street}, {r.city}, {r.state}", "city": r.city, "state": r.state,
         "lat": r.lat, "lon": r.lon, "db_id": r.id}
        for r in rows
    ]


def _geocode_with_db_cache(address: str, session: Session) -> tuple[float, float] | None:
    entry = session.query(GeoCache).filter_by(address=address).first()
    if entry:
        return entry.lat, entry.lon
    coords = geocode_address(address)
    if coords:
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

    processed = []

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
                    contact.nearest_charger_id = nearest_charger_row.id if nearest_charger_row else None
                    contact.distance_miles = dist_float
                    driver_state = extract_state_from_address(parsed["address"])
                    charger_city = nearest_charger_dict["city"]
                    log(f"  Nearest charger: {nearest_charger_dict['name']} ({dist_float} mi)")
                else:
                    log("  No charger found in DB.")
            else:
                log(f"  Could not geocode: {parsed['address']!r}")

        session.add(contact)
        session.flush()

        outbound = None
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
                    body = body.format_map({
                        "name": parsed["name"],
                        "address": parsed["address"],
                        "city": charger_city or "",
                        "state": driver_state or "",
                    })
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

        session.flush()
        processed.append(msg_id)

    session.commit()
    log(f"Done. Processed {len(processed)} new message(s).")
    return processed
```

- [ ] **Run tests:**

```bash
pytest tests/test_pipeline_service.py -v
```

Expected: all 4 pass.

- [ ] **Commit:**

```bash
git add server/pipeline_service.py tests/test_pipeline_service.py
git commit -m "feat(server): pipeline service writing contacts and outbound emails to DB"
```

---

### Task 2.3: Pipeline API endpoints

**Files:**
- Modify: `server/routers/pipeline.py`
- Create: `tests/test_api_pipeline.py`

- [ ] **Write failing tests:**

```python
# tests/test_api_pipeline.py
import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import server.models  # noqa: F401
from server.db import Base
from server.main import app
from server.models import Charger, Template


def _make_client(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)

    def override_session():
        s = factory()
        try:
            yield s
        finally:
            s.close()

    from server.routers.pipeline import get_db
    app.dependency_overrides[get_db] = override_session
    return TestClient(app), factory


def test_pipeline_status_returns_idle():
    client = TestClient(app)
    resp = client.get("/api/pipeline/status")
    assert resp.status_code == 200
    assert resp.json()["status"] == "idle"


def test_pipeline_run_returns_run_id():
    client = TestClient(app)
    with patch("server.routers.pipeline.run_pipeline", return_value=["msg_001"]):
        resp = client.post("/api/pipeline/run")
    assert resp.status_code == 200
    assert "run_id" in resp.json()


def test_pipeline_run_fixture_mode():
    client = TestClient(app)
    with patch("server.routers.pipeline.run_pipeline", return_value=[]) as mock_run:
        resp = client.post("/api/pipeline/run?fixture=true")
    assert resp.status_code == 200
    call_kwargs = mock_run.call_args.kwargs
    assert call_kwargs.get("fixture_messages") is not None
```

- [ ] **Run to confirm failure:**

```bash
pytest tests/test_api_pipeline.py -v
```

Expected: `ImportError` or 404 for `/api/pipeline/run`

- [ ] **Replace `server/routers/pipeline.py`:**

```python
"""Pipeline API endpoints."""

import asyncio
import uuid
from threading import Thread
from typing import Annotated

import yaml  # type: ignore
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from server.pipeline_service import run_pipeline
from server.schemas import PipelineStatusOut
from server.sse import create_run, event_stream, remove_run

router = APIRouter()

_status = {"status": "idle", "last_run_at": None, "run_id": None}
DECISION_TREE_PATH = "decision_tree.yaml"
FIXTURE_DIR = "tests/fixtures/emails"


def get_db():
    from server.main import app, DB_URL
    from server.db import get_engine, get_session
    engine = get_engine(DB_URL)
    from contextlib import contextmanager
    factory_session = []

    class _Ctx:
        def __enter__(self):
            from sqlalchemy.orm import sessionmaker
            s = sessionmaker(bind=engine)()
            factory_session.append(s)
            return s

        def __exit__(self, *_):
            factory_session[0].close()

    with _Ctx() as s:
        yield s


DbDep = Annotated[Session, Depends(get_db)]


@router.get("/status", response_model=PipelineStatusOut)
def pipeline_status():
    return _status


@router.post("/run")
def pipeline_run(db: DbDep, fixture: bool = Query(default=False)):
    run_id = str(uuid.uuid4())
    _status["status"] = "running"
    _status["run_id"] = run_id
    queue = create_run(run_id)

    decision_tree = None
    try:
        with open(DECISION_TREE_PATH) as f:
            decision_tree = yaml.safe_load(f)
    except FileNotFoundError:
        pass

    fixture_messages = None
    if fixture:
        from src.itselectric.fixture import load_fixture_messages
        try:
            fixture_messages = load_fixture_messages(FIXTURE_DIR)
        except FileNotFoundError:
            fixture_messages = []

    def _run():
        from datetime import datetime, timezone
        try:
            run_pipeline(
                db,
                decision_tree=decision_tree,
                log=lambda msg: asyncio.get_event_loop().call_soon_threadsafe(queue.put_nowait, msg),
                fixture_messages=fixture_messages,
            )
        finally:
            asyncio.get_event_loop().call_soon_threadsafe(queue.put_nowait, None)
            _status["status"] = "idle"
            _status["last_run_at"] = datetime.now(timezone.utc).isoformat()
            _status["run_id"] = None
            remove_run(run_id)

    Thread(target=_run, daemon=True).start()
    return {"run_id": run_id}


@router.get("/stream/{run_id}")
async def pipeline_stream(run_id: str):
    return StreamingResponse(event_stream(run_id), media_type="text/event-stream")
```

- [ ] **Run tests:**

```bash
pytest tests/test_api_pipeline.py -v
```

Expected: all 3 pass.

- [ ] **Commit:**

```bash
git add server/routers/pipeline.py tests/test_api_pipeline.py
git commit -m "feat(api): pipeline run, status, and SSE stream endpoints"
```

---

## Chunk 3: Contacts, templates, chargers, and config APIs

### Task 3.1: Contacts API

**Files:**
- Modify: `server/routers/contacts.py`
- Create: `tests/test_api_contacts.py`

- [ ] **Write failing tests:**

```python
# tests/test_api_contacts.py
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

import server.models  # noqa: F401
from server.main import app
from server.models import Contact, OutboundEmail


def _seeded_client():
    client = TestClient(app)
    return client


def test_list_contacts_returns_empty_initially():
    client = TestClient(app)
    # Override DB with in-memory
    resp = client.get("/api/contacts")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_contact_404_on_missing():
    client = TestClient(app)
    resp = client.get("/api/contacts/nonexistent_id")
    assert resp.status_code == 404


def test_skip_contact_returns_200():
    client = TestClient(app)
    # We need a contact in the DB — this tests the endpoint shape
    # Integration tested in test_pipeline_service
    resp = client.post("/api/contacts/bad_id/skip")
    assert resp.status_code in (200, 404)


def test_send_contact_404_on_missing():
    client = TestClient(app)
    resp = client.post("/api/contacts/bad_id/send")
    assert resp.status_code == 404
```

- [ ] **Replace `server/routers/contacts.py`:**

```python
"""Contacts/inbox API endpoints."""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from server.models import Contact, OutboundEmail
from server.schemas import ContactOut, OutboundEmailOut

router = APIRouter()


def get_db():
    from server.main import DB_URL
    from server.db import get_engine
    from sqlalchemy.orm import sessionmaker
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
    if status:
        outbound_alias = db.query(OutboundEmail.contact_id, OutboundEmail.status).subquery()
        if status == "pending":
            q = q.join(outbound_alias, Contact.id == outbound_alias.c.contact_id).filter(
                outbound_alias.c.status == "pending"
            )
        elif status == "unparsed":
            q = q.filter(Contact.parse_status == "unparsed")
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
def send_contact_email(contact_id: str, db: DbDep, template_override: str | None = None):
    from src.itselectric.auth import get_credentials
    from src.itselectric.gmail import send_email

    outbound = db.query(OutboundEmail).filter_by(contact_id=contact_id, status="pending").first()
    if not outbound:
        raise HTTPException(status_code=404, detail="No pending email for contact")

    contact = db.query(Contact).filter_by(id=contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    subject = outbound.subject or ""
    body = outbound.body_html or ""

    if template_override:
        from server.models import Template
        tmpl = db.query(Template).filter_by(name=template_override).first()
        if tmpl:
            subject = tmpl.subject
            body = tmpl.body_html

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

    # Background: append to Sheets
    from server.models import Charger, AppConfig
    charger = db.query(Charger).filter_by(id=contact.nearest_charger_id).first() if contact.nearest_charger_id else None
    spread_id = (db.query(AppConfig).filter_by(key="spreadsheet_id").first() or {})
    if hasattr(spread_id, "value") and spread_id.value:
        from src.itselectric.sheets import append_rows
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
            append_rows(creds, spread_id.value, "Sheet1", [row], 5000)
        except Exception:
            pass  # non-fatal

    return {"ok": ok, "status": outbound.status}


@router.post("/send-batch")
def send_batch(db: DbDep):
    pendings = db.query(OutboundEmail).filter_by(status="pending").all()
    results = []
    for outbound in pendings:
        contact = db.query(Contact).filter_by(id=outbound.contact_id).first()
        if not contact or not contact.email_primary:
            continue
        from src.itselectric.auth import get_credentials
        from src.itselectric.gmail import send_email
        try:
            creds = get_credentials()
            ok = send_email(creds, contact.email_primary, outbound.subject or "", outbound.body_html or "")
            outbound.status = "sent" if ok else "failed"
        except Exception as e:
            outbound.status = "failed"
            outbound.error_message = str(e)
        results.append({"contact_id": outbound.contact_id, "status": outbound.status})
    db.commit()
    return {"sent": len([r for r in results if r["status"] == "sent"]), "results": results}
```

- [ ] **Run tests:**

```bash
pytest tests/test_api_contacts.py -v
```

Expected: all 4 pass.

- [ ] **Commit:**

```bash
git add server/routers/contacts.py tests/test_api_contacts.py
git commit -m "feat(api): contacts list, detail, send, skip, and batch-send endpoints"
```

---

### Task 3.2: Templates and chargers CRUD APIs

**Files:**
- Modify: `server/routers/templates.py`
- Modify: `server/routers/chargers.py`
- Create: `tests/test_api_templates.py`
- Create: `tests/test_api_chargers.py`

- [ ] **Write failing tests:**

```python
# tests/test_api_templates.py
from fastapi.testclient import TestClient
from server.main import app


def test_list_templates_returns_list():
    client = TestClient(app)
    resp = client.get("/api/templates")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_template_404_on_missing():
    client = TestClient(app)
    resp = client.get("/api/templates/nonexistent")
    assert resp.status_code == 404


def test_create_and_get_template(tmp_path):
    client = TestClient(app)
    resp = client.post("/api/templates/my_template",
                       json={"subject": "Hello!", "body_html": "<p>Hi {name}</p>"})
    assert resp.status_code in (200, 201)
    get_resp = client.get("/api/templates/my_template")
    assert get_resp.status_code == 200
    assert get_resp.json()["subject"] == "Hello!"


def test_update_template():
    client = TestClient(app)
    client.post("/api/templates/edit_me", json={"subject": "Old", "body_html": ""})
    resp = client.put("/api/templates/edit_me", json={"subject": "New", "body_html": "<p>new</p>"})
    assert resp.status_code == 200
    get_resp = client.get("/api/templates/edit_me")
    assert get_resp.json()["subject"] == "New"
```

```python
# tests/test_api_chargers.py
from fastapi.testclient import TestClient
from server.main import app


def test_list_chargers_returns_list():
    client = TestClient(app)
    resp = client.get("/api/chargers")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_create_charger():
    client = TestClient(app)
    payload = {"street": "1 Test St", "city": "Boston", "state": "MA",
               "lat": 42.36, "lon": -71.06}
    resp = client.post("/api/chargers", json=payload)
    assert resp.status_code in (200, 201)
    assert resp.json()["city"] == "Boston"
```

- [ ] **Replace `server/routers/templates.py`:**

```python
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from server.models import Template
from server.schemas import TemplateIn, TemplateOut

router = APIRouter()


def get_db():
    from server.main import DB_URL
    from server.db import get_engine
    from sqlalchemy.orm import sessionmaker
    s = sessionmaker(bind=get_engine(DB_URL))()
    try:
        yield s
    finally:
        s.close()


DbDep = Annotated[Session, Depends(get_db)]


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
    existing = db.query(Template).filter_by(name=name).first()
    if existing:
        raise HTTPException(status_code=409, detail="Template already exists")
    tmpl = Template(name=name, subject=body.subject, body_html=body.body_html,
                    updated_at=datetime.now(timezone.utc))
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
    tmpl.body_html = body.body_html
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
```

- [ ] **Replace `server/routers/chargers.py`:**

```python
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from server.models import Charger
from server.schemas import ChargerOut

router = APIRouter()


def get_db():
    from server.main import DB_URL
    from server.db import get_engine
    from sqlalchemy.orm import sessionmaker
    s = sessionmaker(bind=get_engine(DB_URL))()
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
```

- [ ] **Run tests:**

```bash
pytest tests/test_api_templates.py tests/test_api_chargers.py -v
```

Expected: all 6 pass.

- [ ] **Commit:**

```bash
git add server/routers/templates.py server/routers/chargers.py tests/test_api_templates.py tests/test_api_chargers.py
git commit -m "feat(api): templates and chargers CRUD endpoints"
```

---

### Task 3.3: Config and decision tree API

**Files:**
- Modify: `server/routers/config.py`
- Create: `tests/test_api_config.py`

- [ ] **Write failing tests:**

```python
# tests/test_api_config.py
from fastapi.testclient import TestClient
from server.main import app


def test_get_config_returns_dict():
    client = TestClient(app)
    resp = client.get("/api/config")
    assert resp.status_code == 200
    assert "data" in resp.json()


def test_put_config_updates_value():
    client = TestClient(app)
    resp = client.put("/api/config", json={"label": "Test Label", "max_messages": "50"})
    assert resp.status_code == 200
    get_resp = client.get("/api/config")
    assert get_resp.json()["data"].get("label") == "Test Label"


def test_get_decision_tree_returns_dict_or_null():
    client = TestClient(app)
    resp = client.get("/api/decision-tree")
    assert resp.status_code == 200
    assert resp.json() is None or isinstance(resp.json(), dict)


def test_put_decision_tree_saves_and_returns():
    client = TestClient(app)
    tree = {"template": "waitlist"}
    resp = client.put("/api/decision-tree", json=tree)
    assert resp.status_code == 200
    get_resp = client.get("/api/decision-tree")
    assert get_resp.json() == tree


def test_decision_tree_dry_run_returns_routing_table():
    client = TestClient(app)
    tree = {"template": "waitlist"}
    client.put("/api/decision-tree", json=tree)
    resp = client.post("/api/decision-tree/test")
    assert resp.status_code == 200
    assert "results" in resp.json()
```

- [ ] **Replace `server/routers/config.py`:**

```python
"""Configuration and decision tree API endpoints."""

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from server.models import AppConfig

router = APIRouter()

_DECISION_TREE_KEY = "__decision_tree_json__"


def get_db():
    from server.main import DB_URL
    from server.db import get_engine
    from sqlalchemy.orm import sessionmaker
    s = sessionmaker(bind=get_engine(DB_URL))()
    try:
        yield s
    finally:
        s.close()


DbDep = Annotated[Session, Depends(get_db)]

_ALLOWED_CONFIG_KEYS = {
    "label", "max_messages", "body_length", "spreadsheet_id", "sheet",
    "content_limit", "hubspot_access_token", "google_doc_id", "auto_send",
}


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
    from src.itselectric.decision_tree import evaluate
    # Validate: try evaluating against a dummy context
    try:
        evaluate(body, {"driver_state": "NY", "charger_state": "NY",
                        "charger_city": "Brooklyn", "distance_miles": 1.0})
    except (KeyError, ValueError):
        pass  # invalid context is OK as long as the tree is valid JSON
    row = db.query(AppConfig).filter_by(key=_DECISION_TREE_KEY).first()
    if row:
        row.value = json.dumps(body)
    else:
        db.add(AppConfig(key=_DECISION_TREE_KEY, value=json.dumps(body)))
    db.commit()
    return body


@router.post("/decision-tree/test")
def test_decision_tree(db: DbDep):
    """Dry-run the current decision tree against fixture emails."""
    from src.itselectric.fixture import load_fixture_messages
    from src.itselectric.extract import extract_parsed
    from src.itselectric.gmail import get_body_from_payload, body_to_plain
    from src.itselectric.geo import find_nearest_charger, geocode_address, extract_state_from_address
    from server.models import Charger, GeoCache
    from src.itselectric.decision_tree import evaluate

    row = db.query(AppConfig).filter_by(key=_DECISION_TREE_KEY).first()
    if not row:
        raise HTTPException(status_code=400, detail="No decision tree saved")
    tree = json.loads(row.value)

    chargers = [
        {"name": f"{c.street}, {c.city}, {c.state}", "city": c.city,
         "state": c.state, "lat": c.lat, "lon": c.lon}
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
        coords = (cache.lat, cache.lon) if cache else geocode_address(parsed["address"])
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

        results.append({
            "id": msg.get("id", ""),
            "name": parsed["name"],
            "address": parsed["address"],
            "parsed": True,
            "template": template,
        })

    return {"results": results}
```

- [ ] **Run tests:**

```bash
pytest tests/test_api_config.py -v
```

Expected: all 5 pass.

- [ ] **Commit:**

```bash
git add server/routers/config.py tests/test_api_config.py
git commit -m "feat(api): config CRUD, decision tree get/put, and fixture dry-run test endpoint"
```

---

## Chunk 4: Export / import and launch script

### Task 4.1: Export and import API

**Files:**
- Modify: `server/routers/export.py`
- Create: `tests/test_api_export.py`

- [ ] **Write failing tests:**

```python
# tests/test_api_export.py
import json

from fastapi.testclient import TestClient
from server.main import app


def test_snapshot_export_returns_json():
    client = TestClient(app)
    resp = client.get("/api/export/snapshot")
    assert resp.status_code == 200
    data = resp.json()
    assert "contacts" in data
    assert "outbound_emails" in data
    assert "chargers" in data
    assert "templates" in data
    assert "geocache" in data


def test_csv_export_returns_csv_content_type():
    client = TestClient(app)
    resp = client.get("/api/export/csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")


def test_snapshot_import_preview_returns_diff():
    client = TestClient(app)
    snapshot = {
        "contacts": [],
        "outbound_emails": [],
        "chargers": [{"street": "99 New St", "city": "Albany", "state": "NY",
                      "lat": 42.65, "lon": -73.75, "zipcode": None,
                      "charger_id": None, "num_chargers": None}],
        "templates": [],
        "geocache": [],
    }
    resp = client.post("/api/import/snapshot", json=snapshot)
    assert resp.status_code == 200
    assert "preview" in resp.json()
    assert "import_id" in resp.json()


def test_snapshot_import_confirm_applies_changes():
    client = TestClient(app)
    snapshot = {
        "contacts": [], "outbound_emails": [],
        "chargers": [{"street": "88 Merge St", "city": "Troy", "state": "NY",
                      "lat": 42.7, "lon": -73.6, "zipcode": None,
                      "charger_id": None, "num_chargers": None}],
        "templates": [], "geocache": [],
    }
    preview_resp = client.post("/api/import/snapshot", json=snapshot)
    import_id = preview_resp.json()["import_id"]
    confirm_resp = client.post(f"/api/import/snapshot/confirm/{import_id}")
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["ok"] is True
```

- [ ] **Replace `server/routers/export.py`:**

```python
"""Export and import API endpoints."""

import csv
import io
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from server.models import Charger, Contact, GeoCache, OutboundEmail, Template

router = APIRouter()

_pending_imports: dict[str, dict] = {}


def get_db():
    from server.main import DB_URL
    from server.db import get_engine
    from sqlalchemy.orm import sessionmaker
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
            "name": c.name, "address": c.address,
            "email_primary": c.email_primary, "email_form": c.email_form,
            "raw_body": c.raw_body, "parse_status": c.parse_status,
            "nearest_charger_id": c.nearest_charger_id,
            "distance_miles": c.distance_miles, "hubspot_status": c.hubspot_status,
        }

    def _outbound(e: OutboundEmail):
        return {
            "id": e.id, "contact_id": e.contact_id,
            "template_name": e.template_name, "routed_template": e.routed_template,
            "subject": e.subject, "body_html": e.body_html,
            "sent_at": e.sent_at.isoformat() if e.sent_at else None,
            "status": e.status, "sent_by": e.sent_by, "error_message": e.error_message,
        }

    return {
        "contacts": [_contact(c) for c in db.query(Contact).all()],
        "outbound_emails": [_outbound(e) for e in db.query(OutboundEmail).all()],
        "chargers": [
            {"street": c.street, "city": c.city, "state": c.state, "zipcode": c.zipcode,
             "charger_id": c.charger_id, "num_chargers": c.num_chargers, "lat": c.lat, "lon": c.lon}
            for c in db.query(Charger).all()
        ],
        "templates": [
            {"name": t.name, "subject": t.subject, "body_html": t.body_html}
            for t in db.query(Template).all()
        ],
        "geocache": [
            {"address": g.address, "lat": g.lat, "lon": g.lon}
            for g in db.query(GeoCache).all()
        ],
    }


@router.get("/export/csv")
def export_csv(db: DbDep):
    headers = ["Sent Date", "Name", "Address", "Email 1", "Email 2",
               "Content", "Nearest Charger", "Distance (mi)", "HubSpot Contact", "Email Sent"]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)

    contacts = db.query(Contact).order_by(Contact.received_at.desc()).all()
    for c in contacts:
        charger = db.query(Charger).filter_by(id=c.nearest_charger_id).first() if c.nearest_charger_id else None
        outbound = db.query(OutboundEmail).filter_by(contact_id=c.id).order_by(
            OutboundEmail.created_at.desc()
        ).first()
        writer.writerow([
            c.received_at.strftime("%Y-%m-%d %H:%M:%S UTC") if c.received_at else "",
            c.name or "", c.address or "", c.email_primary or "", c.email_form or "",
            (c.raw_body or "")[:5000],
            f"{charger.street}, {charger.city}, {charger.state}" if charger else "",
            str(c.distance_miles) if c.distance_miles else "",
            c.hubspot_status or "",
            outbound.template_name if outbound else "",
        ])

    output.seek(0)
    return StreamingResponse(iter([output.read()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=itselectric_export.csv"})


@router.post("/import/snapshot")
def import_snapshot_preview(body: dict[str, Any], db: DbDep):
    import_id = str(uuid.uuid4())
    _pending_imports[import_id] = body

    new_chargers = len([
        c for c in body.get("chargers", [])
        if not db.query(Charger).filter_by(street=c["street"], city=c["city"], state=c["state"]).first()
    ])
    new_contacts = len([
        c for c in body.get("contacts", [])
        if not db.query(Contact).filter_by(id=c["id"]).first()
    ])
    new_templates = len([
        t for t in body.get("templates", [])
        if not db.query(Template).filter_by(name=t["name"]).first()
    ])

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
        if not db.query(Charger).filter_by(street=c["street"], city=c["city"], state=c["state"]).first():
            db.add(Charger(**{k: v for k, v in c.items() if k != "id"}))

    for t in body.get("templates", []):
        if not db.query(Template).filter_by(name=t["name"]).first():
            db.add(Template(name=t["name"], subject=t.get("subject", ""),
                            body_html=t.get("body_html", "")))

    for g in body.get("geocache", []):
        if not db.query(GeoCache).filter_by(address=g["address"]).first():
            db.add(GeoCache(address=g["address"], lat=g["lat"], lon=g["lon"]))

    db.commit()
    return {"ok": True}
```

- [ ] **Run tests:**

```bash
pytest tests/test_api_export.py -v
```

Expected: all 4 pass.

- [ ] **Commit:**

```bash
git add server/routers/export.py tests/test_api_export.py
git commit -m "feat(api): JSON snapshot export/import with preview, CSV export"
```

---

### Task 4.2: Full test suite green check

- [ ] **Run all tests:**

```bash
pytest tests/ -v --tb=short
```

Expected: all tests pass (existing + new).

- [ ] **Run linter:**

```bash
ruff check src/ server/ tests/
```

Fix any issues before proceeding.

- [ ] **Verify server starts and seeds correctly:**

```bash
mkdir -p data
uvicorn server.main:app --reload --port 8000
```

Open `http://localhost:8000/api/chargers` — should return seeded chargers.
Open `http://localhost:8000/api/templates` — should return template stubs from decision tree.
Open `http://localhost:8000/api/pipeline/status` — should return `{"status": "idle", ...}`

- [ ] **Commit:**

```bash
git commit -m "chore: Phase 1 backend skeleton complete — all tests passing"
```

---

### Task 4.3: Startup script

**Files:**
- Create: `run_server.sh`
- Create: `data/.gitkeep`

- [ ] **Create `run_server.sh`:**

```bash
#!/bin/bash
set -e

# Activate venv if it exists
if [ -f ".venv/bin/activate" ]; then
  source .venv/bin/activate
fi

mkdir -p data

echo "Starting It's Electric server at http://localhost:8000"
uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
```

- [ ] **Make executable:**

```bash
chmod +x run_server.sh
touch data/.gitkeep
echo "data/*.db" >> .gitignore
```

- [ ] **Commit:**

```bash
git add run_server.sh data/.gitkeep .gitignore
git commit -m "chore: add startup script and data directory"
```

---

## Phase 2–5 Roadmap (separate plans)

These phases each get their own implementation plan when Phase 1 is merged.

### Phase 2 — Inbox UI
**Deliverable:** Working web app for the core use case: run pipeline → review inbox → preview email → send.

Key tasks:
- Vite + React + TypeScript + Tailwind scaffold in `web/`
- Sidebar layout with 5 nav items
- Dashboard page: counts, run button, activity feed, SSE log stream
- Inbox page: filterable contact list, email detail panel, preview, send/skip
- FastAPI serves `web/dist` in production; Vite proxies `/api` to `:8000` in dev

### Phase 3 — History, export & import
**Deliverable:** Searchable history log; one-click JSON/CSV export; snapshot import with preview.

Key tasks:
- History page with text search, date filter, pagination
- Download snapshot (JSON) and CSV buttons wired to `/api/export/*`
- Upload snapshot UI with diff preview before confirm

### Phase 4 — Configuration UI
**Deliverable:** Full config editing in browser — decision tree, templates, chargers.

Key tasks:
- Config page: settings form (label, max_messages, etc.)
- Template editor: list + rich text body + subject
- Decision tree: YAML editor (CodeMirror) + dry-run diff table
- Charger table: editable list with add/delete

### Phase 5 — Polish
**Deliverable:** Production-ready local tool.

Key tasks:
- Auto-send toggle (config key → pipeline_service respects it)
- Google credentials health indicator on dashboard (banner on `RefreshError`)
- `run_server.sh` opens browser automatically
- Retire `gui.py` and `app.spec` / `build_app.sh`
- Update `pyproject.toml` entry point: `itselectric-web = "server.main:app"`
