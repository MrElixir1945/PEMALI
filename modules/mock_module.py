import random
import asyncio
from typing import Dict, Any
from pydantic import BaseModel, Field
from core.base_module import PemaliModuleV2, ModuleOutput

class MockInput(BaseModel):
    """
    Schema ini mendikte AI Agent parameter apa saja yang WAJIB dan BOLEH dikirim.
    Pydantic akan me-reject JSON AI jika tidak sesuai dengan format ini.
    """
    target_location: str = Field(..., description="Lokasi target untuk disimulasikan (misal: 'Ubud', 'Gianyar').")
    analysis_type: str = Field(default="quick", description="Tipe analisis: 'quick' atau 'deep'.")

class MockDataGenerator(PemaliModuleV2):
    # Metadata untuk manifest LLM
    name = "mock_data_generator"
    description = (
        "Menghasilkan data ekologi acak (NDVI, kualitas air, suhu) "
        "untuk testing pipeline AI Agent tanpa perlu memanggil API satelit asli."
    )
    input_schema = MockInput
    depends_on = [] # Tidak butuh modul lain berjalan lebih dulu

    async def execute(self, params: MockInput, context: Dict[str, Any]) -> ModuleOutput:
        try:
            # Simulasi network latency
            await asyncio.sleep(1.5)
            
            # Membuat data statistik secara random
            ndvi_score = round(random.uniform(0.2, 0.9), 2)
            water_quality = random.choice(["Good", "Moderate", "Critical"])
            temperature = round(random.uniform(25.0, 32.0), 1)
            
            # Set flag anomali jika angka random menunjukkan kondisi buruk
            is_anomaly = ndvi_score < 0.4 or water_quality == "Critical"

            raw_data = {
                "location_tested": params.target_location,
                "analysis_mode": params.analysis_type,
                "metrics": {
                    "ndvi_index": ndvi_score,
                    "water_quality_status": water_quality,
                    "surface_temperature_c": temperature,
                    "anomaly_detected": is_anomaly
                },
                "metadata": {
                    "session_context": context.get("session_id", "unknown"),
                    "data_source": "Random Simulation Engine"
                }
            }
            
            # Mengembalikan format mutlak V2 (Status, Data, Error Msg)
            return ModuleOutput(
                status=200,
                data=raw_data
            )
            
        except Exception as e:
            # Menangkap error jika simulasi gagal
            return ModuleOutput(
                status=500,
                error_msg=f"Mock Engine failed: {str(e)}"
            )