# SwasthiQ: EOD Billing & Analytics Agent

A full-stack financial reconciliation and operational intelligence platform that ingests a clinic's daily billing log and produces:
1. **Deterministic EOD Reconciliation**: Gross billed, net collected, outstanding balance, and refunds (split by payment channel).
2. **Advanced Operational Analytics**: Hourly revenue velocity, shift distribution, price-tier breakdown, polypharmacy rate, AOV, and doctor prescription leaderboards.
3. **Executive Narrative Briefing**: AI-synthesized operational overview with deterministic figure lineage tracing.
4. **One-Click CSV Audit Export**: Instant export of financial settlement reports for accounting.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, Pydantic, SQLite |
| Frontend | React 18, Vite, Recharts, React Router |
| Design System | Warm Porcelain & Ocean Cobalt Fintech System |
| LLM | OpenRouter API (with deterministic fallback) |
| Testing | pytest |

---

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI entry point + CORS
│   │   ├── models.py          # Pydantic schemas (input + output)
│   │   ├── parser.py          # JSON parsing + per-row validation
│   │   ├── reconciliation.py  # Deterministic EOD reconciliation
│   │   ├── analytics.py       # Deterministic analytics & shift metrics
│   │   ├── narrative.py       # LLM narrative + figure tracing
│   │   ├── database.py        # SQLite persistence layer
│   │   ├── routes.py          # REST API endpoints
│   │   └── tests/
│   │       └── test_billing.py # 14 tests covering all edge cases
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api/client.js      # API client + helpers
│   │   ├── utils/exportCsv.js # One-click CSV export utility
│   │   ├── components/
│   │   │   ├── HeaderNav.jsx             # Top navigation header & upload/export controls
│   │   │   ├── ReconciliationDashboard.jsx# Executive ledger & KPI cards
│   │   │   ├── AnalyticsPage.jsx          # Velocity chart, shift cards & doctor leaderboards
│   │   │   └── NarrativePage.jsx          # Executive briefing memo & lineage ledger
│   │   └── index.css          # Executive design system
│   └── index.html
│
├── billing_log_2026-07-25.json  # Sample data (refund-only day)
├── billing_log_2026-07-26.json  # Sample data (empty day)
├── billing_log_2026-07-27.json  # Sample data (normal day)
└── README.md
```

---

## Quick Start

### Prerequisites
- Python 3.10+ with pip
- Node.js 18+ with npm

### Backend Setup

```bash
cd backend
pip install -r requirements.txt

# Optional: Set OpenRouter API key for LLM narratives in backend/.env
# Without it, the system uses a deterministic fallback narrative
# OPENROUTER_API_KEY=your-api-key-here

# Start the server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend runs on `http://localhost:5173` and the backend on `http://localhost:8000`.

### Run Tests

```bash
cd backend
python -m pytest app/tests/ -v
```

---

## REST API Contract

Base URL: `http://localhost:8000`

### `POST /api/upload`

Upload a billing log JSON file for processing.

**Request:** `multipart/form-data` with `file` field (`.json` file)

**Response (200):**
```json
{
  "status": "success",
  "clinic_id": "CLN-KNP-014",
  "date": "2026-07-27",
  "records_processed": 19,
  "records_rejected": 0,
  "validation_errors": [],
  "reconciliation": { ... },
  "analytics": { ... },
  "narrative": { ... }
}
```

**Error Response (400):**
```json
{
  "detail": "Invalid JSON: ..."
}
```

### `GET /api/reports`

List all available reports.

**Response:** `[{ "clinic_id": "...", "date": "...", "created_at": "..." }]`

### `GET /api/reports/{clinic_id}/{date}`

Get the full report (reconciliation + analytics + narrative).

### `GET /api/reconciliation/{clinic_id}/{date}`

Get reconciliation data only.

### `GET /api/analytics/{clinic_id}/{date}`

Get analytics data only.

### `GET /api/narrative/{clinic_id}/{date}`

Get the executive brief with traced figures.

---

## Architecture & Data Consistency

### Deterministic Layer (Ground Truth)
The reconciliation and analytics modules are **pure functions** — they take validated billing records as input and produce deterministic output. No LLM calls are ever made in this layer. This guarantees:

- **Consistency**: Same input always produces the same output
- **Auditability**: Every computed number can be traced to specific input records
- **Testability**: Covered by automated tests with hand-verified expected values

### Key Computation Formulas
- **Total Billed** = Σ(line_item.qty × unit_price_paise) for non-refund rows
- **Total Collected** = Σ(amount_paid_paise) for non-refund rows
- **Outstanding** = Total Billed − Total Discounts − Total Collected
- **Total Refunds** = Σ(|amount_paid_paise|) for refund rows (always positive)
- **AOV (Average Consultation Value)** = Total Collected / Total Sales Visits
- **Polypharmacy Rate** = % of prescriptions containing 2+ line items

### Money Representation
All monetary values are **integer paise** throughout the stack — from database storage to API responses. This avoids floating-point precision issues entirely. The frontend converts to ₹ rupees for display.

### Data Validation Strategy
Each row is validated independently using Pydantic models with strict types:
- Missing `payment_mode` → defaults gracefully to cash (`default=PaymentMode.cash`)
- Refund rows must have `amount_paid_paise ≤ 0`
- Drug names are normalised to uppercase (typos like `PARACETMOL` are preserved as separate data entries)
- Bad rows are logged, valid rows are processed — one bad row doesn't reject the whole file

### Narrative Grounding
The LLM receives **only** the deterministic report as input and is explicitly instructed:
1. Use only the provided numbers — zero invented figures
2. Do not use emojis — maintain a professional executive tone
3. If a metric can't be computed (e.g., profit without cost price), say so plainly
4. Return a structured JSON with `traced_figures` mapping every number to its source

If the LLM response is malformed or unavailable, a deterministic fallback narrative is generated with perfect figure tracing.

---

## Edge Cases Handled

| Scenario | File | Handling |
|---------|------|---------|
| Missing `payment_mode` | July 27 (V-019) | Defaults gracefully to cash; processed as valid sale record |
| Drug name typo (`PARACETMOL`) | July 27 (V-009) | Tracked as separate drug entry — data issue, not schema violation |
| Amount mismatch | July 27 (V-016) | `amount_paid_paise` ≠ line_items total — shows as outstanding |
| Empty day (zero transactions) | July 26 | Returns all-zero reconciliation; analytics shows "No sales data" |
| Refund-only day | July 25 | Correctly reports zero billed/collected, non-zero refunds |
| Invalid JSON input | N/A | Returns 400 with clear error message |
| Non-array JSON | N/A | Returns 400 with "Expected a JSON array" |
| LLM unavailable | N/A | Falls back to deterministic narrative with full figure tracing |
| LLM returns garbage | N/A | Falls back gracefully — never corrupts output or crashes |

---

## Test Coverage

14 tests covering:
- **Parser**: Malformed row detection, empty file, refund validation, invalid JSON, non-array input
- **Reconciliation**: Normal day math, empty day zeros, refund-only day, payment mode breakdown
- **Analytics**: Revenue bucketing, peak hour detection, drug ranking order, typo handling, empty/refund-only days
