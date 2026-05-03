# Central Orchestrator & Fast API
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, Any, List
import uvicorn
import datetime
import json
import asyncio

# Asumsi: core/registry.py dan core/base_module.py sudah ada
from core.registry import registry
from core.base_module import ModuleOutput
from core.database import SessionLocal, AutonomousTask, AgentMemory, AuditLog
from core.orchestrator import PemaliOrchestrator

app = FastAPI(title="PEMALI Communicate Layer", version="1.0")

# Mount static folder
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- Schemas ---
class ToolCallRequest(BaseModel):
    tool_name: str
    parameters: Dict[str, Any]

class TriggerRequest(BaseModel):
    prompt: str

# --- Endpoints ---
@app.get("/")
async def serve_frontend():
    return FileResponse("static/index.html")

@app.get("/tools", response_model=List[Dict[str, Any]])
async def get_available_tools():
    """Discovery endpoint for LLM context."""
    return registry.get_all_manifests()

@app.post("/execute", response_model=ModuleOutput)
async def execute_agent_tool(request: ToolCallRequest):
    """Execution endpoint for Agent tool calls."""
    try:
        result = await registry.execute_tool(request.tool_name, request.parameters)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Module execution failed: {str(e)}")

# --- New Frontend API Endpoints ---
@app.get("/api/status")
async def get_system_status():
    """Returns data for the left panel (Context)"""
    db = SessionLocal()
    
    # Check worker status via AutonomousTask heartbeat
    latest_task = db.query(AutonomousTask).order_by(AutonomousTask.id.desc()).first()
    worker_active = False
    if latest_task and latest_task.status in ["running", "completed", "pending"]:
        worker_active = True
        
    tasks = db.query(AutonomousTask).order_by(AutonomousTask.id.desc()).limit(5).all()
    queue = [{"id": t.id, "intent": t.intent_description, "status": t.status} for t in tasks]
    
    db.close()
    
    return {
        "fastapi_active": True,
        "worker_active": worker_active,
        "modules": registry.get_all_manifests(),
        "tasks": queue
    }

@app.get("/api/session")
async def get_session_data():
    """Returns data for the right panel (Interaction)"""
    db = SessionLocal()
    
    # 1. Fetch Latest Session ID
    latest_mem = db.query(AgentMemory).order_by(AgentMemory.id.desc()).first()
    target_session = latest_mem.session_id if latest_mem else None
    
    if not target_session:
        db.close()
        return {"session_id": None}
        
    memories = db.query(AgentMemory).filter(AgentMemory.session_id == target_session).order_by(AgentMemory.id.asc()).all()
    mem_list = [{"id": m.id, "role": m.role, "content": m.content, "name": m.name} for m in memories]
    
    # Check if audit exists for this session indirectly (just taking the latest for now)
    latest_log = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
    audit_data = None
    if latest_log:
        audit_data = {
            "id": latest_log.id,
            "location": latest_log.location,
            "issue": latest_log.issue_type,
            "narrative": latest_log.narrative_report,
            "thk": latest_log.thk_alignment
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
            
    db.close()
    
    return {
        "session_id": target_session,
        "memories": mem_list,
        "audit_log": audit_data,
        "satellite_img": img_url
    }

def run_agent_in_background(prompt: str):
    session_id = f"audit-web-{int(datetime.datetime.now().timestamp())}"
    agent = PemaliOrchestrator(session_id=session_id)
    # create new loop for the background task thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(agent.run(prompt))
    finally:
        loop.close()

@app.post("/api/trigger")
async def trigger_agent(req: TriggerRequest, bg_tasks: BackgroundTasks):
    """Trigger agent logic asynchronously"""
    bg_tasks.add_task(run_agent_in_background, req.prompt)
    return {"status": "started"}

if __name__ == "__main__":
    print("[System] Starting Communicate Layer...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)