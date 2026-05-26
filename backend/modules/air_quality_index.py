import asyncio
import os
import httpx
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

class AirQualityInput(BaseModel):
    """Input untuk sensor kualitas udara."""
    location_name: str = Field(
        ...,
        description="Nama daerah di Bali, e.g. 'Denpasar', 'Bedugul', 'Kuta'",
    )
    date: Optional[str] = Field(
        default=None,
        description="Tanggal sampel ISO format YYYY-MM-DD. Default: hari ini.",
    )

class AirQualityIndex(PemaliModuleV2):
    """Sensor polusi udara AQI (Real-time via OpenWeatherMap/IQAir)."""

    @property
    def name(self) -> str:
        return "air_quality_index"

    @property
    def version(self) -> str:
        return "2.0.0"

    @property
    def description(self) -> str:
        return "Mengecek tingkat polusi udara (AQI, PM2.5, CO2, NO2) secara real-time via IQAir/OpenWeather API."

    @property
    def tags(self) -> List[str]:
        return ["air", "environment", "real-time"]

    @property
    def output_example(self) -> Dict[str, Any]:
        return {
            "status": 200,
            "data": {
                "location_name": "Denpasar",
                "aqi_level": 2,
                "status": "Cukup",
                "pm2_5": 18.5,
                "source": "OpenWeatherMap Air Pollution API"
            },
            "agent_hint": "AQI Denpasar level 2 (Cukup). PM2.5 18.5 µg/m³ — di atas batas WHO 15 µg/m³.",
            "thk_alignment": {
                "parahyangan": "...",
                "pawongan": "...",
                "palemahan": "..."
            }
        }

    @property
    def depends_on(self) -> List[str]:
        return []

    @property
    def input_schema(self):
        return AirQualityInput

    async def execute(self, params: AirQualityInput, context: Dict[str, Any]) -> ModuleOutput:
        start_ms = self._now_ms()
        
        iqair_key = os.getenv("IQAIR_API_KEY")
        owm_key = os.getenv("OPENWEATHER_API_KEY")
        
        if not owm_key and not iqair_key:
            return ModuleOutput(
                status=500,
                error_msg="API Keys (OpenWeatherMap/IQAir) tidak ditemukan di environment.",
                agent_hint="Harap konfigurasi API Key di file .env untuk menggunakan modul Kualitas Udara."
            )
        
        # Prioritaskan OpenWeatherMap
        if owm_key:
            return await self._execute_openweathermap(params, owm_key, start_ms)
        else:
            return await self._execute_iqair(params, iqair_key, start_ms)

    async def _execute_openweathermap(self, params: AirQualityInput, api_key: str, start_ms: float) -> ModuleOutput:
        """Fetch data dari OpenWeatherMap Air Pollution API."""
        lat, lon = -8.65, 115.21 # Default Denpasar
        loc_name = params.location_name.lower()
        if "ubud" in loc_name: lat, lon = -8.50, 115.26
        elif "singaraja" in loc_name: lat, lon = -8.11, 115.09
        elif "kuta" in loc_name: lat, lon = -8.73, 115.17
        elif "gianyar" in loc_name: lat, lon = -8.54, 115.32
        
        url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={api_key}"
        
        async with httpx.AsyncClient() as client:
            try:
                res = await client.get(url, timeout=10.0)
                if res.status_code != 200:
                    return ModuleOutput(
                        status=res.status_code, 
                        error_msg=f"OWM API Error: {res.text}",
                        agent_hint="Gagal mengambil data kualitas udara dari OpenWeatherMap. Cek API key atau koneksi."
                    )
                
                data = res.json()
                main = data["list"][0]["main"]
                comp = data["list"][0]["components"]
                aqi = main["aqi"] # 1=Good, 2=Fair, 3=Moderate, 4=Poor, 5=Very Poor
                
                status_map = {1: "Baik", 2: "Cukup", 3: "Sedang", 4: "Buruk", 5: "Sangat Buruk"}
                status_aqi = status_map.get(aqi, "Unknown")
                
                result_data = {
                    "location_name": params.location_name,
                    "aqi_level": aqi,
                    "status": status_aqi,
                    "pm2_5": comp["pm2_5"],
                    "pm10": comp["pm10"],
                    "co": comp["co"],
                    "no2": comp["no2"],
                    "source": "OpenWeatherMap Air Pollution API",
                    "execution_ms": round(self._now_ms() - start_ms, 2)
                }
                
                hint = f"AQI {params.location_name} level {aqi} ({status_aqi}). PM2.5: {comp['pm2_5']} µg/m³."
                if comp['pm2_5'] > 15:
                    hint += " Nilai ini di atas batas aman WHO (15 µg/m³). Perhatikan aktivitas luar ruangan."
                else:
                    hint += " Udara dalam kondisi bersih menurut standar WHO."
                
                return ModuleOutput(
                    status=200,
                    data=result_data,
                    agent_hint=hint,
                    thk_alignment=THKPresets.environmental_sensor("Kualitas Udara", params.location_name)
                )
            except Exception as e:
                return ModuleOutput(
                    status=500, 
                    error_msg=f"OWM Exception: {str(e)}",
                    agent_hint="Terjadi kesalahan teknis saat menghubungi OpenWeatherMap."
                )

    async def _execute_iqair(self, params: AirQualityInput, api_key: str, start_ms: float) -> ModuleOutput:
        """Fetch data asli dari IQAir API."""
        city = "Denpasar"
        if "kuta" in params.location_name.lower(): city = "Kuta"
        
        url = f"https://api.airvisual.com/v2/city?city={city}&state=Bali&country=Indonesia&key={api_key}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, timeout=10.0)
                if response.status_code != 200:
                    return ModuleOutput(
                        status=response.status_code, 
                        error_msg=f"IQAir API Error: {response.text}",
                        agent_hint="Gagal mengambil data kualitas udara dari IQAir. Cek API key atau koneksi."
                    )
                
                res_json = response.json()
                if res_json.get("status") != "success":
                    return ModuleOutput(
                        status=500, 
                        error_msg=f"IQAir Error: {res_json.get('data', {}).get('message')}",
                        agent_hint=f"Layanan IQAir melaporkan error: {res_json.get('data', {}).get('message')}"
                    )
                
                current = res_json["data"]["current"]["pollution"]
                aqi = current["aqius"]
                main_pollutant = current["mainus"]
                
                data = {
                    "location_name": f"{res_json['data']['city']}, {res_json['data']['state']}",
                    "aqi": aqi,
                    "main_pollutant": main_pollutant,
                    "source": "IQAir Real-time API",
                    "execution_ms": round(self._now_ms() - start_ms, 2)
                }
                
                status_aqi = "Baik" if aqi <= 50 else ("Sedang" if aqi <= 100 else "Tidak Sehat")
                hint = f"AQI {data['location_name']} saat ini adalah {aqi} ({status_aqi}). Polutan utama: {main_pollutant}."
                if aqi > 50:
                    hint += " Kualitas udara menurun, pertimbangkan untuk mengurangi aktivitas luar ruangan."
                
                return ModuleOutput(
                    status=200,
                    data=data,
                    agent_hint=hint,
                    thk_alignment=THKPresets.environmental_sensor("Kualitas Udara (IQAir)", data['location_name'])
                )
            except Exception as e:
                return ModuleOutput(
                    status=500, 
                    error_msg=f"IQAir Exception: {str(e)}",
                    agent_hint="Terjadi kesalahan teknis saat menghubungi layanan IQAir."
                )

module = AirQualityIndex()
