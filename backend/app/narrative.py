"""
LLM narrative generation with figure tracing.

Takes the deterministic reconciliation + analytics reports as structured
input and generates a WhatsApp-friendly summary. Every figure in the
narrative is traced back to its source field.

Uses Google Gemini (gemini-2.0-flash) — free tier available.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
from typing import Any

from .models import (
    AnalyticsReport,
    NarrativeResponse,
    ReconciliationReport,
    TracedFigure,
)


def _paise_to_rupees_str(paise: int) -> str:
    """Convert integer paise to a human-readable rupee string."""
    rupees = paise / 100
    if rupees == int(rupees):
        return f"₹{int(rupees)}"
    return f"₹{rupees:.2f}"


def _build_report_context(
    recon: ReconciliationReport, analytics: AnalyticsReport
) -> str:
    """Build a structured text block of all deterministic figures."""

    lines = [
        "=== EOD RECONCILIATION ===",
        f"Clinic: {recon.clinic_id}",
        f"Date: {recon.date}",
        f"Total Visits (sales): {recon.total_visits}",
        f"Total Refund Visits: {recon.total_refund_visits}",
        "",
        f"Total Billed: {recon.total_billed_paise} paise ({_paise_to_rupees_str(recon.total_billed_paise)})",
        f"Total Discount: {recon.total_discount_paise} paise ({_paise_to_rupees_str(recon.total_discount_paise)})",
        f"Total Collected: {recon.total_collected_paise} paise ({_paise_to_rupees_str(recon.total_collected_paise)})",
        f"Outstanding: {recon.outstanding_paise} paise ({_paise_to_rupees_str(recon.outstanding_paise)})",
        f"Total Refunds: {recon.total_refunds_paise} paise ({_paise_to_rupees_str(recon.total_refunds_paise)})",
        "",
        "Payment Mode Breakdown:",
    ]

    for pm in recon.by_payment_mode:
        lines.append(
            f"  {pm.payment_mode}: billed={pm.total_billed_paise} paise, "
            f"discount={pm.total_discount_paise} paise, "
            f"collected={pm.total_collected_paise} paise, "
            f"outstanding={pm.outstanding_paise} paise, "
            f"refunds={pm.total_refunds_paise} paise"
        )

    lines.append("")
    lines.append("=== ANALYTICS ===")

    if analytics.peak_hour is not None:
        lines.append(
            f"Peak Hour: {analytics.peak_hour}:00 UTC with "
            f"{analytics.peak_hour_revenue_paise} paise "
            f"({_paise_to_rupees_str(analytics.peak_hour_revenue_paise)})"
        )
    else:
        lines.append("Peak Hour: N/A (no sales)")

    lines.append("")
    lines.append("Revenue by Hour:")
    for h in analytics.revenue_by_hour:
        lines.append(
            f"  {h.hour}:00 — {h.revenue_paise} paise "
            f"({_paise_to_rupees_str(h.revenue_paise)}), {h.visit_count} visit(s)"
        )

    lines.append("")
    lines.append("Top Drugs by Quantity:")
    for d in analytics.top_drugs_by_quantity:
        lines.append(f"  #{d.rank} {d.drug_name}: {d.value} units")

    lines.append("")
    lines.append("Top Drugs by Revenue:")
    for d in analytics.top_drugs_by_revenue:
        lines.append(
            f"  #{d.rank} {d.drug_name}: {d.value} paise "
            f"({_paise_to_rupees_str(d.value)})"
        )

    if recon.validation_errors:
        lines.append("")
        lines.append("Validation Errors (rows skipped):")
        for err in recon.validation_errors:
            lines.append(f"  - {err}")

    return "\n".join(lines)


def _build_figure_lookup(
    recon: ReconciliationReport, analytics: AnalyticsReport
) -> dict[str, str]:
    """
    Build a lookup mapping formatted values to their source fields,
    used for post-hoc verification of the narrative.
    """
    lookup: dict[str, str] = {}

    # Reconciliation figures
    figures = {
        "total_billed_paise": recon.total_billed_paise,
        "total_discount_paise": recon.total_discount_paise,
        "total_collected_paise": recon.total_collected_paise,
        "outstanding_paise": recon.outstanding_paise,
        "total_refunds_paise": recon.total_refunds_paise,
        "total_visits": recon.total_visits,
        "total_refund_visits": recon.total_refund_visits,
    }

    for field, val in figures.items():
        lookup[str(val)] = field
        if isinstance(val, int) and val != 0:
            # Also map the rupee string
            rupees_str = _paise_to_rupees_str(val)
            lookup[rupees_str] = field

    # Payment mode figures
    for pm in recon.by_payment_mode:
        prefix = f"by_payment_mode.{pm.payment_mode}"
        for attr in ("total_billed_paise", "total_discount_paise",
                      "total_collected_paise", "outstanding_paise",
                      "total_refunds_paise"):
            val = getattr(pm, attr)
            if val != 0:
                lookup[str(val)] = f"{prefix}.{attr}"
                lookup[_paise_to_rupees_str(val)] = f"{prefix}.{attr}"

    # Analytics figures
    if analytics.peak_hour is not None:
        lookup[str(analytics.peak_hour)] = "peak_hour"
        lookup[f"{analytics.peak_hour}:00"] = "peak_hour"
        lookup[str(analytics.peak_hour_revenue_paise)] = "peak_hour_revenue_paise"
        lookup[_paise_to_rupees_str(analytics.peak_hour_revenue_paise)] = "peak_hour_revenue_paise"

    for h in analytics.revenue_by_hour:
        key = f"revenue_by_hour.{h.hour}"
        lookup[str(h.revenue_paise)] = key
        lookup[_paise_to_rupees_str(h.revenue_paise)] = key

    for d in analytics.top_drugs_by_quantity:
        lookup[str(d.value)] = f"top_drugs_by_quantity.{d.drug_name}.qty"

    for d in analytics.top_drugs_by_revenue:
        lookup[str(d.value)] = f"top_drugs_by_revenue.{d.drug_name}.revenue"
        lookup[_paise_to_rupees_str(d.value)] = f"top_drugs_by_revenue.{d.drug_name}.revenue"

    return lookup


SYSTEM_PROMPT = """You are a concise clinic analytics assistant. 
You generate professional end-of-day summaries for clinic owners.

