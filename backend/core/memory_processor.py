"""
Cognitive Memory Processor untuk PEMALI.

Mengekstrak pola temporal dan korelasi dari hasil audit
agar AI Agent bisa "belajar" dari pengalaman sebelumnya.

Layer 1: Temporal Pattern Extraction
- Mendeteksi tren: "NDVI turun 3 bulan berturut-turut"
- Mendeteksi seasonal: "Setiap musim kemarau terjadi deforestasi"
- Mendeteksi anomaly: "Kualitas air menurun drastis bulan ini"
- Mendeteksi korelasi: "Lokasi X deforestasi → Lokasi Y banjir"

Layer 2: Knowledge Graph Builder
- Membangun node (entity, location, issue)
- Membangun edge (relasi kausal, temporal, spasial)
"""

import json
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from pydantic import BaseModel, Field


# ============================================================
# TIPE DATA
# ============================================================

class PatternMatch(BaseModel):
    pattern_type: str
    entities: List[str]
    confidence: float
    description: str
    evidence: Dict[str, Any]

class TemporalSignature(BaseModel):
    months: Optional[List[int]] = None
    seasons: Optional[List[str]] = None
    recurrence: Optional[str] = None  # 'yearly', 'monthly', 'weekly', 'none'
    trend: Optional[str] = None  # 'increasing', 'decreasing', 'stable', 'fluctuating'

class CognitiveSnapshot(BaseModel):
    session_id: str
    location: Optional[str] = None
    issue_type: Optional[str] = None
    severity: Optional[str] = None  # 'critical', 'warning', 'stable', 'improving'
    metrics: Dict[str, Any] = Field(default_factory=dict)
    patterns: List[PatternMatch] = Field(default_factory=list)
    temporal: Optional[TemporalSignature] = None
    related_entities: List[str] = Field(default_factory=list)
    raw_summary: str = Field(default="", description="Ringkasan teks hasil audit")


# ============================================================
# TEMPLATE DETECTOR
# ============================================================

