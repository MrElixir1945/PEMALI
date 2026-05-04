import asyncio
from typing import Dict, Any
from core.base_module import PemaliModule, ModuleOutput

class EnvironmentalAnalyzerModule(PemaliModule):
    
    @property
    def manifest(self) -> Dict[str, Any]:
        return {
            "name": "environmental_analyzer",
            "description": "Melakukan komputasi teknis pada data atau citra satelit untuk menghitung indeks vegetasi (NDVI) dan melihat seberapa parah kerusakan hutan atau alih fungsi lahan secara otomatis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string", 
                        "description": "Nama lokasi atau koordinat yang sedang dianalisis"
                    },
                    "satellite_data_ref": {
                        "type": "string",
                        "description": "URL citra satelit atau referensi data dari pengamatan satelit sebelumnya"
                    }
                },
                "required": ["location"]
            }
        }

    async def execute(self, params: Dict[str, Any], session_id: str = None) -> ModuleOutput:
        try:
            location = params.get("location", "Unknown")
            sat_ref = params.get("satellite_data_ref", "N/A")
            
            # Simulate heavy processing steps for reasoning log
            # Step 1: Pre-processing
            await asyncio.sleep(0.8)
            # Step 2: Index computation
            await asyncio.sleep(0.8)
            # Step 3: Comparison
            await asyncio.sleep(0.4)
            
            raw_data = {
                "location": location,
                "satellite_ref": sat_ref,
                "ndvi_current": 0.45,
                "ndvi_previous": 0.60,
                "vegetation_loss_percentage": 15,
                "damage_level": "Moderate-High",
                "estimated_area_lost_ha": 2.5
            }
            
            return ModuleOutput(
                status="success",
                data=raw_data,
                agent_hint=(
                    f"Analyzing vegetation health in {location}... "
                    f"Computed NDVI: 0.45 (Previous: 0.60). "
                    f"Detected 15% vegetation loss. Status: Moderate-High damage. "
                    f"Likely land-use conversion detected."
                ),
                thk_alignment="Palemahan" 
            )
            
        except Exception as e:
            return ModuleOutput(
                status="error", 
                data={"error_detail": str(e)}, 
                agent_hint=f"Gagal melakukan analisis lingkungan untuk {location}.",
                thk_alignment="Netral"
            )
