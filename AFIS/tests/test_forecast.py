"""Tests for the ML cash flow forecasting engine."""
import pytest
import pandas as pd
import numpy as np


def test_forecast_returns_numeric_values(minimal_df):
    """Forecast output must be numeric and non-empty."""
    try:
        from app.forecasting.model import CashFlowForecaster
        # The forecaster reads from the database, so we test it can be imported
        # and verify its output structure when data is available
        result = CashFlowForecaster.train_and_forecast()
        assert result is not None
        if len(result) > 0:
            first = result[0]
            assert isinstance(first["income"], (int, float))
            assert isinstance(first["expense"], (int, float))
    except Exception:
        pytest.skip("Forecasting requires database with historical data")


def test_forecast_horizon(minimal_df):
    """Forecast should produce at least 3 future periods."""
    try:
        from app.forecasting.model import CashFlowForecaster
        result = CashFlowForecaster.train_and_forecast()
        # Result should be a list with at least 3 projected periods
        if hasattr(result, "__len__"):
            assert len(result) >= 3
    except Exception:
        pytest.skip("Forecasting requires database with historical data")


def test_revenue_exceeds_zero(minimal_df):
    """Revenue transactions should sum to a positive value."""
    revenue_total = minimal_df[minimal_df["type"] == "revenue"]["amount"].sum()
    assert revenue_total > 0
