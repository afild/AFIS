import csv
import io
import re
from datetime import datetime
from app.database.db_manager import get_db_connection, log_audit

class ETLIngestor:
    """
    Automated Financial ETL Ingestor with built-in validation, 
    duplicate detection, anomaly checking, and NIST governance audit logging.
    """
    
    @staticmethod
    def validate_date(date_str: str) -> bool:
        """Validates format YYYY-MM-DD."""
        if not date_str or not isinstance(date_str, str):
            return False
        return bool(re.match(r'^\d{4}-\d{2}-\d{2}$', date_str))

    @staticmethod
    def check_duplicate(cursor, date: str, tx_type: str, amount: float, category: str) -> bool:
        """Checks if a transaction with identical signature already exists in the DB."""
        cursor.execute(
            "SELECT COUNT(*) FROM transactions WHERE date = ? AND type = ? AND amount = ? AND category = ?",
            (date, tx_type, amount, category)
        )
        return cursor.fetchone()[0] > 0

    @classmethod
    def ingest_csv(cls, csv_content: str) -> dict:
        """
        Parses, validates, and ingests financial records from a CSV string.
        CSV Columns: Date, Type, Amount, Category, Description
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        records_processed = 0
        records_inserted = 0
        records_rejected = 0
        duplicates_found = 0
        anomalies_detected = 0
        
        log_audit("INFO", "ETL", "Started financial CSV ingestion pipeline.", conn=conn)
        
        # Parse CSV
        f = io.StringIO(csv_content.strip())
        reader = csv.DictReader(f)
        
        # In case headers are lowercase or have spaces, normalize keys
        fieldnames = [field.strip().lower() for field in (reader.fieldnames or [])]
        
        # Calculate historical average transaction size for anomaly detection (outliers)
        cursor.execute("SELECT AVG(amount) FROM transactions")
        avg_amount_row = cursor.fetchone()
        avg_historical_amount = avg_amount_row[0] if avg_amount_row and avg_amount_row[0] else 1000.0
        
        row_num = 1
        for row in reader:
            row_num += 1
            # Normalize row keys
            normalized_row = {k.strip().lower(): v for k, v in row.items() if k}
            
            date = normalized_row.get("date", "").strip()
            tx_type = normalized_row.get("type", "").strip().lower()
            amount_str = normalized_row.get("amount", "").strip()
            category = normalized_row.get("category", "").strip()
            description = normalized_row.get("description", "").strip()
            
            # 1. Basic format validations
            if not cls.validate_date(date):
                log_audit("WARNING", "ETL", f"Line {row_num} rejected: Invalid date format '{date}'. Expected YYYY-MM-DD.", conn=conn)
                records_rejected += 1
                continue
                
            if tx_type not in ["income", "expense"]:
                log_audit("WARNING", "ETL", f"Line {row_num} rejected: Invalid transaction type '{tx_type}'. Expected 'income' or 'expense'.", conn=conn)
                records_rejected += 1
                continue
                
            try:
                amount = float(amount_str)
                if amount < 0:
                    raise ValueError("Negative value")
            except ValueError:
                log_audit("WARNING", "ETL", f"Line {row_num} rejected: Invalid amount '{amount_str}'. Must be a non-negative number.", conn=conn)
                records_rejected += 1
                continue
                
            # 2. Duplicate Detection (preventing double booking)
            if cls.check_duplicate(cursor, date, tx_type, amount, category):
                duplicates_found += 1
                log_audit("INFO", "ETL", f"Line {row_num} skipped: Duplicate transaction detected.", f"Date: {date}, Category: {category}, Amount: {amount}", conn=conn)
                continue
                
            # 3. Anomaly / Outlier Checking (NIST AI RMF Reliability & Safety)
            # Flag transaction if it is 10x larger than typical transactions
            if amount > (avg_historical_amount * 10):
                anomalies_detected += 1
                log_audit(
                    "WARNING", 
                    "ETL", 
                    f"Anomaly flagged at line {row_num}: Highly unusual transaction amount ${amount:.2f}.",
                    f"Value is {amount/avg_historical_amount:.1f}x higher than historical average of ${avg_historical_amount:.2f}. Category: {category}.",
                    conn=conn
                )
            
            # 4. Insert into database
            cursor.execute(
                "INSERT INTO transactions (date, type, amount, category, description) VALUES (?, ?, ?, ?, ?)",
                (date, tx_type, amount, category, description)
            )
            records_inserted += 1
            records_processed += 1
            
        conn.commit()
        conn.close()
        
        result_summary = {
            "processed": records_processed,
            "inserted": records_inserted,
            "rejected": records_rejected,
            "duplicates": duplicates_found,
            "anomalies": anomalies_detected
        }
        
        log_audit(
            "INFO", 
            "ETL", 
            "CSV ingestion pipeline completed successfully.",
            f"Summary: Processed={records_processed}, Inserted={records_inserted}, Rejected={records_rejected}, Duplicates={duplicates_found}, Anomalies={anomalies_detected}"
        )
        
        return result_summary
