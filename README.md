# SwasthiQ: EOD Billing & Analytics Agent

A full-stack financial reconciliation and operational intelligence platform that ingests a clinic's daily billing log and produces:
1. **Deterministic EOD Reconciliation**: Gross billed, net collected, outstanding balance, and refunds (split by payment channel).
2. **Advanced Operational Analytics**: Hourly revenue velocity, shift distribution, price-tier breakdown, polypharmacy rate, AOV, and doctor prescription leaderboards.
3. **Executive Narrative Briefing**: AI-synthesized operational overview using OpenRouter 100% Free Models (`$0` cost) with deterministic figure lineage tracing.
4. **Auto-Seeding & Instant Preview**: Automatically pre-loads sample billing logs on initial startup so the dashboard is immediately ready.
5. **One-Click CSV Audit Export**: Instant export of financial settlement reports for accounting.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, Pydantic, SQLite |
| Frontend | React 18, Vite, Recharts, React Router |
| Design System | Warm Porcelain & Ocean Cobalt Fintech System |
| LLM | OpenRouter Free Tier API ($0 cost `:free` models with automatic failover) |
| Testing | pytest (17 automated tests) |

---

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI entry point, static SPA serving & auto-seed
│   │   ├── models.py          # Pydantic schemas (input + output)
│   │   ├── parser.py          # JSON parsing + per-row validation
│   │   ├── reconciliation.py  # Deterministic EOD reconciliation
│   │   ├── analytics.py       # Deterministic analytics & shift metrics
│   │   ├── narrative.py       # OpenRouter LLM narrative + free model failover + figure tracing
│   │   ├── database.py        # SQLite persistence layer
│   │   ├── routes.py          # REST API endpoints
│   │   └── tests/
│   │       └── test_billing.py # 17 tests covering parser, reconciliation, analytics & LLM
│   ├── .python-version        # Python 3.12.8 deployment pin
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api/client.js      # API client (relative /api routing + VITE_API_BASE_URL)
│   │   ├── utils/exportCsv.js # One-click CSV export utility
│   │   ├── components/
│   │   │   ├── HeaderNav.jsx             # Top navigation header & upload/export controls
│   │   │   ├── ReconciliationDashboard.jsx# Executive ledger & KPI cards
│   │   │   ├── AnalyticsPage.jsx          # Velocity chart, shift cards & doctor leaderboards
│   │   │   └── NarrativePage.jsx          # Executive briefing memo & lineage ledger
│   │   └── index.css          # Executive design system
│   ├── public/_redirects      # SPA routing fallback for Netlify
│   └── index.html
│
├── netlify.toml               # Netlify deployment configuration
├── billing_log_2026-07-25.json # Sample data (refund-only day)
├── billing_log_2026-07-26.json # Sample data (empty day)
├── billing_log_2026-07-27.json # Sample data (normal day)
└── README.md
```

---

## Quick Start (Local Development)

### Prerequisites
- Python 3.10+ with pip
- Node.js 18+ with npm

### Backend Setup

```bash
cd backend
pip install -r requirements.txt

# Optional: Set OpenRouter API key for LLM narratives in backend/.env
# Get a free key at: https://openrouter.ai/
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Start the backend server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend runs on `http://localhost:5173` and automatically proxies `/api` calls to the backend on `http://localhost:8000`.

### Run Automated Tests

```bash
cd backend
python -m pytest app/tests/ -v
```

---

## LLM Narrative Integration (OpenRouter $0 Free Models)

Narrative briefings use OpenRouter with zero-cost `$0` models. It features **automatic failover** across free models:
1. `google/gemini-2.0-flash-lite-preview-02-05:free`
2. `meta-llama/llama-3.3-70b-instruct:free`
3. `google/gemini-2.0-flash-exp:free`
4. `qwen/qwen-2.5-coder-32b-instruct:free`
5. `deepseek/deepseek-r1:free`
6. `mistralai/mistral-7b-instruct:free`

If an API key is not configured or an endpoint is unreachable, the system gracefully generates a **deterministic fallback narrative** with figure lineage tracing.

---

## Deployment Options

### Option 1: Single-Service All-in-One Deployment (Render / Railway)
FastAPI automatically serves the built React SPA on `/` and API endpoints on `/api`.

- **Build Command**:
  ```bash
  cd frontend && npm install && npm run build && cd ../backend && pip install -r requirements.txt
  ```
- **Start Command**:
  ```bash
  python -m uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
  ```
- **Environment Variables**:
  `OPENROUTER_API_KEY` = `your_openrouter_api_key_here`

### Option 2: Decoupled Deployment (Netlify + Render)
- **Frontend (Netlify)**:
  - Base Directory: `frontend`
  - Build Command: `npm run build`
  - Publish Directory: `dist`
  - Environment Variable: `VITE_API_BASE_URL` = `https://your-backend-service.onrender.com/api`

---

## REST API Contract

Base URL: `/api` (or `http://localhost:8000/api`)

### `POST /api/upload`
Upload a billing log JSON file for processing.

### `GET /api/reports`
List all available reports.

### `GET /api/reports/{clinic_id}/{date}`
Get the full report (reconciliation + analytics + narrative).

### `GET /api/reconciliation/{clinic_id}/{date}`
Get reconciliation data only.

### `GET /api/analytics/{clinic_id}/{date}`
Get analytics data only.

### `GET /api/narrative/{clinic_id}/{date}`
Get the executive briefing with traced figures.

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

17 tests covering:
- **Parser**: Malformed row detection, empty file, refund validation, invalid JSON, non-array input
- **Reconciliation**: Normal day math, empty day zeros, refund-only day, payment mode breakdown
- **Analytics**: Revenue bucketing, peak hour detection, drug ranking order, typo handling, empty/refund-only days
- **Narrative**: Fallback behavior when API key is missing, mocked OpenRouter response, and dynamic model selection
