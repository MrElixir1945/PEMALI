from models.schemas import PriorityLevel, PriorityResult

class ScoringAgent:
    """Modul 3: Priority Scoring Engine"""
    
    NDVI_THRESHOLD = -5.0
    AWARENESS_THRESHOLD = 30
    
    def score(self, ndvi_change: float, awareness: int) -> PriorityResult:
        high_damage = ndvi_change < self.NDVI_THRESHOLD
        low_awareness = awareness < self.AWARENESS_THRESHOLD
        
        if high_damage and low_awareness:
            priority = PriorityLevel.RED_EMERGENCY
            justification = f"NDVI turun {ndvi_change:.1f}% + kesadaran publik hanya {awareness}/100. Dua masalah kritis bersamaan."
            rank = 1
        elif high_damage and not low_awareness:
            priority = PriorityLevel.HIGH_PRIORITY
            justification = f"Kerusakan fisik tinggi ({ndvi_change:.1f}%). Komunitas sudah aware — prioritaskan penanganan lapangan."
            rank = 2
        elif not high_damage and low_awareness:
            priority = PriorityLevel.INFO_CORRECTION
            justification = "Persepsi publik tidak sebanding realita fisik yang masih baik."
            rank = 3
        else:
            priority = PriorityLevel.ROUTINE_MONITOR
            justification = "Kondisi stabil. Lanjutkan pemantauan rutin."
            rank = 4
            
        return PriorityResult(
            priority=priority,
            justification=justification,
            urgency_rank=rank
        )
