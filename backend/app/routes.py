"""
API route definitions for the EOD Billing & Analytics Agent.
"""

from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, File, HTTPException, UploadFile

from . import database as db
from .analytics import compute_analytics
from .models import AnalyticsReport, FullReport, NarrativeResponse, ReconciliationReport
from .narrative import generate_narrative
from .parser import parse_billing_log
from .reconciliation import compute_reconciliation

router = APIRouter(prefix="/api")


def _extract_date(records, raw_data: list[dict]) -> str:
    """Extract the date from the first valid record's timestamp."""
    for rec in records:
        try:
            ts = datetime.fromisoformat(rec.timestamp.replace("Z", "+00:00"))
            return ts.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Fallback: try raw data
    for row in raw_data:
        ts_str = row.get("timestamp", "")
        if ts_str:
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                return ts.strftime("%Y-%m-%d")
            except ValueError:
                continue

    return "unknown"


def _extract_clinic_id(records, raw_data: list[dict]) -> str:
    """Extract clinic_id from the first record."""
    for rec in records:
        return rec.clinic_id
    for row in raw_data:
        cid = row.get("clinic_id", "")
        if cid:
            return cid
    return "unknown"


@router.post("/upload")
async def upload_billing_log(file: UploadFile = File(...)):
    """
    Upload a billing log JSON file.

    Validates each row individually, computes reconciliation + analytics,
    generates LLM narrative, and stores everything.
    """
    # ── Read and parse ──
    try:
        contents = await file.read()
        raw_text = contents.decode("utf-8")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read file: {e}")

    # Parse the raw JSON first to extract metadata even if validation fails
    try:
        raw_data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    if not isinstance(raw_data, list):
        raise HTTPException(status_code=400, detail="Expected a JSON array of billing records")

    # ── Validate records ──
    valid_records, validation_errors = parse_billing_log(raw_text)

    # Extract metadata
    clinic_id = _extract_clinic_id(valid_records, raw_data)
    date = _extract_date(valid_records, raw_data)

    # Handle completely empty file
    if not raw_data:
        # Empty array — valid but no data
        clinic_id = "unknown"
        date = "unknown"

    if clinic_id == "unknown" and not valid_records:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Could not determine clinic_id or date from the data",
                "validation_errors": validation_errors,
            },
        )

    # ── Compute deterministic layers ──
    reconciliation = compute_reconciliation(valid_records, clinic_id, date, validation_errors)
    analytics = compute_analytics(valid_records, clinic_id, date)

    # ── Generate narrative (async, best-effort) ──
    narrative = await generate_narrative(reconciliation, analytics)

    # ── Store ──
    db.save_report(clinic_id, date, raw_text, reconciliation, analytics, narrative)

    return {
        "status": "success",
        "clinic_id": clinic_id,
        "date": date,
        "records_processed": len(valid_records),
        "records_rejected": len(validation_errors),
        "validation_errors": validation_errors,
        "reconciliation": reconciliation.model_dump(),
        "analytics": analytics.model_dump(),
        "narrative": narrative.model_dump() if narrative else None,
    }


@router.get("/reports", response_model=list[dict])
async def list_reports():
    """List all available reports."""
    return db.list_reports()


@router.get("/reports/{clinic_id}/{date}", response_model=FullReport)
async def get_full_report(clinic_id: str, date: str):
    """Get the full report (reconciliation + analytics + narrative)."""
    report = db.get_report(clinic_id, date)
    if not report:
        raise HTTPException(status_code=404, detail=f"No report found for {clinic_id} on {date}")
    return report


@router.get("/reconciliation/{clinic_id}/{date}", response_model=ReconciliationReport)
async def get_reconciliation(clinic_id: str, date: str):
    """Get just the reconciliation data."""
    recon = db.get_reconciliation(clinic_id, date)
    if not recon:
        raise HTTPException(status_code=404, detail=f"No report found for {clinic_id} on {date}")
    return recon


@router.get("/analytics/{clinic_id}/{date}", response_model=AnalyticsReport)
async def get_analytics(clinic_id: str, date: str):
    """Get just the analytics data."""
    analytics = db.get_analytics(clinic_id, date)
    if not analytics:
        raise HTTPException(status_code=404, detail=f"No report found for {clinic_id} on {date}")
    return analytics


@router.get("/narrative/{clinic_id}/{date}", response_model=NarrativeResponse)
async def get_narrative(clinic_id: str, date: str):
    """Get the LLM narrative + traced figures."""
    narrative = db.get_narrative(clinic_id, date)
    if not narrative:
        raise HTTPException(status_code=404, detail=f"No narrative found for {clinic_id} on {date}")
    return narrative
