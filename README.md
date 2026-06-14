# BP Now — Financial Intelligence Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)

This repository is a **monorepo** housing the frameworks and systems that compose the
**BP Now Financial Intelligence Platform** — a suite of open-source tools designed to
empower Small and Medium Enterprises (SMEs) with AI-driven financial intelligence.

---

## Frameworks & Systems

| Directory | Name | Description | Status |
|---|---|---|---|
| [`AFIS/`](AFIS/) | **AI-Powered Financial Intelligence System** | ETL ingestion, ML cash flow forecasting, AI Financial Analyst, NIST AI RMF 1.0 compliance, glassmorphic dashboard | `v0.2.1` — Active |

---

## Getting Started

Each framework is self-contained inside its own directory.
Navigate to the desired system and follow its local `README.md`:

```bash
git clone https://github.com/Albertsfc/AFIS-Core-Framework.git
cd AFIS-Core-Framework/AFIS
pip install -r requirements.txt
python run.py
```

---

## Repository Structure

```
AFIS-Core-Framework/
└── AFIS/               ← AI-Powered Financial Intelligence System
    ├── app/            ← FastAPI backend (ETL, ML, AI Agent)
    ├── data/           ← Sample datasets
    ├── docs/           ← Architecture documentation
    ├── frontend/       ← Glassmorphic web dashboard
    ├── tests/          ← pytest suite
    ├── run.py          ← Single-command launcher
    ├── requirements.txt
    ├── CHANGELOG.md
    └── README.md
```

---

## License

All projects in this repository are licensed under the [MIT License](AFIS/LICENSE).
