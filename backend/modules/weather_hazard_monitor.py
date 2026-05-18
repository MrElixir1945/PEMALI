import asyncio
import httpx
import os
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from backend.core.base_module import (
    PemaliModuleV2,
    ModuleOutput,
    THKAlignment,
    THKPresets,
)

class WeatherInput(BaseModel):
    """Input untuk monitoring cuaca ekstrim."""
    location_name: str = Field(
        ...,
        description="Nama daerah di Bali, e.g. 'Denpasar', 'Kintamani', 'Singaraja', 'Ubud'",
    )

class WeatherHazardMonitor(PemaliModuleV2):
    """Sensor cuaca ekstrim berbasis WeatherAPI.com (Real-time, Free 1M calls/bulan)."""

    @property
    def name(self) -> str:
        return "weather_hazard_monitor"

    @property
    def version(self) -> str:
        return "3.0.0"

    @property
    def description(self) -> str:
        return "Memantau suhu, kelembaban, angin, tekanan, UV index, visibilitas, dan kualitas udara secara real-time via WeatherAPI.com untuk mendeteksi potensi bencana cuaca."

    @property
    def tags(self) -> List[str]:
        return ["weather", "hazard", "real-time", "weatherapi"]

    @property
    def output_example(self) -> Dict[str, Any]:
        return {
            "status": 200,
            "data": {
                "location": "Denpasar, Bali",
                "temperature_c": 29.0,
                "feels_like_c": 35.0,
                "humidity_pct": 84,
                "wind_speed_kmh": 25.2,
                "wind_direction": "SE",
                "uv_index": 0,
                "pressure_mb": 1009,
                "visibility_km": 10.0,
                "condition": "Broken clouds",
                "hazard_level": "Aman"
            },
            "agent_hint": "CUACA REALTIME: Di Denpasar 29°C (terasa 35°C), kelembaban 84%, angin 25km/h SE, UV 0. Status: Aman.",
            "thk_alignment": {
                "parahyangan": "...",
                "pawongan": "...",
                "palemahan": "..."
            }
        }

    @property
    def input_schema(self):
        return WeatherInput

    async def execute(self, params: WeatherInput, context: Dict[str, Any]) -> ModuleOutput:
        start_ms = self._now_ms()

        api_key = os.getenv("WEATHERAPI_KEY", "")
        if not api_key:
            return ModuleOutput(
                status=500,
                error_msg="WEATHERAPI_KEY not set",
                agent_hint="API key WeatherAPI.com belum dikonfigurasi. Daftar gratis di weatherapi.com dan tambahkan WEATHERAPI_KEY ke .env."
            )

        # WeatherAPI endpoint: current weather + air quality
        url = f"http://api.weatherapi.com/v1/current.json?key={api_key}&q={params.location_name},Indonesia&aqi=yes"

        async with httpx.AsyncClient() as client:
            try:
                res = await client.get(url, timeout=10.0)

                if res.status_code != 200:
                    error_data = res.json() if res.headers.get("content-type", "").startswith("application/json") else {}
                    error_msg = error_data.get("error", {}).get("message", res.text[:200])
                    return ModuleOutput(
                        status=400,
                        error_msg=f"WeatherAPI error: {error_msg}",
                        agent_hint=f"Lokasi '{params.location_name}' tidak ditemukan atau API error: {error_msg}"
                    )

                data = res.json()
                current = data["current"]
                location = data["location"]
                condition = current["condition"]

                # Extract values
                temp_c = current["temp_c"]
                feels_like_c = current["feelslike_c"]
                humidity = current["humidity"]
                wind_kph = current["wind_kph"]
                wind_mph = current["wind_mph"]
                wind_dir = current["wind_dir"]
                wind_degree = current["wind_degree"]
                pressure_mb = current["pressure_mb"]
                precip_mm = current["precip_mm"]
                cloud_pct = current["cloud"]
                vis_km = current["vis_km"]
                uv_index = current["uv"]
                is_day = current["is_day"]
                condition_text = condition["text"]
                condition_icon = condition["icon"]

                # Air quality (if available)
                aqi_data = {}
                if current.get("air_quality"):
                    aq = current["air_quality"]
                    aqi_data = {
                        "pm2_5": aq.get("pm2_5"),
                        "pm10": aq.get("pm10"),
                        "co": aq.get("co"),
                        "no2": aq.get("no2"),
                        "o3": aq.get("o3"),
                        "so2": aq.get("so2"),
                        "epa_aqi": aq.get("us-epa-index"),
                        "gb_defra_aqi": aq.get("gb-defra-index"),
                    }

                # Calculate hazard level
                hazard_level = "Aman"
                warnings = []

                # Temperature hazards
                if temp_c > 38:
                    hazard_level = "Bahaya (Panas Ekstrim)"
                    warnings.append(f"Suhu {temp_c}°C sangat berbahaya")
                elif temp_c > 35:
                    hazard_level = "Waspada (Panas Ekstrim)"
                    warnings.append(f"Suhu {temp_c}°C sangat panas")
                elif temp_c > 32:
                    warnings.append(f"Suhu {temp_c}°C cukup panas")

                # Wind hazards
                if wind_kph > 60:
                    hazard_level = "Bahaya (Angin Badai)"
                    warnings.append(f"Angin {wind_kph}km/h — badai")
                elif wind_kph > 40:
                    hazard_level = "Waspada (Angin Kencang)"
                    warnings.append(f"Angin {wind_kph}km/h kencang")
                elif wind_kph > 25:
                    warnings.append(f"Angin {wind_kph}km/h cukup kencang")

                # Precipitation hazards
                if precip_mm > 20:
                    hazard_level = "Waspada (Hujan Lebat)"
                    warnings.append(f"Curah hujan {precip_mm}mm — hujan lebat")
                elif precip_mm > 10:
                    warnings.append(f"Curah hujan {precip_mm}mm — hujan sedang")

                # UV hazards
                if uv_index >= 11:
                    hazard_level = "Bahaya (UV Ekstrim)"
                    warnings.append(f"UV Index {uv_index} — ekstrem, hindari matahari")
                elif uv_index >= 8:
                    hazard_level = "Waspada (UV Sangat Tinggi)"
                    warnings.append(f"UV Index {uv_index} — sangat tinggi, gunakan pelindung")
                elif uv_index >= 6:
                    warnings.append(f"UV Index {uv_index} — tinggi, gunakan sunscreen")

                # Visibility hazards
                if vis_km < 1:
                    hazard_level = "Waspada (Visibilitas Sangat Rendah)"
                    warnings.append(f"Visibilitas hanya {vis_km}km")
                elif vis_km < 3:
                    warnings.append(f"Visibilitas {vis_km}km rendah")

                # Humidity
                if humidity > 95:
                    warnings.append(f"Kelembaban {humidity}% sangat tinggi")

                # Build hint
                hint_parts = [f"CUACA REALTIME: Di {location['name']}, {location['region']}"]
                hint_parts.append(f"suhu {temp_c}°C (terasa {feels_like_c}°C)")
                hint_parts.append(f"kelembaban {humidity}%")
                hint_parts.append(f"angin {wind_kph}km/h {wind_dir} ({wind_degree}°)")
                hint_parts.append(f"tekanan {pressure_mb}hPa")
                hint_parts.append(f"UV Index {uv_index}")
                if aqi_data.get("pm2_5") is not None:
                    hint_parts.append(f"PM2.5: {aqi_data['pm2_5']:.1f}µg/m³")
                hint_parts.append(f"kondisi: {condition_text}")

                if warnings:
                    hint_parts.append("⚠ " + "; ".join(warnings))

                hint_parts.append(f"Status: {hazard_level}.")

                result_data = {
                    "location": f"{location['name']}, {location['region']}, {location['country']}",
                    "coordinates": {"lat": location["lat"], "lon": location["lon"]},
                    "localtime": location["localtime"],
                    "temperature_c": temp_c,
                    "temperature_display": f"{temp_c}°C",
                    "feels_like_c": feels_like_c,
                    "feels_like_display": f"{feels_like_c}°C",
                    "humidity_pct": humidity,
                    "humidity_display": f"{humidity}%",
                    "wind_speed_kmh": wind_kph,
                    "wind_speed_mph": wind_mph,
                    "wind_speed_display": f"{wind_kph}km/h ({wind_mph}mph)",
                    "wind_direction": wind_dir,
                    "wind_degree": wind_degree,
                    "pressure_mb": pressure_mb,
                    "pressure_display": f"{pressure_mb}hPa",
                    "precipitation_mm": precip_mm,
                    "precipitation_display": f"{precip_mm}mm",
                    "cloud_pct": cloud_pct,
                    "visibility_km": vis_km,
                    "visibility_display": f"{vis_km}km",
                    "uv_index": uv_index,
                    "uv_display": str(uv_index),
                    "is_day": bool(is_day),
                    "condition": condition_text,
                    "condition_icon": f"https:{condition_icon}",
                    "air_quality": aqi_data if aqi_data else None,
                    "hazard_level": hazard_level,
                    "warnings": warnings,
                    "source": "WeatherAPI.com (Real-time)",
                    "execution_ms": round(self._now_ms() - start_ms, 2)
                }

                return ModuleOutput(
                    status=200,
                    data=result_data,
                    agent_hint=" ".join(hint_parts),
                    thk_alignment=THKPresets.environmental_sensor("Cuaca/Iklim", location["name"])
                )

            except Exception as e:
                return ModuleOutput(
                    status=500,
                    error_msg=str(e),
                    agent_hint="Terjadi kesalahan teknis saat menghubungi WeatherAPI.com."
                )
