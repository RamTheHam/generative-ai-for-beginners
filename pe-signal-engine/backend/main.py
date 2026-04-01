"""
PE Signal Engine — FastAPI application entry point.

Run with:
    uvicorn backend.main:app --reload --port 8000

Or from project root:
    cd pe-signal-engine
    uvicorn backend.main:app --reload --port 8000
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from .database import init_db
from .routers import search_runs, companies, executives, config
from .services.scoring import seed_default_rules
from .database import SessionLocal

app = FastAPI(
    title="PE Signal Engine",
    description="Modular executive-intelligence system for PE origination and operator mapping.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search_runs.router)
app.include_router(companies.router)
app.include_router(executives.router)
app.include_router(config.router)


@app.on_event("startup")
def on_startup():
    init_db()
    db = SessionLocal()
    try:
        seed_default_rules(db)
    finally:
        db.close()


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


# Serve the frontend SPA from /frontend
_frontend = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(_frontend):
    app.mount("/static", StaticFiles(directory=_frontend), name="static")

    @app.get("/")
    def serve_frontend():
        return FileResponse(os.path.join(_frontend, "index.html"))
