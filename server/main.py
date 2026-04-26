"""FastAPI application entry point."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from server.db import Base, get_engine, get_session
from server.routers import chargers, config, contacts, export, logs, pipeline, templates
from server.seed import seed_chargers, seed_config, seed_decision_tree_from_yaml, seed_geocache, seed_templates_from_yaml

DB_URL = os.getenv("DATABASE_URL", "sqlite:///data/itselectric.db")
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


app = FastAPI(title="It's Electric Automation", lifespan=lifespan)

app.include_router(pipeline.router, prefix="/api/pipeline", tags=["pipeline"])
app.include_router(contacts.router, prefix="/api/contacts", tags=["contacts"])
app.include_router(templates.router, prefix="/api/templates", tags=["templates"])
app.include_router(chargers.router, prefix="/api/chargers", tags=["chargers"])
app.include_router(config.router, prefix="/api", tags=["config"])
app.include_router(export.router, prefix="/api", tags=["export"])
app.include_router(logs.router, prefix="/api", tags=["logs"])

if os.path.exists("web/dist"):
    app.mount("/assets", StaticFiles(directory="web/dist/assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        candidate = Path("web/dist") / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse("web/dist/index.html")
