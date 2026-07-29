"""
FastAPI application entry point.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the database on startup."""
    init_db()
    yield


app = FastAPI(
    title="SwasthiQ EOD Billing & Analytics Agent",
    description=(
        "REST API that ingests a clinic's daily billing log and produces "
        "a deterministic EOD reconciliation report, analytics, and an "
        "LLM-generated narrative summary."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import os
from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Mount API routes
app.include_router(router)


@app.get("/api/health")
async def health_check():
    return {
        "service": "SwasthiQ EOD Billing & Analytics Agent",
        "status": "healthy",
        "version": "1.0.0",
    }


# Optional All-in-One Deployment Mode:
# If frontend/dist exists, serve built React app on the same server
frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
if frontend_dist.is_dir():
    assets_dir = frontend_dist / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api"):
            return None
        file_path = frontend_dist / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist / "index.html")
else:
    @app.get("/")
    async def root():
        return {
            "service": "SwasthiQ EOD Billing & Analytics Agent",
            "version": "1.0.0",
            "docs": "/docs",
        }
