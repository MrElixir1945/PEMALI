from models.schemas import PolicyResult, THKViolation
from data.mock_data import THK_PARAMETERS

class PolicyAgent:
    """Modul 4: Local Policy Analyzer (THK)"""
    
    def analyze(self, ndvi_change: float, awareness_score: int) -> PolicyResult:
        violations = []
        
        # Parahyangan check
        if ndvi_change < THK_PARAMETERS["parahyangan"]["ndvi_threshold"]:
            violations.append(THKViolation(
                dimension="Parahyangan",
                status="TERLANGGAR",
                detail=THK_PARAMETERS["parahyangan"]["fail_msg"]
            ))
            
        # Pawongan check
        if awareness_score < THK_PARAMETERS["pawongan"]["awareness_threshold"]:
            violations.append(THKViolation(
                dimension="Pawongan",
                status="TERLANGGAR",
                detail=THK_PARAMETERS["pawongan"]["fail_msg"]
            ))
            
        # Palemahan check
        if ndvi_change < THK_PARAMETERS["palemahan"]["ndvi_threshold"]:
            violations.append(THKViolation(
                dimension="Palemahan",
                status="TERLANGGAR",
                detail=THK_PARAMETERS["palemahan"]["fail_msg"]
            ))
            
        return PolicyResult(
            thk_violations=violations,
            rtrw_note="Rujuk Perda Provinsi Bali No. 2 Tahun 2023 tentang Rencana Tata Ruang Wilayah.",
            recommendation=self._generate_recommendation(violations)
        )
        
    def _generate_recommendation(self, violations: list[THKViolation]) -> str:
        if not violations:
            return "Kondisi stabil. Terus jalankan awig-awig pelestarian desa."
            
        dims = [v.dimension for v in violations]
        return f"Pelanggaran nilai {', '.join(dims)} terdeteksi. Segera koordinasikan dengan Bendesa Adat untuk peninjauan lapangan."
