import logging
import asyncio
import os
import sys
import traceback

# Ensure project root is in Python path + load .env SEBELUM import backend modules
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

import datetime
import json
import uuid
import re
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

# Import Core Components
from backend.core.database import SessionLocal, init_db, AuditLog, AgentMemory, AutonomousTask, RawSensorData, ChatSession
from backend.core.orchestrator import PemaliOrchestrator, _sanitize_messages
from backend.core.telemetry import telemetry
from backend.core.registry import registry
from backend.core.models import TelemetryEvent, NodeState, CaseIntent, AskQuestion, TaskCreate, LaporanFilter
from backend.core.memory import query_semantic_scoped
from backend.core.llm_client import get_llm_client, OPENROUTER_MODEL

# Configure Logging
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("PEMALI")

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

# Counter active tasks — gak pake semaphore._value (private API)
_active_tasks = 0
_active_tasks_lock = asyncio.Lock()


async def _acquire_task():
    global _active_tasks
    await agent_semaphore.acquire()
    async with _active_tasks_lock:
        _active_tasks += 1


async def _release_task():
    global _active_tasks
    async with _active_tasks_lock:
        _active_tasks -= 1
    agent_semaphore.release()

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
    logger.info(f"[EXEC] Starting agent execution: session={session_id}, prompt={prompt[:100]}...")

    # Save user prompt + create/update ChatSession
    title = prompt[:30] + "..." if len(prompt) > 30 else prompt
    try:
        db = SessionLocal()
        sess = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
        if not sess:
            db.add(ChatSession(session_id=session_id, title=title))
        else:
            sess.last_activity = datetime.datetime.now(datetime.timezone.utc)
        db.add(AgentMemory(session_id=session_id, role="user", content=prompt))
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"[EXEC] Session save error: {e}")
    finally:
        db.close()

    await _acquire_task()
    try:
        logger.info(f"[EXEC] Semaphore acquired for session {session_id}")
        # Collect telemetry events selama eksekusi buat DAG persistence
        collected_events: list[Dict[str, Any]] = []
        _original_emit = telemetry.emit
        
        async def _collector_emit(event: TelemetryEvent):
            data = event.model_dump(mode='json')
            collected_events.append(data)
            await _original_emit(event)
        
        telemetry.emit = _collector_emit
        try:
            orchestrator = PemaliOrchestrator(session_id)
            logger.info(f"[EXEC] Orchestrator created, calling run()...")
            result = await orchestrator.run(prompt)
            logger.info(f"[EXEC] Agent execution completed for session {session_id}")
        finally:
            telemetry.emit = _original_emit
    finally:
        await _release_task()

        # Save collected telemetry events to DB
        if collected_events:
            try:
                db2 = SessionLocal()
                for ev in collected_events:
                    db2.add(AgentMemory(
                        session_id=session_id,
                        role="telemetry",
                        content=json.dumps(ev, ensure_ascii=False)
                    ))
                db2.commit()
                logger.info(f"[EXEC] Saved {len(collected_events)} telemetry events for session {session_id}")
            except Exception as e:
                db2.rollback()
                logger.error(f"[EXEC] Failed to save telemetry events: {e}")
            finally:
                db2.close()

        # Save assistant response to DB for session history
        try:
            if isinstance(result, str) and len(result) > 10:
                logger.info(f"[EXEC] Saving assistant response to session {session_id}")
                db = SessionLocal()
                try:
                    db.add(AgentMemory(session_id=session_id, role="assistant", content=result))
                    sess = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
                    if sess:
                        sess.last_activity = datetime.datetime.now(datetime.timezone.utc)
                        # Title extraction from AI response
                        first_line = result.strip().split("\n")[0]
                        if first_line.startswith("# "):
                            heading_text = first_line[2:].strip()
                            words = heading_text.split()[:4]
                            ai_title = " ".join(words)[:40]
                            if ai_title and len(ai_title) > 3:
                                sess.title = ai_title
                        else:
                            words = first_line.strip().split()[:4]
                            ai_title = " ".join(words)[:40]
                            if ai_title and len(ai_title) > 3:
                                sess.title = ai_title
                    db.commit()
                except Exception as e:
                    db.rollback()
                    logger.error(f"[EXEC] Failed to save response: {e}")
                finally:
                    db.close()
        except Exception as e:
            logger.critical(f"[EXEC] <<<<< FATAL ERROR: {e} >>>>>")
            logger.critical(f"[EXEC] TRACEBACK:\n{traceback.format_exc()}")
            logger.error(f"[EXEC] Fatal Error in session {session_id}: {str(e)}", exc_info=True)
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
    logger.info("[/] Health check requested")
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

