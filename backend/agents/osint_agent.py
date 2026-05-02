from models.schemas import OSINTData
from data.mock_data import MOCK_REGIONS, MOCK_OSINT_DATA

class OSINTAgent:
    """Modul 2: OSINT Social Listener (Mock)"""
    
    def __init__(self):
        # Dalam implementasi asli, di sini inisialisasi Tweepy/YouTube API
        pass
        
    def get_data(self, region: str) -> OSINTData:
        if region not in MOCK_REGIONS:
            raise ValueError(f"Wilayah {region} tidak ditemukan.")
            
        data = MOCK_OSINT_DATA[region]
        return OSINTData(
            region=region,
            total_posts=data["total_posts"],
            env_mentions=data["env_mentions"],
            awareness_score=data["awareness_score"],
            top_keywords=data["top_keywords"]
        )
