import asyncio
import datetime
import random
from typing import Dict, Any

from pydantic import BaseModel, Field

from backend.core.base_module import PemaliModuleV2, ModuleOutput


# =========================
# INPUT SCHEMA
# =========================
class MockInput(BaseModel):
    """
    Schema input untuk validasi otomatis oleh orchestrator.
    """

    target_location: str = Field(
        ...,
        description="Lokasi target untuk simulasi data lingkungan. Contoh: 'Ubud', 'Gianyar'."
    )

    analysis_type: str = Field(
        default="quick",
        description="Mode analisis simulasi. Pilihan umum: 'quick' atau 'deep'."
    )


# =========================
# MODULE IMPLEMENTATION
# =========================
class MockDataGenerator(PemaliModuleV2):

    @property
    def name(self) -> str:
        return "mock_data_generator"

    @property
    def description(self) -> str:
        return (
            "Menghasilkan data simulasi ekologi seperti NDVI, "
            "kualitas air, dan suhu permukaan untuk testing "
            "pipeline AI Agent tanpa menggunakan API satelit asli."
        )

    @property
    def input_schema(self):
        return MockInput

    async def execute(
        self,
        params: MockInput,
        context: Dict[str, Any]
    ) -> ModuleOutput:

        session_id = context.get("session_id", "unknown")

        try:
            # Simulasi latency API/network
            await asyncio.sleep(1.5)

            # Simulasi data lingkungan
            ndvi_score = round(random.uniform(0.2, 0.9), 2)

            water_quality = random.choice([
                "Good",
                "Moderate",
                "Critical"
            ])

            surface_temperature = round(
                random.uniform(25.0, 32.0),
                1
            )

            # Deteksi anomaly sederhana
            anomaly_detected = (
                ndvi_score < 0.4
                or water_quality == "Critical"
            )

            return ModuleOutput(
                status=200,
                data={
                    "location": params.target_location,
                    "analysis_mode": params.analysis_type,

                    "metrics": {
                        "ndvi_index": ndvi_score,
                        "water_quality_status": water_quality,
                        "surface_temperature_c": surface_temperature,
                        "anomaly_detected": anomaly_detected
                    },

                    "metadata": {
                        "session_id": session_id,
                        "data_source": "Random Simulation Engine",
                        "processed_at": str(datetime.datetime.now())
                    }
                }
            )

        except Exception as e:
            return ModuleOutput(
                status=500,
                error_msg=f"MockDataGenerator failed: {str(e)}"
            )