CRITICAL RULES:
1. Use ONLY the numbers provided in the report below. Do NOT invent, estimate, or round any figure.
2. Format money as ₹ rupees (e.g., ₹1,200 for 120000 paise). Convert paise to rupees by dividing by 100.
3. If a metric cannot be computed from the data (e.g., profit, cost price), say so plainly. Do NOT approximate.
4. Keep it brief, professional, and clear. Do NOT use emojis.
5. Mention: total billed, total collected, outstanding, refunds, peak hour, top drugs.
6. If there were validation errors (skipped rows), mention how many rows were skipped.
7. If it was a zero-transaction day, say so clearly.
8. If it was a refund-only day, highlight that clearly.

Return your response as valid JSON with this exact structure:
{
  "narrative": "The summary text here",
  "traced_figures": [
    {"figure": "₹1,200", "source_field": "total_collected_paise", "source_value": "120000"}
  ]
}

The traced_figures array must map EVERY monetary figure and count in your narrative
back to its source field from the report. This is mandatory."""


def _get_api_key() -> str:
    """Retrieve Gemini API key from environment variable or .env file."""
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if api_key:
        return api_key

    # Check for .env file in backend/ directory or root directory
    candidates = [
        Path(__file__).parent.parent / ".env",
        Path(__file__).parent.parent.parent / ".env",
    ]
    for env_path in candidates:
        if env_path.is_file():
            try:
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line.startswith("GEMINI_API_KEY="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val:
                            os.environ["GEMINI_API_KEY"] = val
                            return val
            except Exception:
                pass

    return ""


async def generate_narrative(
    recon: ReconciliationReport,
    analytics: AnalyticsReport,
) -> NarrativeResponse:
    """
    Generate an LLM narrative from the deterministic reports.

    Falls back gracefully if the LLM is unavailable or returns garbage.
    """
    api_key = _get_api_key()

    report_context = _build_report_context(recon, analytics)
    figure_lookup = _build_figure_lookup(recon, analytics)

    if not api_key:
        return _build_fallback_narrative(recon, analytics, figure_lookup,
                                         error="GEMINI_API_KEY not set: using deterministic fallback")

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")

        prompt = f"{SYSTEM_PROMPT}\n\n--- REPORT DATA ---\n{report_context}"

        response = model.generate_content(prompt)
        raw_text = response.text.strip()

        # Try to extract JSON from the response
        parsed = _extract_json(raw_text)

        if parsed and "narrative" in parsed:
            traced = []
            for tf in parsed.get("traced_figures", []):
                if isinstance(tf, dict) and "figure" in tf:
                    traced.append(TracedFigure(
                        figure=str(tf.get("figure", "")),
                        source_field=str(tf.get("source_field", "")),
                        source_value=str(tf.get("source_value", "")),
                    ))

            return NarrativeResponse(
                clinic_id=recon.clinic_id,
                date=recon.date,
                narrative=parsed["narrative"],
                traced_figures=traced,
                llm_model="gemini-2.0-flash",
            )
        else:
            # LLM returned something but not in expected format
            return _build_fallback_narrative(
                recon, analytics, figure_lookup,
                error="LLM response was not in expected JSON format: using deterministic fallback"
            )

    except Exception as e:
        return _build_fallback_narrative(
            recon, analytics, figure_lookup,
            error=f"LLM call failed: {str(e)}: using deterministic fallback"
        )


def _extract_json(text: str) -> dict | None:
    """Try to extract a JSON object from LLM output (may be wrapped in markdown fences)."""
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"```\s*$", "", text, flags=re.MULTILINE)
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                return None
        return None


def _build_fallback_narrative(
    recon: ReconciliationReport,
    analytics: AnalyticsReport,
    figure_lookup: dict[str, str],
    error: str = "",
) -> NarrativeResponse:
    """
    Build a deterministic narrative without LLM.
    Ensures every number traces back to the report.
    """
    traced: list[TracedFigure] = []

    # Handle special days
    if recon.total_visits == 0 and recon.total_refund_visits == 0:
        narrative = (
            f"*EOD Summary ({recon.date})*\n\n"
            f"No transactions recorded today. The clinic had zero billing activity."
        )
        return NarrativeResponse(
            clinic_id=recon.clinic_id,
            date=recon.date,
            narrative=narrative,
            traced_figures=[],
            llm_model="deterministic-fallback",
            error=error,
        )

    parts = [f"*EOD Summary ({recon.date})*\n"]

    if recon.total_visits > 0:
        billed_str = _paise_to_rupees_str(recon.total_billed_paise)
        collected_str = _paise_to_rupees_str(recon.total_collected_paise)
        outstanding_str = _paise_to_rupees_str(recon.outstanding_paise)

        parts.append(
            f"*Billed:* {billed_str} | *Collected:* {collected_str} | "
            f"*Outstanding:* {outstanding_str}"
        )
        traced.extend([
            TracedFigure(figure=billed_str, source_field="total_billed_paise",
                        source_value=str(recon.total_billed_paise)),
            TracedFigure(figure=collected_str, source_field="total_collected_paise",
                        source_value=str(recon.total_collected_paise)),
            TracedFigure(figure=outstanding_str, source_field="outstanding_paise",
                        source_value=str(recon.outstanding_paise)),
        ])

        if recon.total_discount_paise > 0:
            disc_str = _paise_to_rupees_str(recon.total_discount_paise)
            parts.append(f"*Discounts given:* {disc_str}")
            traced.append(TracedFigure(figure=disc_str, source_field="total_discount_paise",
                                      source_value=str(recon.total_discount_paise)))

        parts.append(f"{recon.total_visits} sale(s) processed.")
        traced.append(TracedFigure(figure=str(recon.total_visits), source_field="total_visits",
                                  source_value=str(recon.total_visits)))

    if recon.total_refunds_paise > 0:
        refund_str = _paise_to_rupees_str(recon.total_refunds_paise)
        parts.append(f"*Refunds:* {refund_str} ({recon.total_refund_visits} refund(s))")
        traced.extend([
            TracedFigure(figure=refund_str, source_field="total_refunds_paise",
                        source_value=str(recon.total_refunds_paise)),
            TracedFigure(figure=str(recon.total_refund_visits), source_field="total_refund_visits",
                        source_value=str(recon.total_refund_visits)),
        ])

    if recon.total_visits == 0 and recon.total_refund_visits > 0:
        parts.append("\n*Refund-only day*: no new sales were recorded.")

    if analytics.peak_hour is not None:
        peak_rev_str = _paise_to_rupees_str(analytics.peak_hour_revenue_paise)
        parts.append(f"\n*Peak hour:* {analytics.peak_hour}:00 UTC ({peak_rev_str})")
        traced.extend([
            TracedFigure(figure=f"{analytics.peak_hour}:00", source_field="peak_hour",
                        source_value=str(analytics.peak_hour)),
            TracedFigure(figure=peak_rev_str, source_field="peak_hour_revenue_paise",
                        source_value=str(analytics.peak_hour_revenue_paise)),
        ])

    if analytics.top_drugs_by_quantity:
        top_q = analytics.top_drugs_by_quantity[0]
        parts.append(f"*Top drug (qty):* {top_q.drug_name} ({top_q.value} units)")
        traced.append(TracedFigure(figure=str(top_q.value),
                                  source_field=f"top_drugs_by_quantity.{top_q.drug_name}.qty",
                                  source_value=str(top_q.value)))

    if analytics.top_drugs_by_revenue:
        top_r = analytics.top_drugs_by_revenue[0]
        rev_str = _paise_to_rupees_str(top_r.value)
        parts.append(f"*Top drug (revenue):* {top_r.drug_name} ({rev_str})")
        traced.append(TracedFigure(figure=rev_str,
                                  source_field=f"top_drugs_by_revenue.{top_r.drug_name}.revenue",
                                  source_value=str(top_r.value)))

    if recon.validation_errors:
        parts.append(f"\n{len(recon.validation_errors)} row(s) skipped due to validation errors.")

    parts.append("\n_Note: Profit cannot be computed (cost price data not available)._")

    narrative = "\n".join(parts)

    return NarrativeResponse(
        clinic_id=recon.clinic_id,
        date=recon.date,
        narrative=narrative,
        traced_figures=traced,
        llm_model="deterministic-fallback",
        error=error if error else None,
    )
