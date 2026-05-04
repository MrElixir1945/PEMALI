from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import uvicorn

# Memastikan integrasi dengan core V2
from core.registry import registry
from core.base_module import ModuleOutput

app = FastAPI(
    title="PEMALI Communicate Layer", 
    version="2.0",
    description="V2 Standard: Pydantic Validation & Context Injection Bridge"
)

# --- Schemas ---
class ToolCallRequest(BaseModel):
    session_id: str = "default_session"
    tool_name: str
    parameters: Dict[str, Any]

# --- Endpoints ---
@app.get("/tools", response_model=List[Dict[str, Any]])
async def get_available_tools():
    """
    Discovery endpoint. 
    Mengembalikan manifest lengkap (JSON Schema) untuk Tool Calling LLM.
    """
    return registry.get_all_manifests()

@app.post("/execute", response_model=ModuleOutput)
async def execute_agent_tool(request: ToolCallRequest):
    """
    Execution endpoint.
    Menerima request dari Orchestrator, melakukan validasi Pydantic,
    dan mengeksekusi modul melalui Registry V2.
    """
    try:
        # Injeksi context sistem (seperti session_id)
        context = {"session_id": request.session_id}
        
        # Dispatch request via registry V2 (with strict validation)
        result = await registry.execute_tool(
            tool_name=request.tool_name, 
            raw_params=request.parameters,
            context=context
        )
        return result
        
    except ValueError as e:
        # Menangani tool yang tidak terdaftar
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # Menangani runtime error sistemik
        raise HTTPException(status_code=500, detail=f"Internal Bridge Error: {str(e)}")

if __name__ == "__main__":
    # Inisialisasi Communicate Layer
    print("[System] PEMALI V2 Engine Starting...")
    # Menggunakan reload=True untuk fase pengembangan
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)