from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Type, Optional

# 1. Strict Output Schema Contract
class ModuleOutput(BaseModel):
    status: int = Field(..., description="HTTP-like code: 200 (Success), 400 (Bad Input), 500 (Server Error)")
    data: Dict[str, Any] = Field(default_factory=dict, description="Payload raw data untuk 1M context LLM")
    error_msg: Optional[str] = Field(default=None, description="Pesan error eksplisit untuk SCL")

# 2. V2 Interface Contract
class PemaliModuleV2(ABC):
    # Manifest Definition
    name: str
    description: str
    input_schema: Type[BaseModel]
    depends_on: List[str] = []  # DAG Dependency Array

    @abstractmethod
    async def execute(self, params: BaseModel, context: Dict[str, Any]) -> ModuleOutput:
        """
        Fungsi eksekusi inti.
        - params: Objek turunan BaseModel (strict type).
        - context: Auto-injected state (e.g., session_id) dari Connector.
        """
        pass