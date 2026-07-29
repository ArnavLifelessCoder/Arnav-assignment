"""
Tests for the parser, reconciliation, and analytics modules.
Covers: normal day (July 27), empty day (July 26), refund-only day (July 25).
"""

import json
import os
import sys

import pytest

# Add parent dirs to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.parser import parse_billing_log
from app.reconciliation import compute_reconciliation
from app.analytics import compute_analytics


# ── Sample Data ──

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..")

def _load_log(filename: str) -> str:
    path = os.path.join(DATA_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ═══════════════════════════════════════════
# Parser Tests
# ═══════════════════════════════════════════

class TestParser:
    def test_parse_july27_parses_all_records(self):
        """July 27 has 19 records; V-019 missing payment_mode defaults gracefully."""
        raw = _load_log("billing_log_2026-07-27.json")
        valid, errors = parse_billing_log(raw)
        assert len(valid) == 19
        assert len(errors) == 0
        v19 = [r for r in valid if r.visit_id == "V-20260727-019"][0]
        assert v19.payment_mode == "cash"

    def test_parse_july26_empty(self):
        """July 26 is an empty array — should return 0 records, 0 errors."""
        raw = _load_log("billing_log_2026-07-26.json")
        valid, errors = parse_billing_log(raw)
        assert len(valid) == 0
        assert len(errors) == 0

    def test_parse_july25_refunds(self):
        """July 25 has 3 refund records — all should parse successfully."""
        raw = _load_log("billing_log_2026-07-25.json")
        valid, errors = parse_billing_log(raw)
        assert len(valid) == 3
        assert len(errors) == 0
        for rec in valid:
            assert rec.is_refund is True
            assert rec.amount_paid_paise <= 0

    def test_parse_invalid_json(self):
        """Garbage input should return an error, not crash."""
        valid, errors = parse_billing_log("not json at all")
        assert len(valid) == 0
        assert len(errors) == 1
        assert "Invalid JSON" in errors[0]

    def test_parse_non_array(self):
        """A JSON object instead of array should error."""
        valid, errors = parse_billing_log('{"foo": "bar"}')
        assert len(valid) == 0
        assert len(errors) == 1
        assert "array" in errors[0].lower()


# ═══════════════════════════════════════════
# Reconciliation Tests
# ═══════════════════════════════════════════

class TestReconciliation:
    def test_july27_reconciliation(self):
        """
        July 27: 18 valid records (all non-refund sales).
        Hand-computed expected values.
        """
        raw = _load_log("billing_log_2026-07-27.json")
        valid, errors = parse_billing_log(raw)
        recon = compute_reconciliation(valid, "CLN-KNP-014", "2026-07-27", errors)

        # All 19 valid records are sales (non-refund)
        assert recon.total_visits == 19
        assert recon.total_refund_visits == 0
        assert recon.total_refunds_paise == 0

        # Verify total_billed is sum of all line_items (qty * unit_price)
        # V-001..V-018: 326000 + V-019 (1*4000 = 4000) = 330000
        expected_billed = (6000 + 4000 + 6000 + 52000 + 12000 + 15000 +
                          8000 + 6000 + 4000 + 21000 + 56000 + 4000 +
                          30000 + 12000 + 25000 + 36000 + 23000 + 6000 + 4000)
        assert recon.total_billed_paise == expected_billed

        # Verify total_discount
        expected_discount = 1000+1000+500+1000+500+1000+500+500+1000
        assert recon.total_discount_paise == expected_discount

        # Verify total_collected
        expected_collected = (6000+3000+5000+51500+12000+14500+7000+6000+
                             3500+21000+54500+3500+29500+12000+25000+
                             35200+22000+6000+4000)
        assert recon.total_collected_paise == expected_collected

        # Outstanding = billed - discount - collected
        assert recon.outstanding_paise == expected_billed - expected_discount - expected_collected

    def test_july26_empty_day(self):
        """July 26: empty array — all zeros."""
        recon = compute_reconciliation([], "CLN-KNP-014", "2026-07-26", [])
        assert recon.total_billed_paise == 0
        assert recon.total_collected_paise == 0
        assert recon.outstanding_paise == 0
        assert recon.total_refunds_paise == 0
        assert recon.total_visits == 0

    def test_july25_refund_only(self):
        """July 25: all 3 records are refunds — no sales."""
        raw = _load_log("billing_log_2026-07-25.json")
        valid, errors = parse_billing_log(raw)
        recon = compute_reconciliation(valid, "CLN-KNP-014", "2026-07-25", errors)

        assert recon.total_visits == 0
        assert recon.total_refund_visits == 3
        assert recon.total_billed_paise == 0
        assert recon.total_collected_paise == 0
        assert recon.outstanding_paise == 0
        # Refunds: |−24000| + |−22000| + |−3000| = 49000
        assert recon.total_refunds_paise == 49000

    def test_payment_mode_breakdown(self):
        """Verify payment mode split for July 27."""
        raw = _load_log("billing_log_2026-07-27.json")
        valid, errors = parse_billing_log(raw)
        recon = compute_reconciliation(valid, "CLN-KNP-014", "2026-07-27", errors)

        modes = {pm.payment_mode: pm for pm in recon.by_payment_mode}
        assert "cash" in modes
        assert "card" in modes
        assert "upi" in modes

        # Every mode should have non-negative billed
        for pm in recon.by_payment_mode:
            assert pm.total_billed_paise >= 0
            assert pm.total_collected_paise >= 0


# ═══════════════════════════════════════════
# Analytics Tests
# ═══════════════════════════════════════════

class TestAnalytics:
    def test_july27_analytics(self):
        """July 27: verify peak hour and drug rankings."""
        raw = _load_log("billing_log_2026-07-27.json")
        valid, errors = parse_billing_log(raw)
        analytics = compute_analytics(valid, "CLN-KNP-014", "2026-07-27")

        # Should have revenue by hour data
        assert len(analytics.revenue_by_hour) > 0

        # Peak hour should be identified
        assert analytics.peak_hour is not None
        assert analytics.peak_hour_revenue_paise > 0

        # Should have drug rankings
        assert len(analytics.top_drugs_by_quantity) > 0
        assert len(analytics.top_drugs_by_revenue) > 0

        # Rankings should be sorted (rank 1 has highest value)
        for i in range(len(analytics.top_drugs_by_quantity) - 1):
            assert analytics.top_drugs_by_quantity[i].value >= analytics.top_drugs_by_quantity[i + 1].value

        for i in range(len(analytics.top_drugs_by_revenue) - 1):
            assert analytics.top_drugs_by_revenue[i].value >= analytics.top_drugs_by_revenue[i + 1].value

    def test_july26_empty_analytics(self):
        """July 26: empty day — no analytics."""
        analytics = compute_analytics([], "CLN-KNP-014", "2026-07-26")
        assert len(analytics.revenue_by_hour) == 0
        assert analytics.peak_hour is None
        assert analytics.peak_hour_revenue_paise == 0
        assert len(analytics.top_drugs_by_quantity) == 0
        assert len(analytics.top_drugs_by_revenue) == 0

    def test_july25_refund_only_analytics(self):
        """July 25: refund-only day — analytics should exclude refunds."""
        raw = _load_log("billing_log_2026-07-25.json")
        valid, errors = parse_billing_log(raw)
        analytics = compute_analytics(valid, "CLN-KNP-014", "2026-07-25")

        # All records are refunds, so analytics (non-refund only) should be empty
        assert len(analytics.revenue_by_hour) == 0
        assert analytics.peak_hour is None
        assert len(analytics.top_drugs_by_quantity) == 0
        assert len(analytics.top_drugs_by_revenue) == 0

    def test_drug_rankings_are_distinct(self):
        """By-quantity and by-revenue rankings may have different ordering."""
        raw = _load_log("billing_log_2026-07-27.json")
        valid, errors = parse_billing_log(raw)
        analytics = compute_analytics(valid, "CLN-KNP-014", "2026-07-27")

        qty_order = [d.drug_name for d in analytics.top_drugs_by_quantity]
        rev_order = [d.drug_name for d in analytics.top_drugs_by_revenue]

        # Both should contain the same drugs
        assert set(qty_order) == set(rev_order)

    def test_typo_drug_is_separate_entry(self):
        """PARACETMOL (typo) should be tracked separately from PARACETAMOL."""
        raw = _load_log("billing_log_2026-07-27.json")
        valid, errors = parse_billing_log(raw)
        analytics = compute_analytics(valid, "CLN-KNP-014", "2026-07-27")

        drug_names = [d.drug_name for d in analytics.top_drugs_by_quantity]
        assert "PARACETAMOL" in drug_names
        assert "PARACETMOL" in drug_names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