class TemporalPatternExtractor:

    def __init__(self):
        self.season_map = {
            1: "wet", 2: "wet", 3: "transition_dry",
            4: "dry", 5: "dry", 6: "dry",
            7: "dry", 8: "dry", 9: "dry",
            10: "transition_wet", 11: "wet", 12: "wet"
        }
        self.metric_patterns = [
            (r"\b(ndvi|vegetation_index|vegetasi)\b", "vegetation_health"),
            (r"\b(water_quality|kualitas_air|ph|turbidity)\b", "water_quality"),
            (r"\b(deforestasi|deforestation|forest_loss|hutan)\b", "deforestation"),
            (r"\b(temperature|suhu|surface_temp)\b", "temperature"),
            (r"\b(debit|discharge|water_flow)\b", "water_flow"),
            (r"\b(kebakaran|fire|burn|hotspot)\b", "fire_risk"),
            (r"\b(banjir|flood|water_level|ketinggian)\b", "flood_risk"),
        ]
        self.location_patterns = [
            r"\b(Ubud|Denpasar|Gianyar|Karangasem|Buleleng|Jembrana|"
            r"Bangli|Badung|Tabanan|Klungkung|Singaraja|Negara|"
            r"Amlapura|Semarapura|Mangupura|Tabanan)\b"
        ]

    def extract(self, audit_result: Dict[str, Any], session_id: str = "") -> CognitiveSnapshot:
        report_text = self._flatten_result(audit_result)
        location = self._extract_location(report_text)
        severity = self._extract_severity(report_text)
        metrics = self._extract_metrics(audit_result)
        issue_type = self._extract_issue_type(report_text, metrics)
        patterns = self._detect_patterns(report_text, metrics)
        temporal = self._extract_temporal_signature(metrics)

        return CognitiveSnapshot(
            session_id=session_id,
            location=location,
            issue_type=issue_type,
            severity=severity,
            metrics=metrics,
            patterns=[PatternMatch(**p) if isinstance(p, dict) else p for p in patterns],
            temporal=TemporalSignature(**temporal) if temporal else None,
            related_entities=self._extract_entities(report_text),
            raw_summary=report_text[:500]
        )

    def _flatten_result(self, data: Any, max_depth: int = 3) -> str:
        if isinstance(data, str):
            return data
        if isinstance(data, dict):
            return " ".join(
                f"{k}: {self._flatten_result(v, max_depth - 1)}"
                for k, v in data.items()
                if max_depth > 0 and not k.startswith("_")
            )
        if isinstance(data, list):
            return " ".join(self._flatten_result(i, max_depth - 1) for i in data[:10])
        return str(data)

    def _extract_location(self, text: str) -> Optional[str]:
        for pattern in self.location_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        return None

    def _extract_metrics(self, audit_result: Dict[str, Any]) -> Dict[str, Any]:
        metrics = {}
        flat = self._flatten_result(audit_result)

        kv_patterns = [
            (r"(?:ndvi|vegetation_index)[\s:=]+([\d.]+)", "ndvi"),
            (r"(?:ph)[\s:=]+([\d.]+)", "ph"),
            (r"(?:temperature|suhu)[\s:=]+([\d.]+)", "temperature"),
            (r"(?:debit)[\s:=]+([\d.]+)", "debit"),
            (r"(?:water_level)[\s:=]+([\d.]+)", "water_level"),
            (r"(?:anomaly_detected)[\s:=]+(\w+)", "anomaly"),
        ]

        for pattern, key in kv_patterns:
            m = re.search(pattern, flat, re.IGNORECASE)
            if m:
                try:
                    metrics[key] = float(m.group(1))
                except ValueError:
                    metrics[key] = m.group(1)

        if isinstance(audit_result, dict):
            for k, v in audit_result.items():
                if isinstance(v, dict) and "data" in v:
                    inner = v["data"]
                    if isinstance(inner, dict):
                        for mk, mv in inner.items():
                            if isinstance(mv, (int, float)):
                                metrics[mk] = mv

        return metrics

    def _extract_severity(self, text: str) -> str:
        lower = text.lower()
        if any(w in lower for w in ["critical", "kritis", "darurat", "emergency"]):
            return "critical"
        if any(w in lower for w in ["warning", "perlu perhatian", "anomaly_detected: true"]):
            return "warning"
        if any(w in lower for w in ["anomaly_detected: false", "stable", "stabil"]):
            return "stable"
        return "unknown"

    def _extract_issue_type(self, text: str, metrics: Dict[str, Any]) -> str:
        scores = {}
        for pattern, label in self.metric_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                scores[label] = scores.get(label, 0) + len(matches)

        if "deforestation" in scores and "ndvi" in metrics:
            return "deforestation"
        if "flood_risk" in scores and "debit" in metrics:
            return "flood_risk"
        if "fire_risk" in scores and "temperature" in metrics:
            return "fire_risk"
        if "water_quality" in scores:
            return "water_quality"
        if scores:
            return max(scores, key=scores.get)

        return "general_environmental"

    def _detect_patterns(self, text: str, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        patterns = []

        if "ndvi" in metrics:
            ndvi = metrics["ndvi"]
            if ndvi < 0.3:
                patterns.append({
                    "pattern_type": "vegetation_decline_critical",
                    "entities": ["ndvi"],
                    "confidence": 0.85,
                    "description": f"NDVI sangat rendah ({ndvi}), vegetasi dalam kondisi kritis",
                    "evidence": {"ndvi": ndvi, "threshold_critical": 0.3}
                })
            elif ndvi < 0.5:
                patterns.append({
                    "pattern_type": "vegetation_decline_warning",
                    "entities": ["ndvi"],
                    "confidence": 0.7,
                    "description": f"NDVI menunjukkan penurunan ({ndvi}), perlu pemantauan",
                    "evidence": {"ndvi": ndvi, "threshold_warning": 0.5}
                })

        if metrics.get("anomaly") in ["True", "true", True]:
            patterns.append({
                "pattern_type": "anomaly_detected",
                "entities": ["anomaly"],
                "confidence": 0.9,
                "description": "Anomali terdeteksi dalam data audit ini",
                "evidence": {"triggered": True}
            })

        if "temperature" in metrics and "fire_risk" in text.lower():
            patterns.append({
                "pattern_type": "fire_risk_elevated",
                "entities": ["temperature", "fire"],
                "confidence": 0.75,
                "description": f"Suhu permukaan tinggi ({metrics['temperature']}C), risiko kebakaran meningkat",
                "evidence": {"temperature": metrics["temperature"]}
            })

        return patterns

    def _extract_temporal_signature(self, metrics: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        current_month = now.month
        current_season = self.season_map.get(current_month, "unknown")

        if not metrics:
            return None

        high_risk_months = []
        if metrics.get("ndvi", 1) < 0.4:
            high_risk_months.append(current_month)

        return {
            "months": high_risk_months if high_risk_months else None,
            "seasons": [current_season],
            "recurrence": "none",
            "trend": self._guess_trend(metrics)
        }

    def _guess_trend(self, metrics: Dict[str, Any]) -> str:
        ndvi = metrics.get("ndvi")
        temp = metrics.get("temperature")
        if ndvi is not None and ndvi < 0.4 and temp and temp > 30:
            return "decreasing"
        return "unknown"

    def _extract_entities(self, text: str) -> List[str]:
        entities = []
        seen = set()

        for pattern, label in self.metric_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                if label not in seen:
                    entities.append(label)
                    seen.add(label)

        location = self._extract_location(text)
        if location and location not in seen:
            entities.append(location)

        return entities


# ============================================================
# KNOWLEDGE GRAPH BUILDER
# ============================================================

class KnowledgeGraphBuilder:
    """
    Membangun graf memori dari CognitiveSnapshot.
    Mengidentifikasi relasi antar entity dan event audit.
    """

    def build_nodes(self, snapshot: CognitiveSnapshot) -> List[Dict[str, Any]]:
        nodes = []

        if snapshot.location:
            nodes.append({
                "node_type": "location",
                "label": snapshot.location,
                "properties": {
                    "name": snapshot.location,
                    "first_seen": datetime.now(timezone.utc).isoformat()
                }
            })

        if snapshot.issue_type:
            nodes.append({
                "node_type": "issue",
                "label": f"{snapshot.issue_type}",
                "properties": {
                    "issue_type": snapshot.issue_type,
                    "severity": snapshot.severity,
                    "session_id": snapshot.session_id
                }
            })

        for entity in snapshot.related_entities:
            if entity != snapshot.location:
                nodes.append({
                    "node_type": "metric",
                    "label": entity,
                    "properties": {
                        "name": entity,
                        "value": snapshot.metrics.get(entity)
                    }
                })

        return nodes

    def build_edges(self, snapshot: CognitiveSnapshot, node_ids: Dict[str, int]) -> List[Dict[str, Any]]:
        edges = []
        location_id = node_ids.get(snapshot.location)
        now = datetime.now(timezone.utc)

        if location_id:
            for etype in ["issue", "metric"]:
                for label in snapshot.related_entities:
                    target_id = node_ids.get(label)
                    if target_id:
                        rel_type = "has_issue" if etype == "issue" else "has_metric"
                        edges.append({
                            "source_label": snapshot.location,
                            "target_label": label,
                            "relation_type": rel_type,
                            "temporal_context": {
                                "season": snapshot.temporal.seasons[0] if snapshot.temporal and snapshot.temporal.seasons else "unknown",
                                "timestamp": now.isoformat()
                            },
                            "weight": int(snapshot.patterns[0].confidence * 100) if snapshot.patterns else 50
                        })

        return edges

    def suggest_correlations(self, snapshots: List[CognitiveSnapshot]) -> List[Dict[str, Any]]:
        """
        Analisis beberapa snapshot dan beri saran korelasi.
        Contoh: "Setiap lokasi X NDVI turun, 2 minggu kemudian lokasi Y banjir."
        """
        suggestions = []
        by_location = {}

        for snap in snapshots:
            loc = snap.location or "unknown"
            by_location.setdefault(loc, []).append(snap)

        for loc, snaps in by_location.items():
            if len(snaps) < 2:
                continue
            ndvi_values = [s.metrics.get("ndvi") for s in snaps if s.metrics.get("ndvi")]
            if ndvi_values and all(v is not None for v in ndvi_values):
                if ndvi_values[-1] < ndvi_values[0]:
                    suggestions.append({
                        "pattern": "ndvi_decline",
                        "location": loc,
                        "description": f"NDVI di {loc} menurun dari {ndvi_values[0]:.2f} ke {ndvi_values[-1]:.2f}",
                        "confidence": 0.65
                    })

        return suggestions


# ============================================================
# MIGRATION HELPER
# ============================================================

def migrate_to_cognitive_memory(
    session_id: str,
    raw_result: Dict[str, Any],
    memory_store_fn: callable,
    extractor: TemporalPatternExtractor = None
) -> CognitiveSnapshot:
    """
    Main pipeline: Audit selesai → ekstrak snapshot → simpan ke memory store.

    Dipanggil setelah setiap audit selesai di orchestrator.
    """
    if extractor is None:
        extractor = TemporalPatternExtractor()

    snapshot = extractor.extract(raw_result, session_id)
    memory_store_fn(session_id, snapshot)

    return snapshot