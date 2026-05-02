from models.schemas import SatelliteData
from data.mock_data import MOCK_REGIONS, MOCK_SATELLITE_DATA

class SatelliteAgent:
    """Modul 1: Satellite Environmental Monitor (Mock)"""
    
    def __init__(self):
        # Dalam implementasi asli, di sini inisialisasi GEE API
        pass
        
    def get_data(self, region: str) -> SatelliteData:
        if region not in MOCK_REGIONS:
            raise ValueError(f"Wilayah {region} tidak ditemukan.")
            
        data = MOCK_SATELLITE_DATA[region]
        return SatelliteData(
            region=region,
            ndvi_current=data["ndvi_current"],
            ndvi_baseline=data["ndvi_baseline"],
            change_pct=data["change_pct"],
            status=data["status"],
            history=data["history"]
        )
