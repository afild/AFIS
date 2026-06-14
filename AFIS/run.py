import sys
import os
import subprocess
from pathlib import Path

# Load .env if present (optional, no dependency on python-dotenv)
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


def check_dependencies():
    """Simple check to alert users to run pip install if dependencies are missing."""
    try:
        import fastapi
        import uvicorn
        import pandas
        import sklearn
    except ImportError as e:
        print(f"Error: Missing dependencies! ({e.name})")
        print("Please run: pip install -r requirements.txt")
        sys.exit(1)

if __name__ == "__main__":
    # Ensure current directory is on path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # Check dependencies before starting
    check_dependencies()
    
    print("==========================================================")
    print("          AFIS (AI Financial Intelligence System)         ")
    print("==========================================================")
    print(" * Database: SQLite (afis_finance.db)")
    print(" * Ingestion: ETL pipeline with NIST verification")
    print(" * AI Agent: Virtual CFO + NIST AI RMF Audit Logs")
    print(" * ML Model: Cash Flow Ridge Time-Series Forecasting")
    print("----------------------------------------------------------")
    print(" => Web Dashboard URL: http://localhost:8000/static/index.html")
    print("==========================================================")
    
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
