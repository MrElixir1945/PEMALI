import asyncio
import httpx
import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from backend.core.base_module import (
    PemaliModuleV2,
    ModuleOutput,
    THKAlignment,
    THKPresets,
)

class EarthquakeInput(BaseModel):
    """Input untuk monitoring gempa."""
    min_magnitude: float = Field(
        default=3.0,
        description="Magnitude minimal yang akan dimonitor. Default: 3.0",
    )

class EarthquakeRiskMonitor(PemaliModuleV2):
    """Sensor aktivitas seismik berbasis USGS Earthquake API (Real-time & Gratis)."""

    @property
    def name(self) -> str:
        return "earthquake_risk_monitor"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Memantau gempa bumi terbaru di sekitar wilayah Indonesia (khususnya Bali) menggunakan data USGS."

    @property
    def tags(self) -> List[str]:
        return ["seismic", "hazard", "real-time"]

    @property
    def output_example(self) -> Dict[str, Any]:
        return {
            "status": 200,
            "data": {
                "region": "Bali",
                "earthquake_count": 0,
                "status": "Aman",
                "source": "USGS Earthquake API"
            },
            "agent_hint": "Tidak terdeteksi gempa signifikan di wilayah Bali dalam 24 jam terakhir.",
            "thk_alignment": {
                "parahyangan": "...",
                "pawongan": "...",
                "palemahan": "..."
            }
        }

    @property
    def input_schema(self):
        return EarthquakeInput

    async def execute(self, params: EarthquakeInput, context: Dict[str, Any]) -> ModuleOutput:
        start_ms = self._now_ms()
        
        # Query 24 jam terakhir di sekitar Bali
        # Bounding box Bali/Jawa Timur/NTB: minlat=-10, maxlat=-6, minlon=113, maxlon=118
        starttime = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
        url = (
            f"https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson"
            f"&starttime={starttime}&minmagnitude={params.min_magnitude}"
            f"&minlatitude=-10&maxlatitude=-6&minlongitude=113&maxlongitude=118"
        )

        async with httpx.AsyncClient() as client:
            try:
                res = await client.get(url, timeout=10.0)
                if res.status_code != 200:
                    return ModuleOutput(
                        status=500, 
                        error_msg="USGS API error",
                        agent_hint="Gagal mengambil data gempa dari USGS. Cek koneksi internet."
                    )
                
                raw_data = res.json()
                features = raw_data.get("features", [])
                
                quakes = []
                for f in features:
                    props = f["properties"]
                    coords = f["geometry"]["coordinates"]
                    quakes.append({
                        "place": props["place"],
                        "mag": props["mag"],
                        "time": datetime.datetime.fromtimestamp(props["time"]/1000).isoformat(),
                        "depth_km": coords[2]
                    })

                status = "Aman"
                if quakes:
                    highest_mag = max(q["mag"] for q in quakes)
                    if highest_mag > 5.0:
                        status = "WASPADA (Gempa Signifikan)"
                    else:
                        status = "Informasi (Gempa Kecil Terdeteksi)"

                data = {
                    "quakes_count_24h": len(quakes),
                    "latest_quakes": quakes[:3], # Top 3 terbaru
                    "status": status,
                    "source": "USGS Earthquake API (Real-time)",
                    "execution_ms": round(self._now_ms() - start_ms, 2)
                }

                hint = f"STATUS SEISMIK: Terdeteksi {len(quakes)} gempa di sekitar Bali dalam 24 jam terakhir. Status: {status}."
                if len(quakes) > 0:
                    max_mag = max(q["mag"] for q in quakes)
                    if max_mag > 5.0:
                        hint += f" WASPADA! Gempa terbesar berkekuatan {max_mag} M. Periksa potensi kerusakan."

                return ModuleOutput(
                    status=200,
                    data=data,
                    agent_hint=hint,
                    thk_alignment=THKPresets.environmental_sensor("Seismik/Gempa", "Bali")
                )
            except Exception as e:
                return ModuleOutput(
                    status=500, 
                    error_msg=str(e),
                    agent_hint="Terjadi kesalahan teknis saat menghubungi layanan USGS."
                )
