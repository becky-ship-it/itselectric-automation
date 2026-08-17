"""FastAPI application entry point."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from server import auth
from server.auth import require_user
from server.db import Base, get_engine, get_session
from server.routers import chargers, config, contacts, export, logs, pipeline, templates
from server.seed import (
    seed_chargers,
    seed_config,
    seed_decision_tree_from_yaml,
    seed_geocache,
    seed_templates_from_yaml,
)

DB_URL = os.getenv("DATABASE_URL", "sqlite:///data/itselectric.db")
# Render (and most hosts) hand out postgres URLs as `postgres://` or
# `postgresql://`; pin the psycopg3 dialect SQLAlchemy expects.
if DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DB_URL.startswith("postgresql://"):
    DB_URL = DB_URL.replace("postgresql://", "postgresql+psycopg://", 1)
GEOCACHE_PATH = os.getenv("GEOCACHE_PATH", "geocache.json")
# decision_tree.yaml is a seed-only source — the DB is the live source of truth after first run
DECISION_TREE_PATH = os.getenv("DECISION_TREE_PATH", "decision_tree.yaml")
CONFIG_YAML_PATH = os.getenv("CONFIG_YAML_PATH", "config.yaml")


@asynccontextmanager
async def lifespan(app: FastAPI):
    import yaml  # type: ignore

    import server.models  # noqa: F401 — registers all models with Base.metadata

    engine = get_engine(DB_URL)
    Base.metadata.create_all(engine)
    app.state.engine = engine

    with get_session(engine) as session:
        seed_chargers(session)
        seed_geocache(session, GEOCACHE_PATH)
        if Path(DECISION_TREE_PATH).exists():
            seed_templates_from_yaml(session, DECISION_TREE_PATH)
            seed_decision_tree_from_yaml(session, DECISION_TREE_PATH)
        config_data: dict = {}
        if Path(CONFIG_YAML_PATH).exists():
            with open(CONFIG_YAML_PATH) as f:
                config_data = yaml.safe_load(f) or {}
        seed_config(session, config_data)

    yield


# Fail closed on partial SSO config before anything else.
auth.check_config()

app = FastAPI(title="It's Electric Automation", lifespan=lifespan)

# Signed-cookie sessions back the SSO login. When auth is on, cookies are
# Secure; a per-process random default key keeps local dev working (sessions
# just don't survive a restart).
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", os.urandom(32).hex()),
    same_site="lax",
    https_only=auth.auth_enabled(),
)

if not auth.auth_enabled():
    print(
        "WARNING: Google SSO is DISABLED — the dashboard is open to anyone who "
        "can reach it. Set GOOGLE_OAUTH_CLIENT_ID and ALLOWED_GOOGLE_EMAILS to "
        "enable it."
    )

# Login/callback/logout/me — never behind the guard.
app.include_router(auth.router)

# Everything under /api is guarded. require_user is a no-op when auth is off.
_guard = [Depends(require_user)]
app.include_router(pipeline.router, prefix="/api/pipeline", tags=["pipeline"], dependencies=_guard)
app.include_router(contacts.router, prefix="/api/contacts", tags=["contacts"], dependencies=_guard)
app.include_router(
    templates.router, prefix="/api/templates", tags=["templates"], dependencies=_guard
)
app.include_router(chargers.router, prefix="/api/chargers", tags=["chargers"], dependencies=_guard)
app.include_router(config.router, prefix="/api", tags=["config"], dependencies=_guard)
app.include_router(export.router, prefix="/api", tags=["export"], dependencies=_guard)
app.include_router(logs.router, prefix="/api", tags=["logs"], dependencies=_guard)

if os.path.exists("web/dist"):
    app.mount("/assets", StaticFiles(directory="web/dist/assets"), name="assets")

    _DIST = Path("web/dist").resolve()

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        candidate = (_DIST / full_path).resolve()
        # Confine to web/dist: reject `..` traversal before serving any file.
        if candidate.is_file() and candidate.is_relative_to(_DIST):
            return FileResponse(candidate)
        return FileResponse(_DIST / "index.html")
