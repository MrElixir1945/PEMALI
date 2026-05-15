import asyncio
import datetime
import random
from typing import Dict, Any, List

from pydantic import BaseModel, Field

from backend.core.base_module import (
    PemaliModuleV2, ModuleOutput, THKAlignment, THKPresets
)


# =========================
# INPUT SCHEMA
# =========================
class MockInput(BaseModel):
    """Schema input untuk validasi otomatis oleh orchestrator."""

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
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return (
            "Menghasilkan data simulasi ekologi seperti NDVI, kualitas air, "
            "dan suhu permukaan untuk testing pipeline AI Agent tanpa API satelit asli."
        )

    @property
    def tags(self) -> List[str]:
        return ["testing", "environment"]

    @property
    def input_schema(self):
        return MockInput

    @property
    def output_example(self) -> Dict[str, Any]:
        return {
            "status": 200,
            "data": {
                "location": "Ubud",
                "metrics": {
                    "ndvi_index": 0.72,
                    "water_quality_status": "Good",
                    "surface_temperature_c": 28.5,
                    "anomaly_detected": False
                }
            },
            "agent_hint": "NDVI 0.72 di Ubud normal. Tidak ada anomali terdeteksi.",
            "thk_alignment": {
                "parahyangan": "Data simulasi dihasilkan tanpa bias — murni random seed",
                "pawongan": "Hasil test dapat direproduksi untuk keperluan debugging tim",
                "palemahan": "Testing pipeline memastikan akurasi sebelum audit lingkungan nyata"
            }
        }

    async def execute(
        self,
        params: MockInput,
        context: Dict[str, Any]
    ) -> ModuleOutput:

        session_id = context.get("session_id", "unknown")
        start_ms = self._now_ms()

        try:
            await asyncio.sleep(1.5)

            ndvi_score = round(random.uniform(0.2, 0.9), 2)
            water_quality = random.choice(["Good", "Moderate", "Critical"])
            surface_temperature = round(random.uniform(25.0, 32.0), 1)
            anomaly_detected = ndvi_score < 0.4 or water_quality == "Critical"

            # Bangun agent_hint berdasarkan data
            if anomaly_detected:
                agent_hint = (
                    f"Anomali terdeteksi di {params.target_location}! "
                    f"NDVI={ndvi_score}, kualitas air={water_quality}. "
                    f"Rekomendasi: investigate lebih lanjut, bisa jadi tanda deforestasi atau pencemaran air."
                )
            else:
                agent_hint = (
                    f"Data {params.target_location} normal. "
                    f"NDVI={ndvi_score}, air={water_quality}, suhu={surface_temperature}C. "
                    f"Tidak perlu tindakan lanjutan."
                )

            execution_ms = round(self._now_ms() - start_ms, 2)
            data = {
                "location": params.target_location,
                "analysis_mode": params.analysis_type,
                "metrics": {
                    "ndvi_index": ndvi_score,
                    "water_quality_status": water_quality,
                    "surface_temperature_c": surface_temperature,
                    "anomaly_detected": anomaly_detected,
                },
                "metadata": {
                    "session_id": session_id,
                    "data_source": "Random Simulation Engine",
                    "processed_at": str(datetime.datetime.now()),
                    "execution_ms": execution_ms,
                },
            }

            return ModuleOutput(
                status=200,
                data=data,
                agent_hint=agent_hint,
                thk_alignment=THKPresets.environmental_sensor(
                    "Mock Data Generator", params.target_location
                ),
            )

        except Exception as e:
            execution_ms = round(self._now_ms() - start_ms, 2)
            return ModuleOutput(
                status=500,
                data={"execution_ms": execution_ms},
                error_msg=f"MockDataGenerator failed: {str(e)}",
                agent_hint=f"Simulasi gagal di {params.target_location}. Coba parameter berbeda.",
            )