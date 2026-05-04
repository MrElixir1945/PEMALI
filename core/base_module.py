from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from typing import Any, Dict

# 1. Output Schema Validation
class ModuleOutput(BaseModel):
    status: str = Field(default="success", description="Status eksekusi: success/error")
    data: Dict[str, Any] = Field(..., description="Data teknis mentah untuk disimpan di State Manager")
    agent_hint: str = Field(..., description="Narasi singkat dan jelas untuk penalaran AI Agent")
    thk_alignment: str = Field(..., description="Analisis spesifik terkait pilar Tri Hita Karana")

# 2. Module Interface Contract
class PemaliModule(ABC):
    @property
    @abstractmethod
    def manifest(self) -> Dict[str, Any]:
        """
        Metadata untuk Tool Calling.
        Mendefinisikan nama, deskripsi fungsional, dan skema parameter JSON input.
        """
        pass

    @abstractmethod
    async def execute(self, params: Dict[str, Any], session_id: str = None) -> ModuleOutput:
        """
        Fungsi utama modul.
        Harus bersifat asynchronous dan mengembalikan tipe ModuleOutput.
        """
        pass
