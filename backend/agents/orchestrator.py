from datetime import datetime
from agents.satellite_agent import SatelliteAgent
from agents.osint_agent import OSINTAgent
from agents.scoring_agent import ScoringAgent
from agents.policy_agent import PolicyAgent
from models.schemas import AuditReport

class PEMALIOrchestrator:
    """Koordinator utama yang menjalankan semua agen secara berurutan"""
    
    def __init__(self):
        self.satellite = SatelliteAgent()
        self.osint = OSINTAgent()
        self.scoring = ScoringAgent()
        self.policy = PolicyAgent()
        
    def run_audit(self, region: str) -> AuditReport:
        print(f"[PEMALI] Memulai audit untuk wilayah: {region.upper()}")
        
        # 1. Ambil data fisik
        sat_data = self.satellite.get_data(region)
        
        # 2. Ambil data sosial
        osint_data = self.osint.get_data(region)
        
        # 3. Hitung skor prioritas
        priority_res = self.scoring.score(sat_data.change_pct, osint_data.awareness_score)
        
        # 4. Analisis kebijakan (THK)
        policy_res = self.policy.analyze(sat_data.change_pct, osint_data.awareness_score)
        
        return AuditReport(
            region=region,
            generated_at=datetime.now().isoformat(),
            satellite=sat_data,
            osint=osint_data,
            priority=priority_res,
            policy=policy_res
        )
