"""
Deterministic analytics computation.

This module NEVER calls an LLM. It is the ground truth layer.
All money is integer paise throughout.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from .models import (
    AnalyticsReport,
    BillingRecord,
    DoctorPerformance,
    DrugRanking,
    HourlyRevenue,
    PolypharmacyStats,
    PriceTierShare,
    ShiftBreakdown,
)


def compute_analytics(
    records: list[BillingRecord],
    clinic_id: str,
    date: str,
) -> AnalyticsReport:
    """
    Compute analytics from validated billing records (non-refund only).
    """

    # Filter to non-refund records only
    sales = [r for r in records if not r.is_refund]

    # ── Revenue by hour & shifts ──
    hour_revenue: dict[int, int] = defaultdict(int)
    hour_visits: dict[int, int] = defaultdict(int)

    shift_visits: dict[str, int] = defaultdict(int)
    shift_revenue: dict[str, int] = defaultdict(int)

    for rec in sales:
        try:
            ts = datetime.fromisoformat(rec.timestamp.replace("Z", "+00:00"))
        except ValueError:
            continue
        hour = ts.hour
        hour_revenue[hour] += rec.amount_paid_paise
        hour_visits[hour] += 1

        if hour < 12:
            s_name = "Morning (09:00-12:00)"
        elif hour < 17:
            s_name = "Afternoon (12:00-17:00)"
        else:
            s_name = "Evening (17:00-20:00)"

        shift_visits[s_name] += 1
        shift_revenue[s_name] += rec.amount_paid_paise

    revenue_by_hour = sorted(
        [
            HourlyRevenue(hour=h, revenue_paise=rev, visit_count=hour_visits[h])
            for h, rev in hour_revenue.items()
        ],
        key=lambda x: x.hour,
    )

    peak_hour = None
    peak_hour_revenue = 0
    if revenue_by_hour:
        peak = max(revenue_by_hour, key=lambda x: x.revenue_paise)
        peak_hour = peak.hour
        peak_hour_revenue = peak.revenue_paise

    shifts = [
        ShiftBreakdown(
            shift_name=s_name,
            visit_count=shift_visits[s_name],
            revenue_paise=shift_revenue[s_name],
        )
        for s_name in ["Morning (09:00-12:00)", "Afternoon (12:00-17:00)", "Evening (17:00-20:00)"]
        if shift_visits[s_name] > 0
    ]

    # ── Top medicines & Price Tiers ──
    drug_qty: dict[str, int] = defaultdict(int)
    drug_rev: dict[str, int] = defaultdict(int)

    tier_qty: dict[str, int] = defaultdict(int)
    tier_rev: dict[str, int] = defaultdict(int)
    tier_drugs: dict[str, set] = defaultdict(set)

    for rec in sales:
        for item in rec.line_items:
            name = item.drug_name
            drug_qty[name] += item.qty
            item_rev = item.qty * item.unit_price_paise
            drug_rev[name] += item_rev

            if item.unit_price_paise >= 10000:
                t_name = "High-Value (>= ₹100)"
            elif item.unit_price_paise >= 3000:
                t_name = "Mid-Value (₹30-₹99)"
            else:
                t_name = "Low-Value (< ₹30)"

            tier_qty[t_name] += item.qty
            tier_rev[t_name] += item_rev
            tier_drugs[t_name].add(name)

    top_by_qty = sorted(drug_qty.items(), key=lambda x: x[1], reverse=True)
    top_by_rev = sorted(drug_rev.items(), key=lambda x: x[1], reverse=True)

    top_drugs_by_quantity = [
        DrugRanking(drug_name=name, value=val, rank=i + 1)
        for i, (name, val) in enumerate(top_by_qty)
    ]
    top_drugs_by_revenue = [
        DrugRanking(drug_name=name, value=val, rank=i + 1)
        for i, (name, val) in enumerate(top_by_rev)
    ]

    price_tiers = [
        PriceTierShare(
            tier_name=t_name,
            drug_count=len(tier_drugs[t_name]),
            total_qty=tier_qty[t_name],
            revenue_paise=tier_rev[t_name],
        )
        for t_name in ["High-Value (>= ₹100)", "Mid-Value (₹30-₹99)", "Low-Value (< ₹30)"]
        if tier_qty[t_name] > 0
    ]

    # ── Doctor Performance & Polypharmacy ──
    doc_visits: dict[str, int] = defaultdict(int)
    doc_revenue: dict[str, int] = defaultdict(int)
    total_items = 0

    single_item_visits = 0
    multi_item_visits = 0
    max_items = 0

    total_billed_sum = 0
    total_discount_sum = 0

    for rec in sales:
        doc_visits[rec.doctor_id] += 1
        doc_revenue[rec.doctor_id] += rec.amount_paid_paise
        item_count = len(rec.line_items)
        total_items += sum(item.qty for item in rec.line_items)

        total_billed_sum += sum(item.qty * item.unit_price_paise for item in rec.line_items)
        total_discount_sum += rec.discount_paise

        if item_count == 1:
            single_item_visits += 1
        else:
            multi_item_visits += 1

        if item_count > max_items:
            max_items = item_count

    doc_perf = sorted(
        [
            DoctorPerformance(
                doctor_id=doc_id,
                visit_count=count,
                total_revenue_paise=doc_revenue[doc_id],
            )
            for doc_id, count in doc_visits.items()
        ],
        key=lambda x: x.total_revenue_paise,
        reverse=True,
    )

    total_sales_count = len(sales)
    total_collected_sum = sum(rec.amount_paid_paise for rec in sales)

    avg_visit_val = int(total_collected_sum / total_sales_count) if total_sales_count > 0 else 0
    avg_items_val = round(total_items / total_sales_count, 1) if total_sales_count > 0 else 0.0

    discount_rate = round((total_discount_sum / total_billed_sum) * 100, 2) if total_billed_sum > 0 else 0.0

    poly = PolypharmacyStats(
        single_item_visits=single_item_visits,
        multi_item_visits=multi_item_visits,
        max_items_in_single_visit=max_items,
    )

    return AnalyticsReport(
        clinic_id=clinic_id,
        date=date,
        revenue_by_hour=revenue_by_hour,
        peak_hour=peak_hour,
        peak_hour_revenue_paise=peak_hour_revenue,
        top_drugs_by_quantity=top_drugs_by_quantity,
        top_drugs_by_revenue=top_drugs_by_revenue,
        doctor_performance=doc_perf,
        avg_visit_value_paise=avg_visit_val,
        avg_items_per_visit=avg_items_val,
        shifts=shifts,
        price_tiers=price_tiers,
        polypharmacy=poly,
        effective_discount_rate_pct=discount_rate,
    )
