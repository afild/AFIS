import os
import sqlite3
from datetime import datetime

DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "afis_finance.db")
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")

def get_db_connection():
    """Returns a connection to the SQLite database with row factory enabled."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database using the schema.sql file and inserts seed data if empty."""
    is_new = not os.path.exists(DATABASE_PATH)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    with open(SCHEMA_PATH, 'r') as f:
        schema_sql = f.read()
    
    cursor.executescript(schema_sql)
    conn.commit()
    
    # Check if we should insert seed data
    cursor.execute("SELECT COUNT(*) FROM transactions")
    row_count = cursor.fetchone()[0]
    
    if row_count == 0:
        seed_database(conn)
        
    conn.close()

def log_audit(level: str, module: str, message: str, details: str = None, conn=None):
    """Inserts a log entry for NIST AI RMF 1.0 accountability audits."""
    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO audit_logs (level, module, message, details) VALUES (?, ?, ?, ?)",
        (level, module, message, details)
    )
    conn.commit()
    if should_close:
        conn.close()

def seed_database(conn):
    """Seeds the database with 12 months of realistic SME transaction records for testing."""
    cursor = conn.cursor()
    
    # Financial data pattern (June 2025 to May 2026)
    # Reflects the Business Plan baseline: ~$4,166/mo income, ~$1,666/mo expenses
    history = [
        # June 2025
        ("2025-06-05", "income", 5000.0, "Consulting project milestone - Client A", "Revenue"),
        ("2025-06-10", "expense", 1200.0, "Office rent Orlando HQ", "OpEx"),
        ("2025-06-15", "expense", 300.0, "AWS cloud server hosting", "COGS"),
        ("2025-06-20", "expense", 250.0, "Software subscriptions (GitHub, Slack)", "OpEx"),
        
        # July 2025
        ("2025-07-05", "income", 4000.0, "Web consulting - Client B", "Revenue"),
        ("2025-07-10", "expense", 1200.0, "Office rent Orlando HQ", "OpEx"),
        ("2025-07-15", "expense", 320.0, "AWS cloud server hosting", "COGS"),
        ("2025-07-22", "expense", 150.0, "Online marketing ads", "OpEx"),
        
        # August 2025
        ("2025-08-05", "income", 5000.0, "Data analytics integration - Client C", "Revenue"),
        ("2025-08-10", "expense", 1200.0, "Office rent Orlando HQ", "OpEx"),
        ("2025-08-15", "expense", 310.0, "AWS cloud server hosting", "COGS"),
        ("2025-08-25", "expense", 200.0, "Professional insurance", "OpEx"),
        
        # September 2025
        ("2025-09-05", "income", 3500.0, "Retainer services - Client A", "Revenue"),
        ("2025-09-10", "expense", 1200.0, "Office rent Orlando HQ", "OpEx"),
        ("2025-09-15", "expense", 350.0, "AWS cloud server hosting", "COGS"),
        
        # October 2025
        ("2025-10-05", "income", 6000.0, "Dashboard custom implementation - Client D", "Revenue"),
        ("2025-10-10", "expense", 1200.0, "Office rent Orlando HQ", "OpEx"),
        ("2025-10-15", "expense", 410.0, "AWS cloud server hosting", "COGS"),
        ("2025-10-20", "expense", 500.0, "Legal consultation fees", "OpEx"),
        
        # November 2025
        ("2025-11-05", "income", 4000.0, "Retainer services - Client A", "Revenue"),
        ("2025-11-10", "expense", 1200.0, "Office rent Orlando HQ", "OpEx"),
        ("2025-11-15", "expense", 390.0, "AWS cloud server hosting", "COGS"),
        
        # December 2025
        ("2025-12-05", "income", 4500.0, "ETL Pipeline setup - Client E", "Revenue"),
        ("2025-12-10", "expense", 1200.0, "Office rent Orlando HQ", "OpEx"),
        ("2025-12-15", "expense", 420.0, "AWS cloud server hosting", "COGS"),
        ("2025-12-22", "expense", 800.0, "Holiday workshop and marketing", "OpEx"),
        
        # January 2026
        ("2026-01-05", "income", 5000.0, "Retainer services - Client B", "Revenue"),
        ("2026-01-10", "expense", 1200.0, "Office rent Orlando HQ", "OpEx"),
        ("2026-01-15", "expense", 450.0, "AWS cloud server hosting", "COGS"),
        ("2026-01-20", "expense", 250.0, "Software subscriptions (GitHub, Slack)", "OpEx"),
        
        # February 2026
        ("2026-02-05", "income", 5500.0, "BI system migration - Client F", "Revenue"),
        ("2026-02-10", "expense", 1200.0, "Office rent Orlando HQ", "OpEx"),
        ("2026-02-15", "expense", 460.0, "AWS cloud server hosting", "COGS"),
        
        # March 2026
        ("2026-03-05", "income", 4200.0, "Retainer services - Client A", "Revenue"),
        ("2026-03-10", "expense", 1200.0, "Office rent Orlando HQ", "OpEx"),
        ("2026-03-15", "expense", 440.0, "AWS cloud server hosting", "COGS"),
        ("2026-03-25", "expense", 300.0, "Domain renewal and marketing ads", "OpEx"),
        
        # April 2026
        ("2026-04-05", "income", 6500.0, "AI Agent configuration - Client G", "Revenue"),
        ("2026-04-10", "expense", 1200.0, "Office rent Orlando HQ", "OpEx"),
        ("2026-04-15", "expense", 510.0, "AWS cloud server hosting", "COGS"),
        
        # May 2026
        ("2026-05-05", "income", 5000.0, "Retainer services - Client B", "Revenue"),
        ("2026-05-10", "expense", 1200.0, "Office rent Orlando HQ", "OpEx"),
        ("2026-05-15", "expense", 490.0, "AWS cloud server hosting", "COGS"),
        ("2026-05-20", "expense", 180.0, "Local transportation & travel", "OpEx"),
    ]
    
    for date, tx_type, amount, desc, category in history:
        cursor.execute(
            "INSERT INTO transactions (date, type, amount, description, category) VALUES (?, ?, ?, ?, ?)",
            (date, tx_type, amount, desc, category)
        )
    
    conn.commit()
    
    # Log the seeding event for NIST RMF governance audit
    cursor.execute(
        "INSERT INTO audit_logs (level, module, message, details) VALUES (?, ?, ?, ?)",
        ("INFO", "DATABASE", "Database successfully initialized and seeded with 12 months of transactions.", f"Inserted {len(history)} records.")
    )
    conn.commit()
