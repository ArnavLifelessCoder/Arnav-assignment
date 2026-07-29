"""
Deterministic EOD reconciliation computation.

This module NEVER calls an LLM. It is the ground truth layer.
All money is integer paise throughout.
"""

from __future__ import annotations

from .models import BillingRecord, PaymentModeBreakdown, ReconciliationReport


def compute_reconciliation(
    records: list[BillingRecord],
    clinic_id: str,
    date: str,
    validation_errors: list[str] | None = None,
) -> ReconciliationReport:
    """
    Compute the end-of-day reconciliation from validated billing records.

    Definitions:
    - Total Billed   = Σ(line_item.qty × unit_price_paise) for NON-refund rows
    - Total Discount = Σ(discount_paise) for NON-refund rows
    - Total Collected = Σ(amount_paid_paise) for NON-refund rows
    - Outstanding    = Total Billed − Total Discount − Total Collected
    - Total Refunds  = Σ(|amount_paid_paise|) for refund rows (always positive)
    """

    # ── Accumulators ──
    total_billed = 0
    total_discount = 0
    total_collected = 0
    total_refunds = 0
    total_visits = 0
    total_refund_visits = 0

    # Per payment-mode accumulators
    mode_data: dict[str, dict[str, int]] = {}
    for mode in ("cash", "card", "upi"):
        mode_data[mode] = {
            "billed": 0,
            "discount": 0,
            "collected": 0,
            "refunds": 0,
        }

    # ── Process each record ──
    for rec in records:
        pm = rec.payment_mode.value

        if rec.is_refund:
            total_refund_visits += 1
            refund_amount = abs(rec.amount_paid_paise)
            total_refunds += refund_amount
            mode_data[pm]["refunds"] += refund_amount
        else:
            total_visits += 1
            billed = rec.line_items_total_paise
            total_billed += billed
            total_discount += rec.discount_paise
            total_collected += rec.amount_paid_paise

            mode_data[pm]["billed"] += billed
            mode_data[pm]["discount"] += rec.discount_paise
            mode_data[pm]["collected"] += rec.amount_paid_paise

    # ── Build payment-mode breakdowns ──
    outstanding = total_billed - total_discount - total_collected
    by_payment_mode: list[PaymentModeBreakdown] = []

    for mode in ("cash", "card", "upi"):
        d = mode_data[mode]
        mode_outstanding = d["billed"] - d["discount"] - d["collected"]
        by_payment_mode.append(
            PaymentModeBreakdown(
                payment_mode=mode,
                total_billed_paise=d["billed"],
                total_discount_paise=d["discount"],
                total_collected_paise=d["collected"],
                outstanding_paise=mode_outstanding,
                total_refunds_paise=d["refunds"],
            )
        )

    return ReconciliationReport(
        clinic_id=clinic_id,
        date=date,
        total_billed_paise=total_billed,
        total_discount_paise=total_discount,
        total_collected_paise=total_collected,
        outstanding_paise=outstanding,
        total_refunds_paise=total_refunds,
        total_visits=total_visits,
        total_refund_visits=total_refund_visits,
        by_payment_mode=by_payment_mode,
        validation_errors=validation_errors or [],
    )
