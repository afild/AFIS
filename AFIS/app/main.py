import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.database.db_manager import init_db, get_db_connection, log_audit
from app.etl.ingestor import ETLIngestor
from app.forecasting.model import CashFlowForecaster
from app.ai_agent.analyst import AIFinancialAnalyst

app = FastAPI(title="AFIS Core Framework API", version="0.2.0")

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
        "version": "0.2.0"
    }

# Mount Frontend static files
frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")
else:
    # Fail-safe print for initialization
    print(f"Warning: Frontend directory not found at {frontend_path}")
