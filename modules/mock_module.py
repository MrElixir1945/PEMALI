import asyncio
from typing import Dict, Any
from core.base_module import PemaliModule, ModuleOutput

class MockModule(PemaliModule):
    @property
    def manifest(self) -> Dict[str, Any]:
        return {
            "name": "mock_testing_tool",
            "description": "Dummy tool untuk validasi end-to-end I/O pipeline dan Tool Calling.",
            "parameters": {
                "type": "object",
                "properties": {
                    "test_message": {
                        "type": "string", 
                        "description": "Pesan dari AI Agent untuk trigger."
                    }
                },
                "required": ["test_message"]
            }
        }

    async def execute(self, params: Dict[str, Any], session_id: str = None) -> ModuleOutput:
        # Simulate network delay / processing time
        await asyncio.sleep(0.5)
        
        msg = params.get("test_message", "Empty payload")
        
        return ModuleOutput(
            status="success",
            data={
                "received_payload": msg,
                "simulated_ndvi": 0.85,
                "simulated_sentiment": 0.9
            },
            agent_hint=f"Mock testing berhasil. Input AI: '{msg}'. Pipeline I/O stabil.",
            thk_alignment="Netral (Environment Testing)."
        )