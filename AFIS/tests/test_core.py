import os
import sys
import unittest
import sqlite3

# Ensure app is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.db_manager import init_db, get_db_connection, DATABASE_PATH
from app.etl.ingestor import ETLIngestor
from app.forecasting.model import CashFlowForecaster
from app.ai_agent.analyst import AIFinancialAnalyst

class TestAFISCore(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Initializes database schema before testing."""
        init_db()

    def test_database_connection(self):
        """Verifies database connection and schema initialization."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Test transactions table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transactions'")
        self.assertIsNotNone(cursor.fetchone())
        
        # Test forecasts table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='forecasts'")
        self.assertIsNotNone(cursor.fetchone())
        
        # Test compliance_logs table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='compliance_logs'")
        self.assertIsNotNone(cursor.fetchone())
        
        conn.close()

    def test_etl_validation_dates(self):
        """Verifies the ETL date validator logic."""
        self.assertTrue(ETLIngestor.validate_date("2026-06-08"))
        self.assertFalse(ETLIngestor.validate_date("06-08-2026"))
        self.assertFalse(ETLIngestor.validate_date("2026/06/08"))
        self.assertFalse(ETLIngestor.validate_date("invalid-date"))

    def test_etl_csv_ingestion(self):
        """Tests ingestion of valid financial rows, duplicate detection, and anomaly logging."""
        csv_data = (
            "Date,Type,Amount,Category,Description\n"
            "2026-06-01,income,4500.00,Revenue,Project milestone A\n"
            "2026-06-02,expense,120.00,Software,Cloud subscription\n"
            "2026-06-02,expense,120.00,Software,Cloud subscription\n" # Duplicate row
            "2026-06-03,expense,50000.00,Hardware,Anomaly buy new servers\n" # Anomaly row (outlier)
        )
        
        summary = ETLIngestor.ingest_csv(csv_data)
        
        self.assertEqual(summary["inserted"], 3) # Income, Expense 1, Expense 2 (anomaly is still inserted but logged)
        self.assertEqual(summary["duplicates"], 1) # Expense 1 duplicate skipped
        self.assertEqual(summary["anomalies"], 1) # $50,000 expense is an anomaly

    def test_ml_forecasting(self):
        """Checks if Ridge regression training produces 12-month projections."""
        predictions = CashFlowForecaster.train_and_forecast()
        
        # Verify 12 months forecasted
        self.assertEqual(len(predictions), 12)
        
        # Verify predictions have expected keys
        first_pred = predictions[0]
        self.assertIn("month", first_pred)
        self.assertIn("income", first_pred)
        self.assertIn("expense", first_pred)
        self.assertIn("net", first_pred)
        self.assertTrue(first_pred["lower_bound"] <= first_pred["upper_bound"])

    def test_ai_agent_kpis(self):
        """Tests that CFO AI calculation models evaluate runway and margins properly."""
        kpis = AIFinancialAnalyst.calculate_kpis()
        
        self.assertIn("current_cash", kpis)
        self.assertIn("burn_rate", kpis)
        self.assertIn("runway", kpis)
        self.assertIn("net_margin_percent", kpis)
        
        self.assertGreaterEqual(kpis["current_cash"], 0.0)

    def test_ai_agent_query(self):
        """Tests the natural language parser routes answers to key words correctly."""
        resp1 = AIFinancialAnalyst.answer_query("how is my cash health and runway?")
        self.assertIn("Runway", resp1)
        self.assertIn("CFO Agent", resp1)
        
        resp2 = AIFinancialAnalyst.answer_query("what is the ML forecast?")
        self.assertIn("forecast", resp2)
        self.assertIn("Ridge Regression", resp2)
        
        resp3 = AIFinancialAnalyst.answer_query("give me expense advice")
        self.assertIn("AWS", resp3)
        self.assertIn("Office rent", resp3)

if __name__ == "__main__":
    unittest.main()
