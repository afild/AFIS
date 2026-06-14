# AFIS Architecture Overview

## Pipeline

```
Raw Financial Data (CSV)
        │
        ▼
┌──────────────────────┐
│   ETL Ingestor       │  Validates schema, normalizes dates/currencies,
│   (app/etl/          │  rejects duplicates and outliers, writes to SQLite
│    ingestor.py)      │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│   SQLite Database    │  Local file (afis_finance.db) — no server required
│   (afis_finance.db)  │  Stores transactions, audit logs, model artifacts
└──────┬───────┬───────┘
       │       │
       ▼       ▼
┌──────────┐  ┌─────────────────────────┐
│ ML Engine│  │ AI Financial Analyst    │
│ (Ridge   │  │ (app/llm_client.py)     │
│  Regress)│  │ LLM mode: Claude Haiku  │
│          │  │ Offline mode: heuristics│
└────┬─────┘  └──────────┬──────────────┘
     │                   │
     └─────────┬─────────┘
               │
               ▼
┌──────────────────────┐
│   FastAPI Backend    │  REST API — serves the dashboard and exposes
│   (app/main.py)      │  endpoints for data ingestion, analysis, forecast
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│   Web Dashboard      │  Chart.js visualizations, AI narrative panel,
│   (frontend/)        │  CSV upload interface, responsive dark-mode UI
└──────────────────────┘
```

## Key Design Decisions

**Local-first:** All data stays on the SME's machine by default. No cloud storage,
no third-party data transmission (except optional LLM API calls, which send only
aggregated metrics, never raw transaction data).

**Privacy by design:** The LLM integration sends only computed financial
metrics to the API — never raw transaction records. This aligns with NIST AI RMF
transparency and accountability requirements.

**Zero-server dependency:** SQLite requires no database server. The entire stack
runs with `python run.py` from any machine with Python 3.10+.

**Provider-agnostic LLM:** The `llm_client.py` abstraction layer allows substituting
any LLM provider. The Anthropic integration is the reference implementation.

## NIST AI RMF Alignment

| NIST Function | AFIS Implementation |
|---------------|---------------------|
| GOVERN | MIT License, open audit logs, CONTRIBUTING.md |
| MAP | Financial domain scoped to SME use cases, documented limitations |
| MEASURE | Automated test suite, model performance tracked per run |
| MANAGE | Offline fallback, anomaly flagging in ETL, traceable decisions |

## Module Responsibilities

| Module | Responsibility |
|--------|---------------|
| `app/main.py` | FastAPI app, route registration, static file serving |
| `app/etl/ingestor.py` | CSV ingestion, validation, SQLite writes |
| `app/forecasting/model.py` | Ridge regression model, 12-month projection |
| `app/llm_client.py` | LLM integration with offline fallback |
| `app/ai_agent/analyst.py` | Financial metrics computation, narrative generation |
| `app/database/db_manager.py` | SQLite connection, schema init, compliance logging |
| `frontend/` | Dashboard HTML/CSS/JS, Chart.js charts |
| `data/examples/` | Synthetic SME dataset for demo and testing |
| `tests/` | pytest suite |