@app.post("/api/stream")
async def trigger_stream(req: TriggerRequest):
    """
    POST SSE — real-time streaming audit.
    Mirip Sismind: generator yield langsung ke StreamingResponse tanpa queue.
    """
    session_id = req.session_id or f"sess-{uuid.uuid4().hex[:16]}"
    logger.info(f"[/api/stream] Streaming audit: session={session_id}")

    async def event_generator():
        yield f"event: state\ndata: {json.dumps({'type': 'connected', 'session_id': session_id})}\n\n"
        try:
            await _acquire_task()
            try:
                orchestrator = PemaliOrchestrator(session_id)
                async for line in orchestrator.run_streaming(req.prompt):
                    yield line
            finally:
                await _release_task()
        except Exception as e:
            logger.error(f"[/api/stream] Error: {e}", exc_info=True)
            yield f"event: state\ndata: {json.dumps({'state': 'ERROR', 'narrative': f'Fatal: {str(e)}', 'node_id': 'system'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Content-Type": "text/event-stream",
        }
    )

@app.post("/api/trigger")
async def trigger_agent(req: TriggerRequest, background_tasks: BackgroundTasks):
    """Memulai siklus audit (Manual Trigger) dengan antrean background."""
    session_id = req.session_id or f"sess-{uuid.uuid4().hex[:16]}"
    logger.info(f"[/api/trigger] Received trigger: session={session_id}, prompt_length={len(req.prompt)}")
    logger.debug(f"[/api/trigger] Prompt: {req.prompt[:200]}...")
    
    # Eksekusi dilempar ke background agar endpoint langsung me-return 200 OK
    background_tasks.add_task(execute_agent_safely, req.prompt, session_id)
    logger.info(f"[/api/trigger] Task queued for session {session_id}")
    
    return {
        "status": "queued",
        "session_id": session_id,
        "message": "Task masuk antrean. Pantau status real-time di /api/telemetry"
    }

@app.get("/api/sessions")
def list_sessions(db: Session = Depends(get_db)):
    """Mengambil daftar semua sesi unik dari tabel ChatSession."""
    results = db.query(ChatSession).order_by(ChatSession.last_activity.desc()).all()
    return [
        {"id": r.session_id, "title": r.title or r.session_id, "last_activity": r.last_activity}
        for r in results
    ]

@app.post("/api/telemetry/publish")
async def publish_telemetry(data: dict):
    """Cross-process: worker kirim event → FastAPI broadcast ke SSE subscribers."""
    try:
        event = TelemetryEvent(**data)
        await telemetry.emit(event)
        return {"status": "published"}
    except Exception as e:
        logger.error(f"[/api/telemetry/publish] Error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/telemetry")
