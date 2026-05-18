import asyncio
import httpx
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from backend.core.base_module import (
    PemaliModuleV2,
    ModuleOutput,
    THKAlignment,
    THKPresets,
)

class SeaLevelInput(BaseModel):
    """Input untuk monitoring pasang surut dan gelombang."""
    location_name: str = Field(
        ...,
        description="Nama pesisir di Bali, e.g. 'Pantai Kuta', 'Sanur', 'Nusa Dua'",
    )

class SeaLevelTideMonitor(PemaliModuleV2):
    """Sensor pasang surut dan gelombang laut berbasis Marine API (Real-time)."""

    @property
    def name(self) -> str:
        return "sea_level_tide_monitor"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Memantau ketinggian gelombang, periode gelombang, dan kondisi pasang surut di pesisir Bali secara real-time."

    @property
    def tags(self) -> List[str]:
        return ["marine", "hazard", "real-time"]

    @property
    def output_example(self) -> Dict[str, Any]:
        return {
            "status": 200,
            "data": {
                "location": "Pantai Kuta",
                "wave_height_m": 0.8,
                "wave_height_display": "0.8m",
                "status": "Aman (Tenang)"
            },
            "agent_hint": "Ketinggian gelombang di Pantai Kuta terpantau aman (0.8m).",
            "thk_alignment": {
                "parahyangan": "...",
                "pawongan": "...",
                "palemahan": "..."
            }
        }

    @property
    def input_schema(self):
        return SeaLevelInput

    async def execute(self, params: SeaLevelInput, context: Dict[str, Any]) -> ModuleOutput:
        start_ms = self._now_ms()
        
        # Coordinates for coastal areas in Bali
        lat, lon = -8.72, 115.17 # Kuta default
        loc = params.location_name.lower()
        if "sanur" in loc: lat, lon = -8.67, 115.26
        elif "nusa dua" in loc: lat, lon = -8.80, 115.23
        elif "lovina" in loc: lat, lon = -8.16, 115.02
        elif "padangbai" in loc: lat, lon = -8.53, 115.51

        url = f"https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}&current=wave_height,wave_direction,wave_period&timezone=Asia%2FSingapore"

        async with httpx.AsyncClient() as client:
            try:
                res = await client.get(url, timeout=10.0)
                if res.status_code != 200:
                    return ModuleOutput(
                        status=500, 
                        error_msg="Marine API error", 
                        agent_hint="Gagal mengambil data laut dari Marine API. Cek koneksi internet."
                    )
                
                raw_data = res.json()
                current = raw_data["current"]
                
                wave_h = current["wave_height"]
                wave_p = current["wave_period"]
                wave_d = current["wave_direction"]
                
                status = "Aman (Tenang)"
                if wave_h > 2.0:
                    status = "WASPADA (Gelombang Tinggi)"
                elif wave_h > 3.5:
                    status = "BAHAYA (Gelombang Ekstrim)"

                data = {
                    "location": params.location_name,
                    "wave_height_m": wave_h,
                    "wave_height_display": f"{wave_h}m",
                    "wave_period_s": wave_p,
                    "wave_period_display": f"{wave_p}s",
                    "wave_direction_deg": wave_d,
                    "wave_direction_display": f"{wave_d}°",
                    "status": status,
                    "source": "Open-Meteo Marine API (Real-time)",
                    "execution_ms": round(self._now_ms() - start_ms, 2)
                }

                hint = f"DATA LAUT REALTIME: Di {params.location_name} saat ini ketinggian gelombang {wave_h}m dengan periode {wave_p} detik. Status: {status}."

                return ModuleOutput(
                    status=200,
                    data=data,
                    agent_hint=hint,
                    thk_alignment=THKPresets.environmental_sensor("Pesisir/Laut", params.location_name)
                )
            except Exception as e:
                return ModuleOutput(
                    status=500, 
                    error_msg=str(e), 
                    agent_hint="Terjadi kesalahan teknis saat menghubungi Marine API."
                )
