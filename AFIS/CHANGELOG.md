# Changelog

All notable changes to **AFIS Core Framework** are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) conventions,
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [0.2.1] — 2026-04-28

### Changed
- Finalized README with accurate feature descriptions and updated badge set
- Added v0.2.0 release notes section to project documentation
- Revised architecture overview for clarity on ETL-to-API data flow
- Minor copy fixes and formatting consistency across all Markdown files

---

## [0.2.0] — 2026-03-11

### Added
- `.env.example` template documenting all required and optional environment variables
- Expanded `.gitignore` to cover virtual environments, `.env` files, and IDE artifacts
- Improved local developer onboarding experience (DX): setup now requires zero manual configuration for offline mode

### Changed
- Unified environment variable naming across `run.py`, `app/main.py`, and documentation

---

## [0.1.4] — 2026-01-20

### Added
- `CONTRIBUTING.md`: guidelines for issue reporting, feature requests, pull requests, and code style
- `docs/architecture.md`: detailed technical architecture document covering component responsibilities, data flow, and NIST AI RMF 1.0 mapping
- Developer onboarding section in README linking to contribution guide

---

## [0.1.3] — 2025-11-03

### Added
- Full `pytest` test suite under `tests/test_core.py` covering:
  - ETL ingestion pipeline: validation rules, duplicate detection, and outlier handling
  - ML forecasting engine: model training lifecycle and 12-month projection accuracy
  - FastAPI endpoints: `/api/transactions`, `/api/forecast`, `/api/analysis`, `/api/system/status`
- Test coverage for offline fallback mode (no API key required)

### Changed
- Improved error handling in `app/etl/ingestor.py` to surface structured validation failures during testing

---

## [0.1.2] — 2025-08-17

### Added
- `app/llm_client.py`: LLM client module integrating Anthropic Claude for natural-language financial narrative generation
- Offline fallback mode: when `ANTHROPIC_API_KEY` is not set, the Financial Analyst agent reverts to rule-based heuristic analysis automatically
- `/api/system/status` endpoint reporting active AI mode (`llm` or `offline`) and model version
- `requirements.txt` updated with `anthropic` SDK dependency

### Changed
- Refactored `app/ai_agent/analyst.py` to delegate LLM calls to the new `llm_client` module, improving separation of concerns
- Updated `app/main.py` to initialize LLM client at startup and inject into analyst agent

---

## [0.1.1] — 2025-01-09

### Added
- Synthetic 24-month SME transaction dataset (`data/examples/sample_sme_transactions.csv`) for immediate demo and testing
- Auto-load logic in `run.py`: if no database is found, the system seeds itself from the sample dataset automatically

### Changed
- Updated README Quickstart section to document the auto-load behavior

---

## [0.0.2] — 2024-10-22

### Fixed
- Corrected broken installation URL in README (`git clone` command now points to the correct repository path)
- Added repository description and recommended GitHub Topics for discoverability

---

## [0.0.1] — 2023-02-14

### Added
- **FastAPI backend server** with SQLite database integration via `app/database/db_manager.py` and `app/database/schema.sql`
- **Automated ETL ingestion pipeline** (`app/etl/ingestor.py`): currency and date formatting, duplicate removal, outlier detection, and NIST-aligned validation rules
- **Machine Learning Cash Flow Forecasting engine** (`app/forecasting/model.py`): Ridge regression model trained on historical transaction sequences, projecting 12-month revenue, expense, and net cash flow trends with confidence intervals
- **Financial Analyst reporting module** (`app/ai_agent/analyst.py`): rule-based agent computing Burn Rate, Runway, Net Profit Margin, and flagging financial red flags with strategic recommendations
- **NIST AI RMF 1.0 compliance logging**: persistent audit trail for all ETL actions, model parameters, and analyst outputs
- **Premium glassmorphic web dashboard** (`frontend/`): dark-mode UI with Chart.js interactive visualizations, responsive CSS Grid layout, and real-time API integration
- `run.py`: single-command server launcher
- `requirements.txt`, `LICENSE` (MIT), and initial `README.md`

---

[Unreleased]: https://github.com/Albertsfc/AFIS-Core-Framework/compare/v0.2.1...HEAD
[0.2.1]: https://github.com/Albertsfc/AFIS-Core-Framework/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/Albertsfc/AFIS-Core-Framework/compare/v0.1.4...v0.2.0
[0.1.4]: https://github.com/Albertsfc/AFIS-Core-Framework/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/Albertsfc/AFIS-Core-Framework/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/Albertsfc/AFIS-Core-Framework/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/Albertsfc/AFIS-Core-Framework/compare/v0.0.2...v0.1.1
[0.0.2]: https://github.com/Albertsfc/AFIS-Core-Framework/compare/v0.0.1...v0.0.2
[0.0.1]: https://github.com/Albertsfc/AFIS-Core-Framework/releases/tag/v0.0.1
