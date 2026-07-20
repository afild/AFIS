import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.database.db_manager import init_db, get_db_connection, log_audit
from app.etl.ingestor import ETLIngestor
from app.forecasting.model import CashFlowForecaster
from app.ai_agent.analyst import AIFinancialAnalyst

app = FastAPI(title="AFIS Core Framework API", version="1.0.0")

# Enable CORS for local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize SQLite database and tables
init_db()

# Request model for chat endpoint
class ChatRequest(BaseModel):
    message: str

# Request model for What-If scenario simulator
class WhatIfRequest(BaseModel):
    income_delta_pct: float = 0.0   # e.g. -20.0 = "revenue drops 20%"
    expense_delta_pct: float = 0.0  # e.g. +10.0 = "expenses rise 10%"

@app.get("/api/kpis")
def get_kpis():
    """Retrieve financial performance indicators."""
    try:
        return AIFinancialAnalyst.calculate_kpis()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/transactions")
def get_transactions():
    """Retrieve list of historical transactions."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM transactions ORDER BY date DESC LIMIT 100")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ingest")
async def ingest_csv(file: UploadFile = File(...)):
    """Upload CSV ledger file and trigger automated ETL pipeline."""
    try:
        content = await file.read()
        csv_text = content.decode("utf-8")
        
        # Run ETL
        summary = ETLIngestor.ingest_csv(csv_text)
        
        # Re-train forecasting model with new data
        CashFlowForecaster.train_and_forecast()
        
        return {
            "status": "success",
            "message": "ETL ingestion and model retraining completed.",
            "summary": summary
        }
    except Exception as e:
        log_audit("ERROR", "ETL", f"Ingestion endpoint failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/forecast")
def get_forecast():
    """Trigger ML modeling and return 12-month projections."""
    try:
        forecasts = CashFlowForecaster.train_and_forecast()
        return forecasts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/forecast/whatif")
def get_whatif_forecast(payload: WhatIfRequest):
    """Epic 5: What-If Scenario Simulator. Applies revenue/expense deltas to base forecast."""
    try:
        results = CashFlowForecaster.whatif_forecast(
            income_delta_pct=payload.income_delta_pct,
            expense_delta_pct=payload.expense_delta_pct
        )
        return {"scenario": results, "income_delta_pct": payload.income_delta_pct, "expense_delta_pct": payload.expense_delta_pct}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
def chat_with_analyst(payload: ChatRequest):
    """Chat with the AI Financial Analyst virtual CFO."""
    try:
        response_text = AIFinancialAnalyst.answer_query(payload.message)
        return {"response": response_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/nist-audit")
def get_nist_audit():
    """Retrieve the NIST AI RMF 1.0 audit parameters and metrics."""
    try:
        checklist = AIFinancialAnalyst.get_nist_rmf_checklist()
        
        # Fetch latest logs
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 10")
        logs = cursor.fetchall()
        conn.close()
        
        return {
            "checklist": checklist,
            "recent_logs": [dict(log) for log in logs]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/system/status")
def system_status():
    """Returns the current system status, AI mode, and version."""
    from app.llm_client import get_mode
    return {
        "status": "running",
        "ai_mode": get_mode(),
        "version": "1.0.0"
    }

@app.get("/api/system/health")
def system_health():
    """Extended health check: returns AI mode, cache stats, and version."""
    from app.llm_client import get_mode
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM llm_cache")
        cache_total = cursor.fetchone()[0]
        cursor.execute(
            "SELECT COUNT(*) FROM llm_cache WHERE (julianday('now') - julianday(created_at)) * 86400 < 86400"
        )
        cache_active = cursor.fetchone()[0]
        cursor.execute("SELECT COALESCE(SUM(tokens_used), 0) FROM llm_cache")
        total_tokens = cursor.fetchone()[0]
        conn.close()
    except Exception:
        cache_total = cache_active = total_tokens = 0

    return {
        "status": "running",
        "ai_mode": get_mode(),
        "version": "1.0.0",
        "llm_cache": {
            "total_entries": cache_total,
            "active_entries_24h": cache_active,
            "total_tokens_saved": total_tokens
        }
    }

# Mount Frontend static files
frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")
else:
    # Fail-safe print for initialization
    print(f"Warning: Frontend directory not found at {frontend_path}")
