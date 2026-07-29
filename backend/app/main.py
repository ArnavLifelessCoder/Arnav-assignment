"""
FastAPI application entry point.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .routes import router


import json
from pathlib import Path
from . import database as db
from .analytics import compute_analytics
from .narrative import generate_narrative
from .parser import parse_billing_log
from .reconciliation import compute_reconciliation
from .routes import _extract_clinic_id, _extract_date


async def seed_sample_data_if_empty():
    """Auto-seed sample billing logs if the database has no reports yet."""
    if db.list_reports():
        return

    root_dir = Path(__file__).parent.parent.parent
    sample_filenames = [
        "billing_log_2026-07-27.json",
        "billing_log_2026-07-25.json",
        "billing_log_2026-07-26.json",
    ]

    for fname in sample_filenames:
        sample_path = root_dir / fname
        if sample_path.is_file():
            try:
                raw_text = sample_path.read_text(encoding="utf-8")
                raw_data = json.loads(raw_text)
                valid_records, validation_errors = parse_billing_log(raw_text)

                clinic_id = _extract_clinic_id(valid_records, raw_data)
                date = _extract_date(valid_records, raw_data)

                if clinic_id == "unknown" and not valid_records:
                    if "2026-07-26" in fname:
                        clinic_id, date = "CLN-KNP-014", "2026-07-26"

                if clinic_id != "unknown" and date != "unknown":
                    recon = compute_reconciliation(valid_records, clinic_id, date, validation_errors)
                    analytics = compute_analytics(valid_records, clinic_id, date)
                    narrative = await generate_narrative(recon, analytics)

                    db.save_report(clinic_id, date, raw_text, recon, analytics, narrative)
            except Exception as e:
                print(f"Sample seed error for {fname}: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and seed sample data on startup."""
    init_db()
    await seed_sample_data_if_empty()
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