@app.get("/api/stream") 
async def sse_telemetry(request: Request):
    """
    Endpoint SSE (Server-Sent Events) untuk Dashboard.
    Menyalurkan kognisi AI (thinking, spawning, executing) secara asinkron.
    """
    client_id = request.client.host if request.client else "unknown"
    logging.info(f"[SSE] Client connected: {client_id}")
    try:
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
    except Exception as e:
        logging.error(f"[SSE] Endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        logging.info(f"[SSE] Client disconnected: {client_id}")

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
    """Agregasi data untuk Overview Dashboard & Monitor page."""
    logger.debug("[/api/status] Status check requested")
    try:
        recent_tasks = db.query(AutonomousTask).order_by(AutonomousTask.id.desc()).limit(5).all()
        total_reports = db.query(AuditLog).count()
        total_sessions = db.query(ChatSession).count()
        recent_reports_q = (
            db.query(AuditLog)
            .order_by(AuditLog.created_at.desc())
            .limit(10)
            .all()
        )
        def severity_label(p: int) -> str:
            if p >= 8: return "High"
            if p >= 5: return "Medium"
            return "Low"
        result = {
            "fastapi_active": True,
            "modules_loaded": len(registry.tools),
            "concurrent_tasks_active": _active_tasks,
            "total_reports": total_reports,
            "total_sessions": total_sessions,
            "recent_tasks": [{"id": t.id, "status": t.status, "task_type": t.task_type, "priority": t.priority} for t in recent_tasks],
            "recent_reports": [
                {
                    "id": r.id,
                    "location": r.location or r.title or "—",
                    "issue_type": r.issue_type or "environmental_audit",
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "severity": severity_label(r.priority or 5),
                    "time": r.created_at.strftime("%d %b %Y, %H:%M") if r.created_at else "—",
                }
                for r in recent_reports_q
            ],
        }
        logger.debug(f"[/api/status] Returning: modules={len(registry.tools)}, tasks={len(recent_tasks)}, reports={total_reports}")
        return result
    except Exception as e:
        logger.error(f"[/api/status] Error: {e}")
        return {"error": str(e), "fastapi_active": True}


# ═════════════════════════════════════════════════════════════
# SPRINT 5 — Autonomous Tasks API
# ═════════════════════════════════════════════════════════════

@app.get("/api/tasks")
def list_tasks(
    status: Optional[str] = None,
    type: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List autonomous tasks dengan filter opsional."""
    q = db.query(AutonomousTask)
    if status and status.lower() != "all":
        q = q.filter(AutonomousTask.status == status)
    if type and type.lower() != "all":
        q = q.filter(AutonomousTask.task_type == type)
    tasks = q.order_by(
        AutonomousTask.priority.desc(),
        AutonomousTask.execute_at.asc()
    ).limit(min(limit, 200)).all()
    return {
        "total": len(tasks),
        "tasks": [
            {
                "id": t.id,
                "task_type": t.task_type,
                "priority": t.priority,
                "intent_description": t.intent_description,
                "execute_at": t.execute_at.isoformat() if t.execute_at else None,
                "status": t.status,
                "retries": t.retries or 0,
                "last_error": t.last_error,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in tasks
        ]
    }


@app.post("/api/tasks")
def create_task(req: TaskCreate, db: Session = Depends(get_db)):
    """Buat autonomous task baru (dari UI atau API)."""
    execute_at = (
        datetime.datetime.fromisoformat(req.execute_at)
        if req.execute_at
        else datetime.datetime.now(datetime.timezone.utc)
    )
    task = AutonomousTask(
        task_type=req.task_type,
        priority=req.priority,
        execute_at=execute_at,
        intent_description=req.intent_description,
        status="pending",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    logger.info(f"[/api/tasks] Created task #{task.id}: type={task.task_type}, priority={task.priority}")
    return {"status": "created", "task_id": task.id, "execute_at": task.execute_at.isoformat()}


# ═════════════════════════════════════════════════════════════
# SPRINT 5 — Laporan Store API
# ═════════════════════════════════════════════════════════════

@app.get("/api/laporan")
def list_laporan(
    source: Optional[str] = None,
    location: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """List semua laporan audit dengan filter."""
    q = db.query(AuditLog)
    if source and source.lower() != "all":
        q = q.filter(AuditLog.source == source)
    if location:
        q = q.filter(AuditLog.location.ilike(f"%{location}%"))
    reports = q.order_by(AuditLog.created_at.desc()).limit(min(limit, 100)).all()
    return {
        "total": len(reports),
        "reports": [
            {
                "id": r.id,
                "session_id": r.session_id,
                "source": r.source,
                "title": r.title,
                "location": r.location,
                "issue_type": r.issue_type,
                "priority": r.priority,
                "narrative_preview": r.narrative_report[:300] if r.narrative_report else "",
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in reports
        ]
    }


@app.get("/api/laporan/{id}")
def get_laporan(id: int, db: Session = Depends(get_db)):
    """Detail satu laporan audit."""
    report = db.query(AuditLog).filter(AuditLog.id == id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Laporan tidak ditemukan")

    raw_data = db.query(RawSensorData).filter(
        RawSensorData.session_id == report.session_id
    ).all()

    return {
        "id": report.id,
        "session_id": report.session_id,
        "source": report.source,
        "title": report.title,
        "location": report.location,
        "issue_type": report.issue_type,
        "priority": report.priority,
        "narrative_report": report.narrative_report,
        "thk_alignment": report.thk_alignment,
        "metadata": report.metadata_json,
        "raw_sensor_data": [
            {
                "id": r.id,
                "agent_name": r.agent_name,
                "tool_name": r.tool_name,
                "raw_payload": r.raw_payload,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in raw_data
        ],
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }


@app.post("/api/laporan/{id}/ask")
async def ask_laporan(id: int, req: AskQuestion, db: Session = Depends(get_db)):
    """AiBubble Q&A — scoped RAG per laporan."""
    report = db.query(AuditLog).filter(AuditLog.id == id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Laporan tidak ditemukan")

    # Scoped RAG — hanya search di session laporan ini
    chunks = await asyncio.to_thread(
        query_semantic_scoped, req.question, report.session_id, 3
    )

    # Ambil raw sensor data sesi ini
    raw_data = db.query(RawSensorData).filter(
        RawSensorData.session_id == report.session_id
    ).limit(10).all()

    # Build context untuk LLM
    context_parts = []
    if report.narrative_report:
        context_parts.append(f"=== LAPORAN AUDIT ===\n{report.narrative_report}")
    if raw_data:
        context_parts.append("=== DATA SENSOR MENTAH ===")
        for rd in raw_data:
            context_parts.append(
                f"[{rd.agent_name or rd.tool_name}]: "
                f"{json.dumps(rd.raw_payload, default=str, ensure_ascii=False)[:1000]}"
            )
    if chunks:
        context_parts.append("=== KONTEKS TERKAIT (RAG) ===")
        for c in chunks:
            context_parts.append(c["content"][:500])

    context_text = "\n\n".join(context_parts)
    if len(context_text) > 8000:
        context_text = context_text[:8000] + "\n\n... (dipotong)"

    # LLM generate answer
    try:
        llm = get_llm_client()
        messages = [
            {
                "role": "system",
                "content": (
                    "Kamu adalah asisten laporan audit lingkungan PEMALI untuk Bali.\n"
                    "Jawab pertanyaan user berdasarkan data laporan berikut.\n"
                    "Jawab dalam bahasa Indonesia, singkat dan jelas.\n"
                    "Jika data tidak cukup untuk menjawab, katakan dengan jujur.\n"
                    "Jangan mengarang data yang tidak ada di laporan."
                )
            },
            {
                "role": "user",
                "content": (
                    f"DATA LAPORAN:\n{context_text}\n\n"
                    f"PERTANYAAN USER: {req.question}"
                )
            },
        ]
        res = await llm.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=_sanitize_messages(messages),
            max_tokens=2048,
            timeout=30.0,
        )
        answer = res.choices[0].message.content or "Maaf, tidak bisa menjawab pertanyaan ini."
    except Exception as e:
        logger.error(f"[/api/laporan/{id}/ask] LLM error: {e}")
        answer = f"Maaf, terjadi kesalahan saat mencari jawaban: {str(e)[:100]}"

    return {
        "question": req.question,
        "answer": answer,
        "sources": len(chunks),
        "session_id": report.session_id,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)