# Sample Data

`sample_sme_transactions.csv` contains 24 months of synthetic financial data
for a fictional U.S. SME (Ridgemont Manufacturing LLC). This data is entirely
fictional and generated for demonstration purposes.

**To use your own data:** export transactions from QuickBooks, Xero, or Wave
as a CSV and ensure it matches the column schema described below.

## Column Schema

| Column | Type | Description |
|--------|------|-------------|
| date | YYYY-MM-DD | Transaction date |
| transaction_id | string | Unique identifier (e.g., TXN-202301-001) |
| amount | float | Transaction amount (always positive) |
| type | string | `revenue` or `expense` |
| category | string | Transaction category |
| description | string | Human-readable description |
