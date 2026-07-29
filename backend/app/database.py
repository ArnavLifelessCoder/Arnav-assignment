"""
SQLite storage layer for billing data and computed reports.

Uses SQLite for persistence — no managed database required.
Reports are keyed by (clinic_id, date).
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Optional

from .models import (
    AnalyticsReport,
    FullReport,
    NarrativeResponse,
    ReconciliationReport,
)

DB_PATH = Path(__file__).parent.parent / "swasthiq.db"


def get_connection() -> sqlite3.Connection:
    """Get a SQLite connection with row factory."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    """Create tables if they don't exist."""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS reports (
            clinic_id TEXT NOT NULL,
            date TEXT NOT NULL,
            raw_billing_json TEXT NOT NULL,
            reconciliation_json TEXT NOT NULL,
            analytics_json TEXT NOT NULL,
            narrative_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (clinic_id, date)
        );
    """)
    conn.commit()
    conn.close()


def save_report(
    clinic_id: str,
    date: str,
    raw_billing_json: str,
    reconciliation: ReconciliationReport,
    analytics: AnalyticsReport,
    narrative: Optional[NarrativeResponse] = None,
) -> None:
    """Save or update a report in the database."""
    conn = get_connection()
    conn.execute(
        """
        INSERT OR REPLACE INTO reports
            (clinic_id, date, raw_billing_json, reconciliation_json, analytics_json, narrative_json)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            clinic_id,
            date,
            raw_billing_json,
            reconciliation.model_dump_json(),
            analytics.model_dump_json(),
            narrative.model_dump_json() if narrative else None,
        ),
    )
    conn.commit()
    conn.close()


def get_report(clinic_id: str, date: str) -> Optional[FullReport]:
    """Retrieve a stored report."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM reports WHERE clinic_id = ? AND date = ?",
        (clinic_id, date),
    ).fetchone()
    conn.close()

    if not row:
        return None

    recon = ReconciliationReport.model_validate_json(row["reconciliation_json"])
    analytics = AnalyticsReport.model_validate_json(row["analytics_json"])
    narrative = (
        NarrativeResponse.model_validate_json(row["narrative_json"])
        if row["narrative_json"]
        else None
    )

    return FullReport(
        reconciliation=recon,
        analytics=analytics,
        narrative=narrative,
    )


def get_reconciliation(clinic_id: str, date: str) -> Optional[ReconciliationReport]:
    """Retrieve just the reconciliation report."""
    conn = get_connection()
    row = conn.execute(
        "SELECT reconciliation_json FROM reports WHERE clinic_id = ? AND date = ?",
        (clinic_id, date),
    ).fetchone()
    conn.close()

    if not row:
        return None
    return ReconciliationReport.model_validate_json(row["reconciliation_json"])


def get_analytics(clinic_id: str, date: str) -> Optional[AnalyticsReport]:
    """Retrieve just the analytics report."""
    conn = get_connection()
    row = conn.execute(
        "SELECT analytics_json FROM reports WHERE clinic_id = ? AND date = ?",
        (clinic_id, date),
    ).fetchone()
    conn.close()

    if not row:
        return None
    return AnalyticsReport.model_validate_json(row["analytics_json"])


def get_narrative(clinic_id: str, date: str) -> Optional[NarrativeResponse]:
    """Retrieve just the narrative."""
    conn = get_connection()
    row = conn.execute(
        "SELECT narrative_json FROM reports WHERE clinic_id = ? AND date = ?",
        (clinic_id, date),
    ).fetchone()
    conn.close()

    if not row or not row["narrative_json"]:
        return None
    return NarrativeResponse.model_validate_json(row["narrative_json"])


def list_reports() -> list[dict]:
    """List all available reports."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT clinic_id, date, created_at FROM reports ORDER BY date DESC"
    ).fetchall()
    conn.close()

    return [{"clinic_id": r["clinic_id"], "date": r["date"], "created_at": r["created_at"]} for r in rows]


def update_narrative(clinic_id: str, date: str, narrative: NarrativeResponse) -> None:
    """Update the narrative for an existing report."""
    conn = get_connection()
    conn.execute(
        "UPDATE reports SET narrative_json = ? WHERE clinic_id = ? AND date = ?",
        (narrative.model_dump_json(), clinic_id, date),
    )
    conn.commit()
    conn.close()
