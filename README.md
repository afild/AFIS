# AFIS — AI-Powered Financial Intelligence System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)

a suite of open-source tools designed to empower Small and Medium Enterprises (SMEs) with AI-driven financial intelligence.

---

## AFIS

| Directory | Description | Version |
|---|---|---|
| [`AFIS/`](AFIS/) | **AI-Powered Financial Intelligence System** — ETL ingestion, Ridge regression cash flow forecasting, AI Financial Analyst, NIST AI RMF 1.0 aligned compliance logging, glassmorphic web dashboard | `v0.2.1` |

---

## Quickstart

```bash
git clone https://github.com/Albertsfc/AFIS-Core-Framework.git
cd AFIS-Core-Framework/AFIS
pip install -r requirements.txt
python run.py
```

See [`AFIS/README.md`](AFIS/README.md) for full documentation, architecture diagrams, REST API reference, and contributing guidelines.

---

## Repository Structure

```
AFIS-Core-Framework/
└── AFIS/                ← AI-Powered Financial Intelligence System
    ├── app/             ← FastAPI backend (ETL, ML, AI Agent)
    ├── data/            ← Synthetic SME datasets for demo and testing
    ├── docs/            ← Architecture documentation and diagrams
    ├── frontend/        ← Glassmorphic dark-mode web dashboard
    ├── tests/           ← pytest suite
    ├── run.py           ← Single-command launcher
    ├── requirements.txt
    ├── CHANGELOG.md
    └── README.md        ← Full technical documentation
```

---

## License

MIT License — see [`AFIS/LICENSE`](AFIS/LICENSE).
