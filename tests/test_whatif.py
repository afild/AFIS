"""
HARNESS: What-If Scenario Simulator Tests
==========================================
Valida que:
1. whatif_forecast() responde em < 500ms (benchmark de performance)
2. income_delta_pct=-20 resulta em receita ~20% menor
3. expense_delta_pct=+30 resulta em despesas ~30% maiores
4. Deltas zerados produzem resultado idêntico ao forecast base
5. A API endpoint /api/forecast/whatif responde corretamente

Alinhado com HARNESS.md §5 (Performance < 500ms).
"""

import time
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Unit Tests — CashFlowForecaster.whatif_forecast()
# ---------------------------------------------------------------------------

class TestWhatIfForecastUnit:

    @pytest.fixture(autouse=True)
    def setup_base_forecast(self, tmp_path):
        """Seeds a temporary DB with base forecast data for testing."""
        import sqlite3
        db_path = str(tmp_path / "test_whatif.db")
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE forecasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                predicted_income REAL NOT NULL,
                predicted_expense REAL NOT NULL,
                confidence_lower REAL NOT NULL,
                confidence_upper REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                level TEXT NOT NULL,
                module TEXT NOT NULL,
                message TEXT NOT NULL,
                details TEXT
            )
        """)
        # Insert 12 months of sample forecast data
        for i in range(1, 13):
            month = f"2026-{i:02d}"
            conn.execute(
                "INSERT INTO forecasts (date, predicted_income, predicted_expense, confidence_lower, confidence_upper) VALUES (?,?,?,?,?)",
                (month, 5000.0, 1800.0, 1500.0, 3800.0)
            )
        conn.commit()
        conn.close()
        self.db_path = db_path
        self.base_income = 5000.0
        self.base_expense = 1800.0

    def _run_whatif(self, income_delta, expense_delta):
        from app.forecasting.model import CashFlowForecaster
        with patch("app.forecasting.model.get_db_connection") as mock_conn_fn, \
             patch("app.forecasting.model.log_audit"):
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            mock_conn_fn.return_value = conn
            return CashFlowForecaster.whatif_forecast(income_delta, expense_delta)

    def test_performance_under_500ms(self):
        """Scenario simulation must complete in under 500ms (HARNESS.md §5)."""
        start = time.perf_counter()
        results = self._run_whatif(0.0, 0.0)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 500, f"whatif_forecast() took {elapsed_ms:.1f}ms — must be < 500ms"

    def test_zero_deltas_match_base(self):
        """With 0% deltas, results must equal the base forecast."""
        results = self._run_whatif(0.0, 0.0)
        assert len(results) == 12
        for r in results:
            assert abs(r["income"] - self.base_income) < 0.01, "Income must equal base at 0% delta"
            assert abs(r["expense"] - self.base_expense) < 0.01, "Expense must equal base at 0% delta"

    def test_income_drop_20_percent(self):
        """A -20% income delta must reduce projected income by approximately 20%."""
        results = self._run_whatif(-20.0, 0.0)
        expected_income = self.base_income * 0.80
        for r in results:
            assert abs(r["income"] - expected_income) < 1.0, (
                f"Expected income ~${expected_income:.2f}, got ${r['income']:.2f}"
            )
            # Expenses should be unchanged
            assert abs(r["expense"] - self.base_expense) < 0.01

    def test_expense_increase_30_percent(self):
        """A +30% expense delta must increase projected expenses by approximately 30%."""
        results = self._run_whatif(0.0, 30.0)
        expected_expense = self.base_expense * 1.30
        for r in results:
            assert abs(r["expense"] - expected_expense) < 1.0, (
                f"Expected expense ~${expected_expense:.2f}, got ${r['expense']:.2f}"
            )

    def test_combined_scenario_net_calculation(self):
        """Net = income - expense must be calculated correctly for combined deltas."""
        results = self._run_whatif(-20.0, +10.0)
        for r in results:
            expected_income = self.base_income * 0.80
            expected_expense = self.base_expense * 1.10
            expected_net = expected_income - expected_expense
            assert abs(r["net"] - expected_net) < 1.0, (
                f"Net mismatch: expected ${expected_net:.2f}, got ${r['net']:.2f}"
            )

    def test_income_never_negative(self):
        """Even at extreme negative deltas, income must not go below 0."""
        results = self._run_whatif(-100.0, 0.0)
        for r in results:
            assert r["income"] >= 0.0, f"Income went negative: ${r['income']}"

    def test_returns_12_months(self):
        """whatif_forecast() must always return exactly 12 monthly projections."""
        results = self._run_whatif(10.0, -5.0)
        assert len(results) == 12, f"Expected 12 months, got {len(results)}"

    def test_result_contains_required_keys(self):
        """Each result dict must contain all required fields."""
        results = self._run_whatif(0.0, 0.0)
        required_keys = {"month", "income", "expense", "net", "lower_bound", "upper_bound",
                         "income_delta_pct", "expense_delta_pct"}
        for r in results:
            missing = required_keys - set(r.keys())
            assert not missing, f"Result missing keys: {missing}"


# ---------------------------------------------------------------------------
# API Endpoint Tests — POST /api/forecast/whatif
# ---------------------------------------------------------------------------

class TestWhatIfEndpoint:

    def test_whatif_endpoint_success(self):
        """The /api/forecast/whatif endpoint must return 200 with scenario data."""
        from fastapi.testclient import TestClient
        from unittest.mock import patch

        mock_results = [
            {"month": f"2026-{i:02d}", "income": 4000.0, "expense": 1800.0,
             "net": 2200.0, "lower_bound": 1000.0, "upper_bound": 3400.0,
             "income_delta_pct": -20.0, "expense_delta_pct": 0.0}
            for i in range(1, 13)
        ]

        with patch("app.forecasting.model.CashFlowForecaster.whatif_forecast", return_value=mock_results), \
             patch("app.database.db_manager.init_db"):
            from app.main import app
            client = TestClient(app)
            res = client.post("/api/forecast/whatif", json={"income_delta_pct": -20.0, "expense_delta_pct": 0.0})

        assert res.status_code == 200
        body = res.json()
        assert "scenario" in body
        assert body["income_delta_pct"] == -20.0
        assert len(body["scenario"]) == 12

    def test_whatif_endpoint_default_params(self):
        """Endpoint must accept empty body (default 0% deltas)."""
        from fastapi.testclient import TestClient

        mock_results = [
            {"month": f"2026-{i:02d}", "income": 5000.0, "expense": 1800.0,
             "net": 3200.0, "lower_bound": 2000.0, "upper_bound": 4400.0,
             "income_delta_pct": 0.0, "expense_delta_pct": 0.0}
            for i in range(1, 13)
        ]

        with patch("app.forecasting.model.CashFlowForecaster.whatif_forecast", return_value=mock_results), \
             patch("app.database.db_manager.init_db"):
            from app.main import app
            client = TestClient(app)
            res = client.post("/api/forecast/whatif", json={})

        assert res.status_code == 200
        assert res.json()["income_delta_pct"] == 0.0
        assert res.json()["expense_delta_pct"] == 0.0
