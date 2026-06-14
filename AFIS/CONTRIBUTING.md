# Contributing to AFIS

Thank you for your interest in contributing to the AI Financial Intelligence System.
AFIS is MIT-licensed and welcomes contributions from developers, financial analysts,
and SME practitioners.

## How to Contribute

### Reporting Issues
Open a GitHub Issue describing the problem, expected behavior, and steps to reproduce.

### Suggesting Features
Open a GitHub Issue with the label `enhancement`. Describe the use case for a U.S. SME
and why the current system does not address it.

### Submitting Code

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/your-feature-name`
3. Make your changes and add tests under `tests/`
4. Ensure all tests pass: `pytest tests/ -v`
5. Open a Pull Request against `main` with a description of your changes

### Code Style
- Follow PEP 8 for Python
- Add docstrings to all public functions
- Keep functions focused and under 50 lines

### Data Contributions
If you are an SME practitioner and want to contribute anonymized transaction schemas
or additional sample datasets, please open an Issue first to discuss format.

## Development Setup

```bash
git clone https://github.com/Albertsfc/AFIS-Core-Framework.git
cd AFIS-Core-Framework/AFIS
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

## Areas Where Help Is Needed

- Additional ETL connectors (e.g., Xero, Wave CSV formats)
- More robust ML models (Prophet, LSTM) for seasonal businesses
- Localization for Spanish-speaking SME owners
- Docker Compose setup for zero-dependency deployment

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
