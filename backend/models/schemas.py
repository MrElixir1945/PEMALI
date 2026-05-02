from pydantic import BaseModel
from typing import List, Optional
from enum import Enum
from datetime import datetime

class PriorityLevel(str, Enum):
    RED_EMERGENCY = "DARURAT_MERAH"
    HIGH_PRIORITY = "PRIORITAS_TINGGI"
    INFO_CORRECTION = "KLARIFIKASI_INFORMASI"
    ROUTINE_MONITOR = "MONITORING_RUTIN"

class SatelliteData(BaseModel):
    region: str
    ndvi_current: float
    ndvi_baseline: float
    change_pct: float
    status: str
    history: List[dict] # {month: "Jan", ndvi: 0.65}

class OSINTData(BaseModel):
    region: str
    total_posts: int
    env_mentions: int
    awareness_score: int
    top_keywords: List[str]

class PriorityResult(BaseModel):
    priority: PriorityLevel
    justification: str
    urgency_rank: int

class THKViolation(BaseModel):
    dimension: str
    status: str
    detail: str

class PolicyResult(BaseModel):
    thk_violations: List[THKViolation]
    rtrw_note: str
    recommendation: str

class AuditReport(BaseModel):
    region: str
    generated_at: str
    satellite: SatelliteData
    osint: OSINTData
    priority: PriorityResult
    policy: PolicyResult
