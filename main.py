# Central Orchestrator & Fast API
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, List
import uvicorn
import datetime
import json
import asyncio
import os

from core.registry import registry
from core.base_module import ModuleOutput
from core.database import SessionLocal, AutonomousTask, AgentMemory, AuditLog
from core.orchestrator import PemaliOrchestrator

app = FastAPI(title="PEMALI Communicate Layer", version="1.2")

# --- Schemas ---
class ToolCallRequest(BaseModel):
    tool_name: str
    parameters: Dict[str, Any]
    session_id: Optional[str] = None

class TriggerRequest(BaseModel):
    prompt: str

# --- Endpoints ---
@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "online",
        "service": "PEMALI Communicate Layer",
        "timestamp": datetime.datetime.now().isoformat()
    }

@app.get("/api/tools", response_model=List[Dict[str, Any]])
@app.get("/tools", response_model=List[Dict[str, Any]]) # Backward compatibility
async def get_available_tools():
    """Discovery endpoint for LLM context."""
    return registry.get_all_manifests()

@app.post("/api/execute", response_model=ModuleOutput)
@app.post("/execute", response_model=ModuleOutput) # Backward compatibility
async def execute_agent_tool(request: ToolCallRequest):
    """Execution endpoint for Agent tool calls."""
    try:
        result = await registry.execute_tool(
            request.tool_name, 
            request.parameters, 
            session_id=request.session_id
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Module execution failed: {str(e)}")

# --- New Frontend API Endpoints ---
@app.get("/api/status")
async def get_system_status():
    """Returns data for the system status."""
    db = None
    try:
        db = SessionLocal()
        if not db:
            return {"fastapi_active": True, "worker_active": False, "tasks": [], "error": "Database session failed"}
            
        # Check worker status via AutonomousTask heartbeat
        latest_task = db.query(AutonomousTask).order_by(AutonomousTask.id.desc()).first()
        worker_active = False
        if latest_task and latest_task.status in ["running", "completed", "pending"]:
            worker_active = True
            
        tasks = db.query(AutonomousTask).order_by(AutonomousTask.id.desc()).limit(5).all()
        queue = [{"id": t.id, "intent": t.intent_description, "status": t.status} for t in tasks]
        
        # Fetch Recent Audits
        recent_audits = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(10).all()
        audits_list = []
        for a in recent_audits:
            # Ambil pesan pertama user untuk judul history
            first_msg = db.query(AgentMemory).filter(
                AgentMemory.session_id == a.session_id,
                AgentMemory.role == "user"
            ).order_by(AgentMemory.created_at.asc()).first()
            
            title = first_msg.content[:40] + "..." if first_msg and len(first_msg.content) > 40 else (first_msg.content if first_msg else a.issue_type)

            audits_list.append({
                "id": a.id, 
                "location": a.location, 
                "issue": title, 
                "thk": a.thk_alignment,
                "timestamp": a.created_at.isoformat()
            })
        
        return {
            "fastapi_active": True,
            "worker_active": worker_active,
            "modules": registry.get_all_manifests(),
            "tasks": queue,
            "recent_audits": audits_list
        }
    except Exception as e:
        print(f"[API] Status Error: {e}")
        return {
            "fastapi_active": True,
            "worker_active": False,
            "modules": registry.get_all_manifests(),
            "tasks": [],
            "recent_audits": [],
            "error": str(e)
        }
    finally:
        if db:
            db.close()

@app.get("/api/session")
async def get_session_data(session_id: Optional[str] = None):
    """Returns data for the interaction history."""
    db = None
    try:
        db = SessionLocal()
        if not db:
            return {"session_id": None, "error": "Database session failed"}
            
        # 1. Determine Target Session
        if session_id:
            target_session = session_id
        else:
            latest_mem = db.query(AgentMemory).order_by(AgentMemory.id.desc()).first()
            target_session = latest_mem.session_id if latest_mem else None
        
        if not target_session:
            return {"session_id": None}
            
        memories = db.query(AgentMemory).filter(AgentMemory.session_id == target_session).order_by(AgentMemory.id.asc()).all()
        mem_list = [{"id": m.id, "role": m.role, "content": m.content, "name": m.name} for m in memories]
        
        # Check if audit exists for this session
        latest_log = db.query(AuditLog).filter(AuditLog.session_id == target_session).first()
        # Fallback to latest if not found and it's the latest session (optional, but safer)
        if not latest_log and not session_id:
             latest_log = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
        audit_data = None
        if latest_log:
            # Simulate NDVI scores for the UI
            audit_data = {
                "id": latest_log.id,
                "location": latest_log.location,
                "issue": latest_log.issue_type,
                "narrative": latest_log.narrative_report,
                "thk": latest_log.thk_alignment,
                "ndvi_score": 0.42,
                "ndvi_change": -12.5
            }
            
        # Get satellite image if available
        tool_mems = db.query(AgentMemory).filter(AgentMemory.session_id == target_session, AgentMemory.name == "satellite_intelligence").order_by(AgentMemory.id.desc()).first()
        img_url = None
        if tool_mems and tool_mems.content:
            try:
                data = json.loads(tool_mems.content)
                img_url = data.get("data", {}).get("image_url")
            except:
                pass
                
        return {
            "session_id": target_session,
            "memories": mem_list,
            "audit_log": audit_data,
            "satellite_img": img_url
        }
    except Exception as e:
        print(f"[API] Session Error: {e}")
        return {"session_id": None, "error": str(e)}
    finally:
        if db:
            db.close()

async def run_agent_in_background(prompt: str):
    session_id = f"audit-web-{int(datetime.datetime.now().timestamp())}"
    agent = PemaliOrchestrator(session_id=session_id)
    try:
        await agent.run(prompt)
    except Exception as e:
        print(f"[Background Agent] Error: {e}")

@app.post("/api/trigger")
async def trigger_agent(req: TriggerRequest, bg_tasks: BackgroundTasks):
    """Trigger agent logic asynchronously"""
    bg_tasks.add_task(run_agent_in_background, req.prompt)
    return {"status": "started"}

if __name__ == "__main__":
    print("[System] Starting Communicate Layer...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)