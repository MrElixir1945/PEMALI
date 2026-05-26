import asyncio
import httpx
import os
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from backend.core.base_module import (
    PemaliModuleV2,
    ModuleOutput,
    THKAlignment,
    THKPresets,
)

logger = logging.getLogger(__name__)

class FireInput(BaseModel):
    """Input untuk deteksi titik api."""
    region: str = Field(
        default="Bali",
        description="Wilayah yang akan dipantau. Contoh: 'Kintamani', 'Gianyar', 'Bali'",
    )

class FireHotspotDetector(PemaliModuleV2):
    """Sensor titik api satelit berbasis NASA FIRMS API (Real-time)."""

    @property
    def name(self) -> str:
        return "fire_hotspot_detector"

    @property
    def version(self) -> str:
        return "2.0.0"

    @property
    def description(self) -> str:
        return "Mendeteksi titik panas (hotspot) kebakaran hutan di Bali menggunakan data satelit MODIS/VIIRS via NASA FIRMS."

    @property
    def tags(self) -> List[str]:
        return ["fire", "satellite", "hazard", "real-time"]

    @property
    def output_example(self) -> Dict[str, Any]:
        return {
            "status": 200,
            "data": {
                "region": "Bali",
                "hotspots_count": 0,
                "status": "Aman",
                "source": "NASA FIRMS (Satellite Real-time)"
            },
            "agent_hint": "Tidak terdeteksi titik panas (hotspot) kebakaran di wilayah Bali.",
            "thk_alignment": {
                "parahyangan": "...",
                "pawongan": "...",
                "palemahan": "..."
            }
        }

    @property
    def input_schema(self):
        return FireInput

    async def execute(self, params: FireInput, context: Dict[str, Any]) -> ModuleOutput:
        start_ms = self._now_ms()
        api_key = os.getenv("NASA_FIRMS_API_KEY")
        
        if not api_key:
            return ModuleOutput(
                status=500,
                error_msg="NASA_FIRMS_API_KEY tidak ditemukan di environment.",
                agent_hint="Harap konfigurasi NASA_FIRMS_API_KEY di file .env untuk deteksi kebakaran."
            )

        # Area Bali: [114.4, -8.9, 115.8, -8.0]
        url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{api_key}/MODIS_NRT/114.4,-8.9,115.8,-8.0/1"

        async with httpx.AsyncClient() as client:
            try:
                res = await client.get(url, timeout=15.0)
                if res.status_code != 200 or "Invalid API call" in res.text:
                    return ModuleOutput(
                        status=res.status_code if res.status_code != 200 else 401,
                        error_msg=f"NASA FIRMS API Error: {res.text}",
                        agent_hint="Gagal mengambil data satelit NASA. Periksa API Key atau koneksi."
                    )
                
                lines = res.text.strip().split("\n")
                hotspots = []
                if len(lines) > 1:
                    for line in lines[1:]:
                        parts = line.split(",")
                        if len(parts) >= 9:
                            hotspots.append({
                                "lat": parts[0],
                                "lon": parts[1],
                                "confidence": parts[8],
                                "satellite": parts[7]
                            })

                status = "Aman" if not hotspots else "WASPADA (Hotspot Terdeteksi)"
                
                data = {
                    "region": params.region,
                    "hotspots_count": len(hotspots),
                    "details": hotspots[:5],
                    "status": status,
                    "source": "NASA FIRMS (Satellite Real-time)",
                    "execution_ms": round(self._now_ms() - start_ms, 2)
                }

                hint = f"DATA SATELIT: Terdeteksi {len(hotspots)} titik panas (hotspot) di wilayah {params.region}. Status: {status}."

                return ModuleOutput(
                    status=200,
                    data=data,
                    agent_hint=hint,
                    thk_alignment=THKPresets.environmental_sensor("Titik Panas/Kebakaran", params.region)
                )
            except Exception as e:
                return ModuleOutput(
                    status=500,
                    error_msg=f"NASA API Exception: {str(e)}",
                    agent_hint="Gagal terhubung ke NASA FIRMS. Cek API key atau koneksi internet."
                )

module = FireHotspotDetector()
