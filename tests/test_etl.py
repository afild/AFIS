"""Tests for the ETL ingestion pipeline."""
import pytest
import pandas as pd
from pathlib import Path


def test_sample_data_exists():
    """The synthetic dataset must be present."""
    path = Path(__file__).parent.parent / "data" / "examples" / "sample_sme_transactions.csv"
    assert path.exists(), f"Sample data not found at {path}"


def test_sample_data_schema(sample_df):
    """Sample data must have the required columns."""
    required_columns = {"date", "transaction_id", "amount", "type", "category", "description"}
    assert required_columns.issubset(set(sample_df.columns))


def test_sample_data_row_count(sample_df):
    """Dataset should cover at least 20 months of transactions."""
    sample_df["date"] = pd.to_datetime(sample_df["date"])
    months_covered = sample_df["date"].dt.to_period("M").nunique()
    assert months_covered >= 20, f"Expected 20+ months, got {months_covered}"


def test_transaction_types(sample_df):
    """Only valid transaction types should be present."""
    valid_types = {"revenue", "expense"}
    found_types = set(sample_df["type"].unique())
    assert found_types.issubset(valid_types), f"Invalid types found: {found_types - valid_types}"


def test_amounts_are_positive(sample_df):
    """All amounts must be positive floats."""
    assert (sample_df["amount"] > 0).all(), "Found non-positive amounts"


def test_no_duplicate_transaction_ids(sample_df):
    """Transaction IDs must be unique."""
    assert sample_df["transaction_id"].nunique() == len(sample_df)
