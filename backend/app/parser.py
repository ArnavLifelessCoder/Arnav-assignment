"""
Parse and validate a raw billing log JSON array.

Each row is validated individually — a single malformed row does not
reject the entire file. Instead, we collect valid records and return
per-row validation errors with actionable messages.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from .models import BillingRecord


def parse_billing_log(raw_json: str | bytes) -> tuple[list[BillingRecord], list[str]]:
    """
    Parse a billing log JSON string/bytes into validated BillingRecord objects.

    Returns:
        (valid_records, validation_errors)
    """
    errors: list[str] = []

    # ── Step 1: Parse the outer JSON structure ──
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as e:
        return [], [f"Invalid JSON: {e}"]

    if not isinstance(data, list):
        return [], ["Expected a JSON array of billing records, got " + type(data).__name__]

    # ── Step 2: Validate each record individually ──
    valid_records: list[BillingRecord] = []

    for idx, row in enumerate(data):
        if not isinstance(row, dict):
            errors.append(f"Row {idx}: expected a JSON object, got {type(row).__name__}")
            continue

        visit_id = row.get("visit_id", f"<row {idx}>")

        try:
            record = BillingRecord(**row)
            valid_records.append(record)
        except ValidationError as e:
            # Build actionable error messages from Pydantic errors
            for err in e.errors():
                field_path = " → ".join(str(loc) for loc in err["loc"])
                msg = err["msg"]
                errors.append(f"Row {visit_id}: field '{field_path}' — {msg}")

    return valid_records, errors


def parse_billing_log_from_dict(data: list[dict[str, Any]]) -> tuple[list[BillingRecord], list[str]]:
    """
    Validate an already-parsed list of dicts (e.g. from request body).

    Returns:
        (valid_records, validation_errors)
    """
    errors: list[str] = []
    valid_records: list[BillingRecord] = []

    for idx, row in enumerate(data):
        if not isinstance(row, dict):
            errors.append(f"Row {idx}: expected a JSON object, got {type(row).__name__}")
            continue

        visit_id = row.get("visit_id", f"<row {idx}>")

        try:
            record = BillingRecord(**row)
            valid_records.append(record)
        except ValidationError as e:
            for err in e.errors():
                field_path = " → ".join(str(loc) for loc in err["loc"])
                msg = err["msg"]
                errors.append(f"Row {visit_id}: field '{field_path}' — {msg}")

    return valid_records, errors
