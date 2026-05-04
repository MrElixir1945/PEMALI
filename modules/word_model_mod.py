from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field
from core.base_module import PemaliModuleV2, ModuleOutput
import asyncio

class WorldModelInput(BaseModel):
    query: str = Field(..., description="Kueri analitik (e.g., 'Proyeksi krisis air 12 bulan')")
    data_type: str = Field(default="climate_series", description="Jenis data: 'climate_series', 'ndvi_historical', 'demographics'")
    limit: Optional[int] = Field(default=100, description="Max baris data yang diekstrak")

class WorldModelModule(PemaliModuleV2):
    name = "world_model_mod"
    description = "Hybrid RAG untuk context-heavy ingestion. Mengekstrak raw time-series data dalam format terstruktur (JSONL/CSV) untuk simulasi kausalitas."
    input_schema = WorldModelInput
    depends_on = []

    async def execute(self, params: WorldModelInput, context: Dict[str, Any]) -> ModuleOutput:
        """
        Mockup: Query ke Vector DB / Graph DB.
        Mereturn raw data padat untuk LLM context window.
        """
        try:
            await asyncio.sleep(1.5) # RAG I/O delay

            # Mock RAG response (JSONL-style structure)
            mock_rag_data: List[Dict[str, Any]] = []
            
            if params.data_type == "climate_series":
                mock_rag_data = [
                    {"t": "2023-01", "rainfall_mm": 320, "deforestation_ha": 12},
                    {"t": "2023-02", "rainfall_mm": 280, "deforestation_ha": 15},
                    {"t": "2023-03", "rainfall_mm": 210, "deforestation_ha": 20},
                    {"t": "2023-04", "rainfall_mm": 150, "deforestation_ha": 25},
                ]
            else:
                mock_rag_data = [{"msg": f"Data type '{params.data_type}' not indexed yet."}]

            return ModuleOutput(
                status=200,
                data={
                    "query_context": params.query,
                    "retrieved_records": len(mock_rag_data),
                    "raw_series": mock_rag_data,
                    "format": "json_array"
                }
            )

        except Exception as e:
            return ModuleOutput(status=500, error_msg=f"RAG Engine Error: {str(e)}")