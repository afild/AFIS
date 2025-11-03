"""Shared fixtures for the AFIS test suite."""
import pytest
import pandas as pd
from pathlib import Path


SAMPLE_DATA_PATH = Path(__file__).parent.parent / "data" / "examples" / "sample_sme_transactions.csv"


@pytest.fixture
def sample_df():
    """Load the synthetic SME dataset as a DataFrame."""
    return pd.read_csv(SAMPLE_DATA_PATH)


@pytest.fixture
def minimal_df():
    """Minimal in-memory DataFrame for fast unit tests."""
    data = {
        "date": pd.date_range("2024-01-01", periods=24, freq="ME").strftime("%Y-%m-%d").tolist(),
        "transaction_id": [f"TXN-TEST-{i:03d}" for i in range(24)],
        "amount": [100000.0 + i * 1000 for i in range(12)] + [60000.0 + i * 500 for i in range(12)],
        "type": ["revenue"] * 12 + ["expense"] * 12,
        "category": ["product_sales"] * 12 + ["payroll"] * 12,
        "description": ["Monthly sales"] * 12 + ["Payroll"] * 12,
    }
    return pd.DataFrame(data)
