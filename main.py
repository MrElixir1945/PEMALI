# Central Orchestrator & Fast API
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
import uvicorn

# Asumsi: core/registry.py dan core/base_module.py sudah ada
from core.registry import registry
from core.base_module import ModuleOutput

app = FastAPI(title="PEMALI Communicate Layer", version="1.0")

# --- Schemas ---
class ToolCallRequest(BaseModel):
    tool_name: str
    parameters: Dict[str, Any]

# --- Endpoints ---
@app.get("/tools", response_model=List[Dict[str, Any]])
async def get_available_tools():
    """
    Discovery endpoint. 
    AI Agent hit ini untuk dapetin list manifest (deskripsi tool).
    """
    return registry.get_all_manifests()

@app.post("/execute", response_model=ModuleOutput)
async def execute_agent_tool(request: ToolCallRequest):
    """
    Execution endpoint.
    AI Agent ngirim JSON (tool_name & params) ke mari.
    """
    try:
        # Dispatch request via registry
        result = await registry.execute_tool(request.tool_name, request.parameters)
        return result
    except ValueError as e:
        # Menangani tool yang tidak terdaftar
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Menangani runtime error di dalam modul
        raise HTTPException(status_code=500, detail=f"Module execution failed: {str(e)}")

if __name__ == "__main__":
    # Jalankan server
    print("[System] Starting Communicate Layer...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)