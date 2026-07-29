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

# Mount routes
app.include_router(router)


@app.get("/")
async def root():
    return {
        "service": "SwasthiQ EOD Billing & Analytics Agent",
        "version": "1.0.0",
        "docs": "/docs",
    }
