from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Type, Optional

# 1. Kontrak Output yang Ketat (V2 Standard)
class ModuleOutput(BaseModel):
    """
    Standar output untuk semua modul PEMALI.
    Status menggunakan HTTP-style code: 200 (OK), 400 (Bad Params), 500 (Error).
    """
    status: int = Field(..., description="HTTP-style status code")
    data: Dict[str, Any] = Field(default_factory=dict, description="Data mentah hasil eksekusi")
    error_msg: Optional[str] = Field(default=None, description="Detail error untuk Self-Correction AI")

# 2. Interface PemaliModule V2
class PemaliModuleV2(ABC):
    """
    Base class untuk semua modul sistem. 
    Mendukung auto-validation menggunakan Pydantic input_schema.
    """
    name: str
    description: str
    input_schema: Type[BaseModel]
    depends_on: List[str] = []  # Jalur dependensi DAG

    @abstractmethod
    async def execute(self, params: BaseModel, context: Dict[str, Any]) -> ModuleOutput:
        """
        Logika inti eksekusi modul.
        - params: Ter-validate otomatis oleh registry menggunakan input_schema.
        - context: Variabel sistem seperti session_id.
        """
        pass