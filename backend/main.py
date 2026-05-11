import logging
import asyncio
import os
import datetime
import json
import uuid
import re
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# Import Core Components
from backend.core.database import SessionLocal, init_db, AuditLog, AgentMemory, AutonomousTask
from backend.core.orchestrator import PemaliOrchestrator
from backend.core.telemetry import telemetry
from backend.core.registry import registry
from backend.core.models import TelemetryEvent, NodeState

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", ".env"))

# Configure Logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI(title="PEMALI V2", version="2.6.0")

# Setup CORS agar frontend (Next.js/Streamlit) bisa akses SSE tanpa hambatan
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inisialisasi DB pada Startup
@app.on_event("startup")
def on_startup():
    init_db()

# Dependency DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Optimasi Concurrency ---
# Membatasi maksimal 10 eksekusi agen bersamaan (Cegah CPU/Token Spike)
MAX_CONCURRENT_TASKS = 10
agent_semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)

# --- Schemas ---
class TriggerRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=500, description="Instruksi untuk agent.")
    session_id: Optional[str] = Field(None, description="ID Sesi jika ingin melanjutkan konteks sebelumnya.")

    @field_validator("prompt")
    @classmethod
    def clean_prompt(cls, v):
        # Buang karakter TUI box/unicode yang mungkin ke-capture dari terminal
        cleaned = re.sub(r'[─│┌┐└┘├┤╭╮╰╯○●◎◉✗◆◇▸▹﹁﹂═║╒╓╔╕╖╗╘╙╚╛╜╝╞╟╠╡╢╣╤╥╦╧╨╩╪╫╬▌▐▀▄█▓▒░]', '', v)
        cleaned = cleaned.strip()
        if len(cleaned) < 3:
            raise ValueError("Prompt tidak valid setelah dibersihkan")
        return cleaned

# --- Background Wrapper ---
async def execute_agent_safely(prompt: str, session_id: str):
    """Bungkus eksekusi dengan antrean semaphore untuk mencegah resource spike."""
    async with agent_semaphore:
        logging.info(f"[Orchestrator] Starting session {session_id} with prompt: {prompt[:50]}...")
        orchestrator = PemaliOrchestrator(session_id)
        try:
            await orchestrator.run(prompt)
        except Exception as e:
            logging.error(f"[Orchestrator] Fatal Error in session {session_id}: {str(e)}")
            await telemetry.emit(TelemetryEvent(
                trace_id=session_id,
                node_id="system",
                node_type="Manager",
                state=NodeState.ERROR,
                narrative=f"Critical Error: {str(e)}"
            ))

# --- Endpoints ---

@app.get("/")
async def root():
    """Health check & Engine identity."""
    return {
        "status": "online",
        "service": "PEMALI Super Agent (Hierarchical DAG)",
        "version": "2.6.0-production",
        "concurrent_slots": MAX_CONCURRENT_TASKS,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

@app.get("/api/tools")
@app.get("/tools") 
async def get_available_tools():
    """Discovery endpoint untuk registrasi tools ke LLM."""
    return registry.get_all_manifests()

@app.post("/api/trigger")
async def trigger_agent(req: TriggerRequest, background_tasks: BackgroundTasks):
    """Memulai siklus audit (Manual Trigger) dengan antrean background."""
    session_id = req.session_id or f"sess-{uuid.uuid4().hex[:16]}"
    
    # Eksekusi dilempar ke background agar endpoint langsung me-return 200 OK
    background_tasks.add_task(execute_agent_safely, req.prompt, session_id)
    
    return {
        "status": "queued",
        "session_id": session_id,
        "message": "Task masuk antrean. Pantau status real-time di /api/telemetry"
    }

@app.get("/api/telemetry")
@app.get("/api/stream") 
async def sse_telemetry(request: Request):
    """
    Endpoint SSE (Server-Sent Events) untuk Dashboard.
    Menyalurkan kognisi AI (thinking, spawning, executing) secara asinkron.
    """
    return StreamingResponse(
        telemetry.subscribe(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Content-Type": "text/event-stream"
        }
    )

@app.get("/api/history/{session_id}")
@app.get("/api/session/{session_id}")
def get_history(session_id: str, db: Session = Depends(get_db)):
    """
    Mengambil riwayat kognitif, chat, dan laporan audit per sesi.
    Optimasi: N+1 Query Fix menggunakan filter langsung.
    """
    memories = db.query(AgentMemory).filter(AgentMemory.session_id == session_id).order_by(AgentMemory.id.asc()).all()
    logs = db.query(AuditLog).filter(AuditLog.session_id == session_id).order_by(AuditLog.created_at.desc()).all()
    
    if not memories and not logs:
        raise HTTPException(status_code=404, detail="Sesi tidak ditemukan")
        
    return {
        "session_id": session_id,
        "audit_logs": logs,
        "agent_memories": memories
    }

@app.get("/api/status")
async def get_system_status(db: Session = Depends(get_db)):
    """Agregasi data untuk Overview Dashboard."""
    try:
        recent_tasks = db.query(AutonomousTask).order_by(AutonomousTask.id.desc()).limit(5).all()
        return {
            "fastapi_active": True,
            "modules_loaded": len(registry.tools),
            "concurrent_tasks_active": MAX_CONCURRENT_TASKS - agent_semaphore._value,
            "recent_tasks": [{"id": t.id, "status": t.status} for t in recent_tasks]
        }
    except Exception as e:
        return {"error": str(e), "fastapi_active": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)