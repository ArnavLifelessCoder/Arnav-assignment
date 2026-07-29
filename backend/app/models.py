"""
Pydantic models for billing data validation and API responses.
All monetary values are stored as integer paise — never float rupees.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ──────────────────────────────────────────────
# Input Models
# ──────────────────────────────────────────────

class PaymentMode(str, Enum):
    """Accepted payment modes."""
    cash = "cash"
    card = "card"
    upi = "upi"


class LineItem(BaseModel):
    """A single drug/item in a visit."""
    drug_name: str = Field(..., min_length=1)
    qty: int = Field(..., gt=0)
    unit_price_paise: int = Field(..., ge=0)

    @field_validator("drug_name")
    @classmethod
    def normalise_drug_name(cls, v: str) -> str:
        return v.strip().upper()


class BillingRecord(BaseModel):
    """
    One visit/transaction row from the daily billing log.
    Validation is intentionally strict — a malformed row should be
    caught here with a clear error, not silently accepted.
    """
    clinic_id: str = Field(..., min_length=1)
    visit_id: str = Field(..., min_length=1)
    timestamp: str  # ISO-8601 UTC string — parsed downstream
    doctor_id: str = Field(..., min_length=1)
    line_items: list[LineItem] = Field(..., min_length=1)
    payment_mode: PaymentMode = Field(default=PaymentMode.cash)
    amount_paid_paise: int
    discount_paise: int = Field(default=0, ge=0)
    is_refund: bool = False

    @field_validator("payment_mode", mode="before")
    @classmethod
    def handle_missing_payment_mode(cls, v: Any) -> Any:
        if v is None or v == "":
            return PaymentMode.cash
        return v

    @model_validator(mode="after")
    def refund_amount_must_be_non_positive(self) -> "BillingRecord":
        if self.is_refund and self.amount_paid_paise > 0:
            raise ValueError(
                f"Refund row {self.visit_id}: amount_paid_paise must be <= 0 "
                f"for refunds, got {self.amount_paid_paise}"
            )
        return self

    @property
    def line_items_total_paise(self) -> int:
        """Gross total from line items (qty × unit_price)."""
        return sum(item.qty * item.unit_price_paise for item in self.line_items)


# ──────────────────────────────────────────────
# Output Models
# ──────────────────────────────────────────────

class PaymentModeBreakdown(BaseModel):
    """Reconciliation figures for a single payment mode."""
    payment_mode: str
    total_billed_paise: int = 0
    total_discount_paise: int = 0
    total_collected_paise: int = 0
    outstanding_paise: int = 0
    total_refunds_paise: int = 0


class ReconciliationReport(BaseModel):
    """End-of-day reconciliation — the single source of truth."""
    clinic_id: str
    date: str
    total_billed_paise: int = 0
    total_discount_paise: int = 0
    total_collected_paise: int = 0
    outstanding_paise: int = 0
    total_refunds_paise: int = 0
    total_visits: int = 0
    total_refund_visits: int = 0
    by_payment_mode: list[PaymentModeBreakdown] = []
    validation_errors: list[str] = []


class HourlyRevenue(BaseModel):
    """Revenue collected in one hour slot."""
    hour: int  # 0-23
    revenue_paise: int
    visit_count: int


class DrugRanking(BaseModel):
    """A drug entry in a ranking list."""
    drug_name: str
    value: int  # qty or revenue_paise depending on the ranking
    rank: int


class DoctorPerformance(BaseModel):
    """Doctor prescription & revenue breakdown."""
    doctor_id: str
    visit_count: int = 0
    total_revenue_paise: int = 0


class ShiftBreakdown(BaseModel):
    """Clinic activity split by operating shift."""
    shift_name: str  # Morning, Afternoon, Evening
    visit_count: int = 0
    revenue_paise: int = 0


class PriceTierShare(BaseModel):
    """Medication revenue share by unit price tier."""
    tier_name: str  # High (>₹100), Medium (₹30-₹100), Low (<₹30)
    drug_count: int = 0
    total_qty: int = 0
    revenue_paise: int = 0


class PolypharmacyStats(BaseModel):
    """Distribution of prescribed item counts per visit."""
    single_item_visits: int = 0
    multi_item_visits: int = 0
    max_items_in_single_visit: int = 0


class AnalyticsReport(BaseModel):
    """Comprehensive analytics computed deterministically."""
    clinic_id: str
    date: str
    revenue_by_hour: list[HourlyRevenue] = []
    peak_hour: Optional[int] = None
    peak_hour_revenue_paise: int = 0
    top_drugs_by_quantity: list[DrugRanking] = []
    top_drugs_by_revenue: list[DrugRanking] = []
    doctor_performance: list[DoctorPerformance] = []
    avg_visit_value_paise: int = 0
    avg_items_per_visit: float = 0.0
    shifts: list[ShiftBreakdown] = []
    price_tiers: list[PriceTierShare] = []
    polypharmacy: Optional[PolypharmacyStats] = None
    effective_discount_rate_pct: float = 0.0


class TracedFigure(BaseModel):
    """Maps a number in the narrative to its source field."""
    figure: str
    source_field: str
    source_value: str


class NarrativeResponse(BaseModel):
    """LLM-generated narrative with traced figures."""
    clinic_id: str
    date: str
    narrative: str
    traced_figures: list[TracedFigure] = []
    llm_model: str = ""
    error: Optional[str] = None


class FullReport(BaseModel):
    """Combined response containing all three layers."""
    reconciliation: ReconciliationReport
    analytics: AnalyticsReport
    narrative: Optional[NarrativeResponse] = None
