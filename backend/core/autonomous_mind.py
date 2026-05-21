"""
Agent Otak — Strategic Environmental Reasoning Engine.

Bangun → refleksi evaluasi diri → tentukan N kasus audit →
spawn Agent Run per kasus (paralel, sorted by priority) →
aggregate cross-case overview → self-schedule next wake.
"""

import asyncio
import datetime
import json
import logging
import os

import httpx
import time
import uuid
from typing import List, Dict, Any

from backend.core.models import CaseIntent, TelemetryEvent, NodeState
from backend.core.telemetry import telemetry
from backend.core.llm_client import get_llm_client, OPENROUTER_MODEL
from backend.core.memory import (
    query_semantic,
    query_memory_graph_for_context,
    query_semantic_scoped,
    store_semantic_memory,
)
from backend.core.database import SessionLocal, AutonomousTask, AuditLog
from backend.core.orchestrator import PemaliOrchestrator, _sanitize_messages

logger = logging.getLogger("PEMALI.AutonomousMind")

MAX_PARALLEL_RUNNERS = 3

BALI_REGIONS = [
    {"name": "Denpasar", "lat": -8.65, "lon": 115.22},
    {"name": "Badung", "lat": -8.58, "lon": 115.17},
    {"name": "Gianyar", "lat": -8.54, "lon": 115.32},
    {"name": "Tabanan", "lat": -8.54, "lon": 115.12},
    {"name": "Klungkung", "lat": -8.53, "lon": 115.40},
    {"name": "Karangasem", "lat": -8.47, "lon": 115.61},
    {"name": "Buleleng", "lat": -8.11, "lon": 115.09},
    {"name": "Jembrana", "lat": -8.38, "lon": 114.67},
    {"name": "Bangli", "lat": -8.45, "lon": 115.36},
]

DEFAULT_OSINT_KEYWORDS = [
    "kebakaran hutan Bali",
    "banjir Bali",
    "polusi udara Bali",
    "kekeringan Bali",
    "longsor Bali",
]

# ── Agent Otak system prompt ──────────────────────────────────
OTAK_SYSTEM_PROMPT = """Kamu adalah AGENT OTAK — strategic environmental reasoning engine untuk audit Bali.

Kamu baru bangun dari jadwal pemantauan rutin. Tugasmu BUKAN menjalankan audit — tugasmu MEMUTUSKAN apa yang harus diaudit.

EVALUASI DIRI SIKLUS LALU:
{evaluation_context}

MEMORY CONTEXT:
{memory_context}

SCAN DATA — KONDISI TERKINI:
{scan_result}

SCAN DATA — OSINT TRENDS:
{osint_result}

TUGAS WAJIB:
1. BACA dan ANALISA SCAN DATA di atas — data real-time dari 9 kabupaten + OSINT trends
2. CARI pattern: cross-reference antar region (contoh: suhu tinggi + hotspot = potensi kebakaran)
3. BANDINGKAN current vs history — deteksi anomali
4. PUTUSKAN — tentukan kasus audit SEKARANG. Gunakan tool decide_cases dengan minimal 1 kasus.

5. PRIORITASKAN & VARIASIKAN:
   - Priority 10 = darurat (anomali kritis), 1 = rutin belaka
   - JANGAN ulangi area/lokasi yang sama dengan siklus sebelumnya
   - Variasikan tipe isu: air, lahan, kebakaran, pesisir, mangrove, sosial, subak
   - Prioritaskan kabupaten yang BELUM diaudit dalam 7 hari terakhir
   - Jika tidak ada anomali baru, pilih monitoring rutin di area berbeda
   - Jangan buat lebih dari 5 kasus per siklus

6. KAMU TIDAK MENJALANKAN AUDIT. Agent Run akan menjalankan tiap kasus.

7. SETELAH SELESAI — gunakan tool schedule_next_wake untuk menentukan kapan bangun lagi,
   berdasarkan hasil evaluasi dan kondisi terkini."""


# ── Agent Run system prompt (injected into orchestrator) ──────

# ── Tools ─────────────────────────────────────────────────────

DECIDE_CASES_TOOL = {
    "type": "function",
    "function": {
        "name": "decide_cases",
        "description": "Tentukan kasus-kasus audit yang harus dijalankan sekarang, beserta prioritasnya.",
        "parameters": {
            "type": "object",
            "properties": {
                "cases": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "case_id": {"type": "string", "description": "ID unik, e.g. case-001"},
                            "title": {"type": "string", "description": "Judul singkat kasus (maks 80 karakter)"},
                            "intent": {"type": "string", "description": "Instruksi lengkap untuk Agent Run — detail, spesifik, lokasi, metrik"},
                            "priority": {"type": "integer", "minimum": 1, "maximum": 10},
                            "urgency_reason": {"type": "string", "description": "Kenapa prioritas segitu?"}
                        },
                        "required": ["case_id", "title", "intent", "priority", "urgency_reason"]
                    }
                }
            },
            "required": ["cases"]
        }
    }
}

EVALUATE_PAST_CYCLE_TOOL = {
    "type": "function",
    "function": {
        "name": "evaluate_past_cycle",
        "description": "Refleksi diri — evaluasi apakah keputusan siklus sebelumnya sudah tepat.",
        "parameters": {
            "type": "object",
            "properties": {
                "was_decision_correct": {
                    "type": "boolean",
                    "description": "Apakah mayoritas keputusan siklus lalu benar?"
                },
                "priority_accuracy": {
                    "type": "integer", "minimum": 1, "maximum": 10,
                    "description": "Seberapa akurat prioritas yang diberikan? 10 = sangat tepat"
                },
                "unexpected_findings": {
                    "type": "string",
                    "description": "Temuan tak terduga dari siklus lalu"
                },
                "strategy_adjustments": {
                    "type": "string",
                    "description": "Apa yang harus diubah dalam strategi pemantauan ke depan?"
                },
                "confidence": {
                    "type": "integer", "minimum": 1, "maximum": 10,
                    "description": "Seberapa yakin dengan strategi saat ini? 10 = sangat yakin"
                }
            },
            "required": ["was_decision_correct", "priority_accuracy", "strategy_adjustments", "confidence"]
        }
    }
}

SCHEDULE_NEXT_WAKE_TOOL = {
    "type": "function",
    "function": {
        "name": "schedule_next_wake",
        "description": "Tentukan kapan Agent Otak harus bangun lagi untuk siklus berikutnya.",
        "parameters": {
            "type": "object",
            "properties": {
                "interval_minutes": {
                    "type": "integer", "minimum": 30, "maximum": 1440,
                    "description": "Interval dalam menit sebelum bangun lagi (30 menit - 24 jam)"
                },
                "reason": {
                    "type": "string",
                    "description": "Kenapa interval ini dipilih? Kaitkan dengan temuan dan prioritas."
                }
            },
            "required": ["interval_minutes", "reason"]
        }
    }
}


class AutonomousMind:
    """Agent Otak — berpikir strategis, spawn Agent Run, self-schedule."""

    def __init__(self, trace_id: str):
        self.trace_id = trace_id
        self.started_at = time.time()
        self.evaluation = None
        self.last_cases = []
        self.scan_result: Dict[str, Any] = {}
        self.osint_result: Dict[str, Any] = {}

    async def wake(self, task_id: int, priority: int) -> Dict[str, Any]:
        """Entry point: bangun, evaluasi diri, pikir, jalankan, jadwalkan ulang."""
        logger.info(f"[AutonomousMind] Waking: trace_id={self.trace_id}, task_id={task_id}")
        await telemetry.emit(TelemetryEvent(
            trace_id=self.trace_id, node_id="agent_otak", node_type="Manager",
            state=NodeState.THINKING,
            narrative="Agent Otak bangun. Memuat memori dan mengevaluasi diri...",
            metadata={"phase": "loading", "task_type": "autonomous"}
        ))

        # 1. Load consciousness + past evaluation data
        memory, eval_context = await self._load_consciousness()

        # 2. REFLEKSI DIRI — evaluate past cycle
        await self._evaluate_past(eval_context)

        # 3. SCAN kondisi terkini (sebelum decide cases)
        await telemetry.emit(TelemetryEvent(
            trace_id=self.trace_id, node_id="agent_otak", node_type="Manager",
            state=NodeState.THINKING,
            narrative="Memindai kondisi lingkungan terkini 9 kabupaten Bali...",
            metadata={"phase": "scan", "scan_type": "current_conditions"}
        ))
        self.scan_result = await self._scan_current_conditions(history_days=7)

        await telemetry.emit(TelemetryEvent(
            trace_id=self.trace_id, node_id="agent_otak", node_type="Manager",
            state=NodeState.THINKING,
            narrative="Memindai tren OSINT lingkungan Bali...",
            metadata={"phase": "scan", "scan_type": "osint_trends"}
        ))
        self.osint_result = await self._scan_osint_trends()

        await telemetry.emit(TelemetryEvent(
            trace_id=self.trace_id, node_id="agent_otak", node_type="Manager",
            state=NodeState.THINKING,
            narrative="Menganalisis data scan dan memutuskan kasus audit...",
            metadata={"phase": "planning", "confidence": self.evaluation.get("confidence", 5) if self.evaluation else None}
        ))

        # 4. Decide cases (dengan scan context + diversity + reflection)
        cases = await self._decide_cases(memory, eval_context, self.scan_result, self.osint_result)

        self.last_cases = cases

        if not cases:
            logger.info("[AutonomousMind] No cases decided — self-scheduling with LLM")
            next_delay = await self._calculate_next_interval_llm(cases, {}, eval_context) or 720
            await self._schedule_next_wake(next_delay, task_id)
            return {"status": "idle", "cases": 0, "message": "Tidak ada kasus yang perlu diaudit."}

        # 5. Emit plan event with full context (for /agentic display)
        plan_metadata = {
            "phase": "plan",
            "phase_step": "decided",
            "case_count": len(cases),
            "cases": [
                {
                    "case_id": c.case_id,
                    "title": c.title,
                    "priority": c.priority,
                    "intent": c.intent,
                    "urgency_reason": c.urgency_reason,
                } for c in cases
            ],
            "scan_summary": self._build_scan_summary(self.scan_result, self.osint_result),
        }
        await telemetry.emit(TelemetryEvent(
            trace_id=self.trace_id, node_id="agent_otak", node_type="Manager",
            state=NodeState.THINKING,
            narrative=f"Memutuskan {len(cases)} kasus audit berdasarkan scan data terkini. Menjalankan Agent Run sesuai prioritas...",
            metadata=plan_metadata,
        ))

        # 6. Spawn Agent Run paralel
        results = await self._spawn_runners(cases)

        # 7. Aggregate overview
        overview = await self._synthesize_overview(cases, results)

        # 8. Self-schedule (LLM decided)
        next_delay = await self._calculate_next_interval_llm(cases, results, eval_context) or \
                      self._calculate_next_interval_fallback(cases, results)
        await self._schedule_next_wake(next_delay, task_id)

        # 9. Store evaluation for next cycle
        await self._store_evaluation(eval_context)

        elapsed = round(time.time() - self.started_at, 1)
        conf = self.evaluation.get("confidence", 5) if self.evaluation else "?"
        await telemetry.emit(TelemetryEvent(
            trace_id=self.trace_id, node_id="agent_otak", node_type="Manager",
            state=NodeState.DONE,
            narrative=f"Siklus otonom selesai. {len(cases)} kasus diaudit dalam {elapsed}s. Confidence: {conf}/10. Bangun lagi dalam {next_delay} menit.",
            metadata={"phase": "done", "type": "autonomous_cycle_complete",
                       "cases": len(cases), "duration_s": elapsed, "next_wake_minutes": next_delay,
                       "confidence": self.evaluation.get("confidence", 5) if self.evaluation else 5}
        ))

        return overview

    async def _load_consciousness(self):
        """Load memory: semantic + knowledge graph + recent logs + past evaluations."""
        parts = []
        eval_context = {}

        try:
            semantic_results = await asyncio.to_thread(
                query_semantic, "kondisi lingkungan Bali anomali kerusakan audit", 5
            )
            if semantic_results:
                parts.append("=== MEMORI SEMANTIK (ChromaDB) ===")
                for r in semantic_results:
                    parts.append(f"- {r['content'][:300]}")
        except Exception as e:
            logger.warning(f"[AutonomousMind] Semantic memory load failed: {e}")

        try:
            graph_context = await asyncio.to_thread(
                query_memory_graph_for_context, "Bali lingkungan audit", 5, 5
            )
            if graph_context:
                parts.append("=== KNOWLEDGE GRAPH (PostgreSQL) ===")
                parts.append(graph_context)
        except Exception as e:
            logger.warning(f"[AutonomousMind] Knowledge graph load failed: {e}")

        try:
            db = SessionLocal()
            try:
                # Recent autonomous tasks
                recent_tasks = db.query(AutonomousTask).filter(
                    AutonomousTask.status.in_(["completed", "failed"])
                ).order_by(AutonomousTask.id.desc()).limit(5).all()
                if recent_tasks:
                    parts.append("=== RIWAYAT TASK OTONOM ===")
                    for t in recent_tasks:
                        parts.append(f"- Task #{t.id}: status={t.status}, intent={t.intent_description[:100] if t.intent_description else '-'}")

                # Recent audit reports (topics, locations, priorities)
                recent_reports = db.query(AuditLog).filter(
                    AuditLog.source == "autonomous"
                ).order_by(AuditLog.id.desc()).limit(5).all()
                if recent_reports:
                    eval_context["last_cycle_cases"] = []
                    for r in recent_reports:
                        meta = r.metadata_json or {}
                        eval_context["last_cycle_cases"].append({
                            "title": r.title,
                            "priority": r.priority,
                            "location": r.location,
                            "anomalies": "anomali" in (r.narrative_report or "").lower(),
                            "sub_agents": meta.get("sub_agents", []),
                            "tool_success": meta.get("tool_success", 0),
                        })
                    # First report is last cycle
                    if eval_context["last_cycle_cases"]:
                        eval_context["last_cycle"] = eval_context["last_cycle_cases"][0]

                # Past self-evaluations from ChromaDB
                try:
                    evals = await asyncio.to_thread(
                        query_semantic_scoped, "self evaluation confidence", "otak-eval-latest", 2
                    )
                    if evals:
                        eval_context["past_evaluations"] = [e["content"][:500] for e in evals]
                except Exception:
                    pass
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"[AutonomousMind] DB load failed: {e}")

        return "\n\n".join(parts) if parts else "Belum ada memori. Ini adalah siklus pertama.", eval_context

    async def _evaluate_past(self, eval_context: dict):
        """Step 0: Refleksi diri — evaluasi keputusan siklus sebelumnya."""
        if not eval_context or not eval_context.get("last_cycle"):
            logger.info("[AutonomousMind] No past cycle to evaluate — first cycle")
            self.evaluation = {"confidence": 5, "is_first_cycle": True}
            return

        await telemetry.emit(TelemetryEvent(
            trace_id=self.trace_id, node_id="agent_otak", node_type="Manager",
            state=NodeState.THINKING,
            narrative="Mengevaluasi keputusan siklus sebelumnya...",
            metadata={"phase": "evaluation"}
        ))

        llm = get_llm_client()
        eval_prompt = f"""Evaluasi siklus audit otonom sebelumnya.

DATA SIKLUS LALU:
{json.dumps(eval_context, ensure_ascii=False, default=str)[:3000]}

Gunakan tool evaluate_past_cycle untuk mengevaluasi apakah keputusanmu sudah tepat."""

        for attempt in range(2):
            try:
                res = await llm.chat.completions.create(
                    model=OPENROUTER_MODEL,
                    messages=_sanitize_messages([
                        {"role": "system", "content": "Kamu adalah sistem evaluasi diri Agent Otak PEMALI."},
                        {"role": "user", "content": eval_prompt}
                    ]),
                    tools=[EVALUATE_PAST_CYCLE_TOOL],
                    tool_choice="auto",
                    max_tokens=2048,
                    timeout=60.0,
                )
                if not res or not res.choices:
                    raise ValueError(f"LLM response tanpa choices — res={res}")
                msg = res.choices[0].message
                if msg.tool_calls and msg.tool_calls[0].function.arguments:
                    self.evaluation = json.loads(msg.tool_calls[0].function.arguments)
                    logger.info(f"[AutonomousMind] Self-evaluation: confidence={self.evaluation.get('confidence')}")
                    await telemetry.emit(TelemetryEvent(
                        trace_id=self.trace_id, node_id="agent_otak", node_type="Manager",
                        state=NodeState.THINKING,
                        narrative=f"Refleksi: confidence {self.evaluation.get('confidence', '?')}/10. {self.evaluation.get('strategy_adjustments', '')[:150]}",
                        metadata={"phase": "evaluation", "evaluation": self.evaluation}
                    ))
                    return
            except Exception as e:
                logger.warning(f"[AutonomousMind] Evaluate attempt {attempt+1} failed: {e}")
                if attempt == 0:
                    await asyncio.sleep(1)

        self.evaluation = {"confidence": 5, "evaluation_failed": True}
        logger.warning("[AutonomousMind] Self-evaluation failed — using default confidence")

    async def _decide_cases(self, memory: str, eval_context: dict, scan_result: dict, osint_result: dict) -> List[CaseIntent]:
        """LLM strategic decision: tentukan kasus apa yang perlu diaudit."""
        llm = get_llm_client()
        eval_text = json.dumps(self.evaluation, ensure_ascii=False) if self.evaluation else "Siklus pertama — belum ada evaluasi."
        scan_text = json.dumps(scan_result, ensure_ascii=False, default=str)[:8000] if scan_result else "Tidak tersedia"
        osint_text = json.dumps(osint_result, ensure_ascii=False, default=str)[:5000] if osint_result else "Tidak tersedia"
        prompt = OTAK_SYSTEM_PROMPT.format(
            evaluation_context=eval_text,
            memory_context=memory,
            scan_result=scan_text,
            osint_result=osint_text,
        )

        for attempt in range(2):
            try:
                res = await llm.chat.completions.create(
                    model=OPENROUTER_MODEL,
                    messages=_sanitize_messages([
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": "Putuskan kasus audit yang harus dijalankan SEKARANG. WAJIB panggil tool decide_cases dengan minimal 1 kasus spesifik di Bali. Jangan skip tool ini. PENTING: Jangan ulangi kasus yang sudah diaudit di cycle sebelumnya — pilih region dan topik yang berbeda."}
                    ]),
                    tools=[DECIDE_CASES_TOOL],
                    tool_choice="auto",
                    max_tokens=2048,
                    timeout=90.0,
                )
                if not res or not res.choices:
                    raise ValueError(f"LLM response tanpa choices — res={res}")
                msg = res.choices[0].message

                cases = []
                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        if tc.function.name == "decide_cases" and tc.function.arguments:
                            parsed = json.loads(tc.function.arguments)
                            for c in parsed.get("cases", []):
                                cases.append(CaseIntent(**c))

                # Diversity filter: buang kasus yang terlalu mirip dengan cycle sebelumnya
                if cases and self.last_cases:
                    prev_titles = {c.title.lower().strip() for c in self.last_cases}
                    prev_intents = {c.intent.lower().strip()[:100] for c in self.last_cases}
                    filtered = []
                    for c in cases:
                        title_similar = any(c.title.lower().strip() in pt or pt in c.title.lower().strip() for pt in prev_titles)
                        intent_similar = any(c.intent.lower().strip()[:100] in pi or pi in c.intent.lower().strip()[:100] for pi in prev_intents)
                        if not (title_similar and intent_similar):
                            filtered.append(c)
                        else:
                            logger.info(f"[AutonomousMind] Filtered duplicate case: {c.title}")
                    cases = filtered

                if cases:
                    cases.sort(key=lambda x: x.priority, reverse=True)
                    logger.info(f"[AutonomousMind] Decided {len(cases)} cases: {[(c.case_id, c.priority) for c in cases]}")
                    return cases

                logger.warning(f"[AutonomousMind] Decide cases attempt {attempt+1} returned 0 cases")
            except Exception as e:
                logger.error(f"[AutonomousMind] Decide cases attempt {attempt+1} failed: {e}")
                if attempt == 0:
                    await asyncio.sleep(2)

        # Fallback: kalau LLM tetap skip/empty, generate 1 case default
        logger.warning("[AutonomousMind] LLM failed to decide cases — generating fallback case")
        return [CaseIntent(
            case_id=f"fallback-{int(time.time())}",
            title="Monitoring rutin lingkungan Bali",
            intent="Lakukan audit lingkungan untuk deteksi anomali di area yang belum pernah diaudit. Gunakan sensor NDVI, kualitas air, dan suhu permukaan.",
            priority=5,
            urgency_reason="Siklus otomatis — LLM tidak menghasilkan kasus, jalankan monitoring default.",
        )]


    # ═════════════════════════════════════════════════════════════
    # SCANNER — Real-time environmental conditions (9 regions)
    # ═════════════════════════════════════════════════════════════

    async def _scan_current_conditions(self, history_days: int = 7) -> Dict[str, Any]:
        """Scan real-time environmental conditions across 9 Bali regions.
        Direct API calls — no registry overhead, no SSE noise.
        Partial failure = return what succeeded + warnings."""
        start_time = time.time()
        logger.info(f"[AutonomousMind] Scanning current conditions: {len(BALI_REGIONS)} regions, {history_days}d history")

        results: Dict[str, Any] = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "region_count": len(BALI_REGIONS),
            "history_days": history_days,
        }
        api_status = {"total": 5, "success": 0, "failed": 0, "details": {}}

        # ── 1. WeatherAPI current (9 regions parallel) ──
        api_status["details"]["weatherapi"] = "pending"
        try:
            weather_key = os.environ.get("WEATHERAPI_KEY", "")
            if weather_key:
                async def fetch_weather(region: dict) -> dict:
                    url = f"http://api.weatherapi.com/v1/current.json?key={weather_key}&q={region['name']},Indonesia&aqi=yes"
                    async with httpx.AsyncClient() as c:
                        r = await c.get(url, timeout=10.0)
                        if r.status_code == 200:
                            d = r.json()["current"]
                            return {
                                "name": region["name"],
                                "temp_c": d["temp_c"],
                                "feelslike_c": d["feelslike_c"],
                                "humidity": d["humidity"],
                                "wind_kph": d["wind_kph"],
                                "wind_dir": d["wind_dir"],
                                "pressure_mb": d["pressure_mb"],
                                "precip_mm": d["precip_mm"],
                                "vis_km": d["vis_km"],
                                "uv": d["uv"],
                                "condition": d["condition"]["text"],
                                "aqi": d.get("air_quality", {}),
                            }
                        return {"name": region["name"], "error": f"HTTP {r.status_code}"}

                weather = await asyncio.gather(*[fetch_weather(r) for r in BALI_REGIONS], return_exceptions=True)
                weather_ok = [w for w in weather if isinstance(w, dict) and "error" not in w]
                weather_fail = [w for w in weather if isinstance(w, dict) and "error" in w]
                results["weather"] = {
                    "regions": {w["name"]: {k: v for k, v in w.items() if k != "name"} for w in weather_ok},
                    "_summary": {
                        "avg_temp": round(sum(w["temp_c"] for w in weather_ok) / len(weather_ok), 1) if weather_ok else None,
                        "max_temp": max(w["temp_c"] for w in weather_ok) if weather_ok else None,
                        "min_temp": min(w["temp_c"] for w in weather_ok) if weather_ok else None,
                        "regions_ok": len(weather_ok),
                        "regions_failed": len(weather_fail),
                    },
                    "_warning": f"{len(weather_fail)} region weather failed" if weather_fail else None,
                }
                api_status["details"]["weatherapi"] = "ok" if weather_ok else "partial"
                api_status["success"] += 1 if weather_ok else 0
                api_status["failed"] += 1 if not weather_ok else 0
            else:
                results["weather"] = {"_warning": "WEATHERAPI_KEY not set"}
                api_status["details"]["weatherapi"] = "no_key"
                api_status["failed"] += 1
        except Exception as e:
            results["weather"] = {"_warning": f"WeatherAPI error: {str(e)[:100]}"}
            api_status["details"]["weatherapi"] = f"error: {str(e)[:50]}"
            api_status["failed"] += 1

        # ── 2. Open-Meteo Historical (9 regions parallel) ──
        api_status["details"]["openmeteo_history"] = "pending"
        try:
            end = datetime.datetime.now()
            start = end - datetime.timedelta(days=history_days)

            async def fetch_history(region: dict) -> dict:
                url = (
                    f"https://archive-api.open-meteo.com/v1/archive"
                    f"?latitude={region['lat']}&longitude={region['lon']}"
                    f"&start_date={start.strftime('%Y-%m-%d')}&end_date={end.strftime('%Y-%m-%d')}"
                    f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
                    f"&timezone=Asia/Singapore"
                )
                async with httpx.AsyncClient() as c:
                    r = await c.get(url, timeout=15.0)
                    if r.status_code == 200:
                        d = r.json()["daily"]
                        return {
                            "name": region["name"],
                            "max_temps": d["temperature_2m_max"],
                            "min_temps": d["temperature_2m_min"],
                            "precip_sum": d["precipitation_sum"],
                            "days": len(d["time"]),
                        }
                    return {"name": region["name"], "error": f"HTTP {r.status_code}"}

            history = await asyncio.gather(*[fetch_history(r) for r in BALI_REGIONS], return_exceptions=True)
            hist_ok = [h for h in history if isinstance(h, dict) and "error" not in h]
            results["history"] = {
                "regions": {h["name"]: {k: v for k, v in h.items() if k != "name"} for h in hist_ok},
                "_summary": {
                    "period_days": history_days,
                    "regions_ok": len(hist_ok),
                    "regions_failed": len(BALI_REGIONS) - len(hist_ok),
                },
            }
            api_status["details"]["openmeteo_history"] = "ok" if hist_ok else "failed"
            api_status["success"] += 1 if hist_ok else 0
            api_status["failed"] += 0 if hist_ok else 1
        except Exception as e:
            results["history"] = {"_warning": f"Open-Meteo history error: {str(e)[:80]}"}
            api_status["details"]["openmeteo_history"] = f"error: {str(e)[:50]}"
            api_status["failed"] += 1

        # ── 3. NASA FIRMS fire hotspots ──
        api_status["details"]["nasa_firms"] = "pending"
        try:
            firms_key = os.environ.get("NASA_FIRMS_API_KEY", "")
            if firms_key:
                url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{firms_key}/MODIS_NRT/114.4,-8.9,115.8,-8.0/1"
                async with httpx.AsyncClient() as c:
                    r = await c.get(url, timeout=15.0)
                    if r.status_code == 200 and "Invalid" not in r.text:
                        lines = r.text.strip().split("\n")
                        hotspots = []
                        for line in lines[1:]:
                            parts = line.split(",")
                            if len(parts) >= 9:
                                hotspots.append({"lat": parts[0], "lon": parts[1], "confidence": parts[8]})
                        results["fire_hotspots"] = {
                            "count": len(hotspots),
                            "hotspots": hotspots[:10],
                            "status": "WASPADA" if hotspots else "Aman",
                        }
                        api_status["details"]["nasa_firms"] = "ok"
                        api_status["success"] += 1
                    else:
                        results["fire_hotspots"] = {"count": 0, "status": "unknown", "_warning": "API response invalid"}
                        api_status["details"]["nasa_firms"] = "invalid_response"
                        api_status["failed"] += 1
            else:
                results["fire_hotspots"] = {"_warning": "NASA_FIRMS_API_KEY not set"}
                api_status["details"]["nasa_firms"] = "no_key"
                api_status["failed"] += 1
        except Exception as e:
            results["fire_hotspots"] = {"_warning": f"NASA FIRMS error: {str(e)[:80]}"}
            api_status["details"]["nasa_firms"] = f"error: {str(e)[:50]}"
            api_status["failed"] += 1

        # ── 4. USGS earthquakes ──
        api_status["details"]["usgs"] = "pending"
        try:
            starttime = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
            url = (
                f"https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson"
                f"&starttime={starttime}&minmagnitude=2.5"
                f"&minlatitude=-10&maxlatitude=-6&minlongitude=113&maxlongitude=118"
            )
            async with httpx.AsyncClient() as c:
                r = await c.get(url, timeout=10.0)
                if r.status_code == 200:
                    features = r.json().get("features", [])
                    quakes = []
                    for f in features:
                        p = f["properties"]
                        coords = f["geometry"]["coordinates"]
                        quakes.append({
                            "place": p["place"],
                            "mag": p["mag"],
                            "time": datetime.datetime.fromtimestamp(p["time"] / 1000).isoformat(),
                            "depth_km": round(coords[2], 1),
                        })
                    results["earthquakes"] = {
                        "count_24h": len(quakes),
                        "latest": quakes[:5],
                        "max_magnitude": max(q["mag"] for q in quakes) if quakes else None,
                        "status": "WASPADA" if any(q["mag"] > 5.0 for q in quakes) else ("Informasi" if quakes else "Aman"),
                    }
                    api_status["details"]["usgs"] = "ok"
                    api_status["success"] += 1
                else:
                    results["earthquakes"] = {"_warning": f"USGS HTTP {r.status_code}"}
                    api_status["details"]["usgs"] = "http_error"
                    api_status["failed"] += 1
        except Exception as e:
            results["earthquakes"] = {"_warning": f"USGS error: {str(e)[:80]}"}
            api_status["details"]["usgs"] = f"error: {str(e)[:50]}"
            api_status["failed"] += 1

        # ── 5. OpenWeatherMap Air Quality (9 regions parallel) ──
        api_status["details"]["openweathermap_air"] = "pending"
        try:
            owm_key = os.environ.get("OPENWEATHER_API_KEY", "")
            if owm_key:
                async def fetch_air(region: dict) -> dict:
                    url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={region['lat']}&lon={region['lon']}&appid={owm_key}"
                    async with httpx.AsyncClient() as c:
                        r = await c.get(url, timeout=10.0)
                        if r.status_code == 200:
                            d = r.json()["list"][0]
                            comp = d["components"]
                            return {
                                "name": region["name"],
                                "aqi": d["main"]["aqi"],
                                "pm2_5": comp["pm2_5"],
                                "pm10": comp["pm10"],
                                "no2": comp["no2"],
                                "co": comp["co"],
                                "o3": comp["o3"],
                            }
                        return {"name": region["name"], "error": f"HTTP {r.status_code}"}

                air = await asyncio.gather(*[fetch_air(r) for r in BALI_REGIONS], return_exceptions=True)
                air_ok = [a for a in air if isinstance(a, dict) and "error" not in a]
                results["air_quality"] = {
                    "regions": {a["name"]: {k: v for k, v in a.items() if k != "name"} for a in air_ok},
                    "_summary": {
                        "avg_aqi": round(sum(a["aqi"] for a in air_ok) / len(air_ok), 1) if air_ok else None,
                        "worst_aqi": max(a["aqi"] for a in air_ok) if air_ok else None,
                        "worst_location": max(air_ok, key=lambda x: x["aqi"])["name"] if air_ok else None,
                        "regions_ok": len(air_ok),
                    },
                }
                api_status["details"]["openweathermap_air"] = "ok" if air_ok else "failed"
                api_status["success"] += 1 if air_ok else 0
                api_status["failed"] += 0 if air_ok else 1
            else:
                results["air_quality"] = {"_warning": "OPENWEATHER_API_KEY not set"}
                api_status["details"]["openweathermap_air"] = "no_key"
                api_status["failed"] += 1
        except Exception as e:
            results["air_quality"] = {"_warning": f"OWM air error: {str(e)[:80]}"}
            api_status["details"]["openweathermap_air"] = f"error: {str(e)[:50]}"
            api_status["failed"] += 1

        elapsed = round(time.time() - start_time, 1)
        results["_meta"] = {
            "elapsed_s": elapsed,
            "apis_success": api_status["success"],
            "apis_failed": api_status["failed"],
            "api_details": api_status["details"],
        }

        logger.info(f"[AutonomousMind] Scan complete: {api_status['success']}/5 APIs OK in {elapsed}s")
        return results

    # ═════════════════════════════════════════════════════════════
    # SCANNER — OSINT trends (via module)
    # ═════════════════════════════════════════════════════════════

    async def _scan_osint_trends(self) -> Dict[str, Any]:
        """Scan OSINT trends: generate keywords via LLM, call osint_trend_scanner module, return results.
        Fallback: hardcoded defaults if LLM fails."""
        logger.info("[AutonomousMind] Scanning OSINT trends...")
        start_time = time.time()

        # Generate keywords via LLM
        keywords = await self._generate_osint_keywords()

        # Call module via registry
        try:
            from backend.core.registry import registry

            result = await registry.execute_tool("osint_trend_scanner", {
                "keywords": keywords or DEFAULT_OSINT_KEYWORDS,
                "max_results_per_keyword": 3,
                "region": "Bali",
                "history_days": 7,
            })

            data = result.model_dump() if hasattr(result, "model_dump") else {}
            elapsed = round(time.time() - start_time, 1)
            data["_elapsed_s"] = elapsed
            logger.info(f"[AutonomousMind] OSINT scan complete: {len(data.get('data', {}).get('trends', []))} trends in {elapsed}s")
            return data

        except Exception as e:
            logger.warning(f"[AutonomousMind] OSINT scan failed: {e}")
            return {
                "_warning": f"OSINT scan unavailable: {str(e)[:100]}",
                "keywords_used": keywords or DEFAULT_OSINT_KEYWORDS,
                "trends": [],
                "analysis": {"overall_sentiment": "unknown", "urgency": "unknown"},
            }

    async def _generate_osint_keywords(self) -> List[str] | None:
        """Generate search keywords via LLM based on memory context."""
        try:
            llm = get_llm_client()
            res = await llm.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=_sanitize_messages([
                    {"role": "system", "content": "Generate 3-5 search keywords in Indonesian for current environmental issues in Bali. Return ONLY a JSON array of strings."},
                    {"role": "user", "content": f"Generate keywords based on evaluation context: {json.dumps(self.evaluation, ensure_ascii=False)[:500] if self.evaluation else 'First cycle'}"},
                ]),
                max_tokens=1024,
                timeout=20.0,
            )
            content = res.choices[0].message.content or ""
            # Try JSON parse
            try:
                parsed = json.loads(content)
                if isinstance(parsed, list) and all(isinstance(k, str) for k in parsed):
                    return parsed[:5]
            except json.JSONDecodeError:
                pass
            # Fallback: extract quoted strings
            import re
            found = re.findall(r'"([^"]+)"', content)
            if found:
                return found[:5]
        except Exception as e:
            logger.warning(f"[AutonomousMind] Keyword generation failed: {e}")

        return None  # caller will use DEFAULT_OSINT_KEYWORDS

    @staticmethod
    def _build_scan_summary(scan: Dict[str, Any], osint: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key metrics from scan data for telemetry plan event (avoid flooding SSE with raw data)."""
        summary: Dict[str, Any] = {}

        w = scan.get("weather", {}) if scan else {}
        ws = w.get("_summary", {}) if isinstance(w, dict) else {}
        if ws.get("regions_ok"):
            summary["weather"] = {
                "avg_temp": ws.get("avg_temp"),
                "max_temp": ws.get("max_temp"),
                "regions_ok": ws.get("regions_ok"),
                "regions_failed": ws.get("regions_failed"),
            }

        f = scan.get("fire_hotspots", {}) if scan else {}
        if isinstance(f, dict) and "count" in f:
            summary["fire_hotspots"] = {"count": f["count"], "status": f.get("status")}

        e = scan.get("earthquakes", {}) if scan else {}
        if isinstance(e, dict) and "count_24h" in e:
            summary["earthquakes"] = {"count_24h": e["count_24h"], "max_mag": e.get("max_magnitude")}

        a = scan.get("air_quality", {}) if scan else {}
        if isinstance(a, dict):
            aq = a.get("_summary", {})
            if aq:
                summary["air_quality"] = {"avg_aqi": aq.get("avg_aqi"), "worst_aqi": aq.get("worst_aqi"), "worst_location": aq.get("worst_location")}

        if osint:
            osint_data = osint.get("data", {}) if isinstance(osint, dict) else {}
            oa = osint_data.get("analysis", {}) if isinstance(osint_data, dict) else {}
            if oa:
                summary["osint_trends"] = {
                    "sentiment": oa.get("overall_sentiment"),
                    "urgency": oa.get("urgency"),
                    "keywords": osint_data.get("keywords_used", []),
                }

        return summary

    async def _build_case_memory(self, case: CaseIntent) -> str:
        """Build rich memory context untuk satu case — biar Agent Run paham kenapa dia dipilih."""
        parts = []
        if self.evaluation:
            parts.append(f"Evaluasi Agent Otak: {json.dumps(self.evaluation, ensure_ascii=False)[:500]}")

        # Semantic search scoped to case topic
        try:
            search_query = f"{case.title} {case.urgency_reason} Bali lingkungan"
            related = await asyncio.to_thread(query_semantic, search_query, 2)
            if related:
                parts.append("=== RIWAYAT TERKAIT ===")
                for r in related:
                    parts.append(f"- {r['content'][:300]}")
        except Exception:
            pass

        # Knowledge graph untuk isu terkait
        try:
            graph = await asyncio.to_thread(query_memory_graph_for_context, case.title, 3, 3)
            if graph:
                parts.append(f"=== KNOWLEDGE GRAPH TERKAIT ===\n{graph}")
        except Exception:
            pass

        # Parallel cases context
        if self.last_cases:
            others = [c for c in self.last_cases if c.case_id != case.case_id]
            if others:
                parts.append("=== KASUS PARALEL ===")
                for o in others:
                    parts.append(f"- {o.title} (P{o.priority}): {o.urgency_reason[:100]}")

        return "\n\n".join(parts) if parts else f"Dipilih karena: {case.urgency_reason}"

    async def _spawn_runners(self, cases: List[CaseIntent]) -> Dict[str, Any]:
        """Jalankan Agent Run paralel, max 3 sekaligus, sorted by priority."""
        sem = asyncio.Semaphore(MAX_PARALLEL_RUNNERS)
        results: Dict[str, Any] = {}

        async def run_one(c: CaseIntent):
            async with sem:
                session_id = f"auto-run-{c.case_id}-{int(time.time())}"
                logger.info(f"[AutonomousMind] Spawning Agent Run: {c.case_id} (P{c.priority}) — {c.title}")

                # Build rich memory for this case
                case_memory = await self._build_case_memory(c)
                strategic_context = f"Prioritas: {c.priority}/10. Alasan: {c.urgency_reason}."

                await telemetry.emit(TelemetryEvent(
                    trace_id=self.trace_id, node_id=f"agent_run_{c.case_id}", node_type="SubAgent",
                    state=NodeState.SPAWNING,
                    narrative=f"Agent Run memulai audit: {c.title} (Prioritas {c.priority})",
                    metadata={"case_id": c.case_id, "priority": c.priority, "title": c.title,
                               "session_id": session_id, "urgency_reason": c.urgency_reason}
                ))

                orchestrator = PemaliOrchestrator(session_id)
                # S5: Kirim clean intent (bukan full system prompt) sebagai prompt
                # Strategi context dikirim terpisah via set_autonomous_mode
                run_prompt = c.intent
                orchestrator.set_autonomous_mode(
                    memory_context=case_memory,
                    source="autonomous",
                    priority=c.priority,
                    case_title=c.title,
                    strategic_context=strategic_context,
                )

                try:
                    report = await orchestrator.run(run_prompt)
                    results[c.case_id] = {
                        "status": "success",
                        "report": report,
                        "title": c.title,
                        "priority": c.priority,
                    }
                    await telemetry.emit(TelemetryEvent(
                        trace_id=self.trace_id, node_id=f"agent_run_{c.case_id}", node_type="SubAgent",
                        state=NodeState.DONE,
                        narrative=f"Audit selesai: {c.title}",
                        metadata={"case_id": c.case_id, "title": c.title,
                                   "priority": c.priority, "report_length": len(report) if report else 0}
                    ))
                except Exception as e:
                    logger.error(f"[AutonomousMind] Agent Run {c.case_id} failed: {e}")
                    results[c.case_id] = {
                        "status": "error",
                        "error": str(e),
                        "title": c.title,
                        "priority": c.priority,
                    }
                    await telemetry.emit(TelemetryEvent(
                        trace_id=self.trace_id, node_id=f"agent_run_{c.case_id}", node_type="SubAgent",
                        state=NodeState.ERROR,
                        narrative=f"Agent Run gagal: {c.title} — {str(e)[:100]}",
                        metadata={"case_id": c.case_id, "title": c.title, "priority": c.priority}
                    ))

        await asyncio.gather(*[run_one(c) for c in cases], return_exceptions=True)
        return results

    async def _synthesize_overview(self, cases: List[CaseIntent], results: Dict[str, Any]) -> Dict[str, Any]:
        """Cross-case synthesis: overview dari semua kasus yang dijalankan."""
        success = sum(1 for r in results.values() if r.get("status") == "success")
        failed = sum(1 for r in results.values() if r.get("status") == "error")
        total = len(cases)

        overview = {
            "total_cases": total,
            "success": success,
            "failed": failed,
            "cases": [],
        }

        for c in cases:
            r = results.get(c.case_id, {})
            overview["cases"].append({
                "case_id": c.case_id,
                "title": c.title,
                "priority": c.priority,
                "status": r.get("status", "unknown"),
                "report_preview": (r.get("report", "") or "")[:200],
            })

        await telemetry.emit(TelemetryEvent(
            trace_id=self.trace_id, node_id="agent_otak", node_type="Manager",
            state=NodeState.THINKING,
            narrative=f"Agregasi: {success}/{total} kasus sukses. {failed} gagal.",
            metadata={"phase": "synthesis", "success": success, "failed": failed}
        ))

        return overview

    def _calculate_next_interval_fallback(self, cases: List[CaseIntent], results: Dict[str, Any]) -> int:
        """Fallback: tentukan interval jika LLM decide gagal."""
        if not cases:
            return 720
        has_critical = any(
            c.priority >= 8 and results.get(c.case_id, {}).get("status") != "error"
            for c in cases
        )
        has_anomaly = any(
            r.get("status") == "success"
            and any(kw in (r.get("report", "") or "").lower() for kw in ["kritis", "anomali", "berbahaya", "menurun drastis"])
            for r in results.values()
        )
        has_failures = any(r.get("status") == "error" for r in results.values())

        if has_critical or has_anomaly:
            return 120
        elif has_failures:
            return 180
        elif any(c.priority >= 7 for c in cases):
            return 240
        elif any(c.priority >= 5 for c in cases):
            return 360
        return 720

    async def _calculate_next_interval_llm(self, cases: List[CaseIntent], results: Dict[str, Any], eval_context: dict) -> int | None:
        """LLM memutuskan kapan bangun lagi — adaptive scheduling."""
        if not cases:
            return None

        llm = get_llm_client()
        context = {
            "cases_audited": [{"title": c.title, "priority": c.priority, "status": results.get(c.case_id, {}).get("status")} for c in cases],
            "evaluation": self.evaluation,
            "anomalies_found": sum(1 for r in results.values() if r.get("status") == "success"),
            "failures": sum(1 for r in results.values() if r.get("status") == "error"),
        }

        try:
            res = await llm.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=_sanitize_messages([
                    {"role": "system", "content": "Tentukan interval pemantauan berikutnya berdasarkan hasil audit."},
                    {"role": "user", "content": f"Berdasarkan hasil siklus ini:\n{json.dumps(context, ensure_ascii=False)[:2000]}\n\nGunakan tool schedule_next_wake."}
                ]),
                tools=[SCHEDULE_NEXT_WAKE_TOOL],
                tool_choice="auto",
                max_tokens=1024,
                timeout=30.0,
            )
            msg = res.choices[0].message
            if msg.tool_calls and msg.tool_calls[0].function.arguments:
                parsed = json.loads(msg.tool_calls[0].function.arguments)
                interval = parsed.get("interval_minutes", 360)
                reason = parsed.get("reason", "")
                logger.info(f"[AutonomousMind] LLM self-schedule: {interval} min — {reason}")
                return int(interval)
        except Exception as e:
            logger.warning(f"[AutonomousMind] LLM schedule_next_wake failed: {e}")

        return None

    async def _store_evaluation(self, eval_context: dict):
        """Simpan hasil evaluasi ke ChromaDB untuk siklus berikutnya."""
        if not self.evaluation:
            return
        try:
            text = f"Evaluasi siklus autonomous: {json.dumps(self.evaluation, ensure_ascii=False)}"
            await asyncio.to_thread(
                store_semantic_memory,
                "otak-eval-latest",
                text,
                {"type": "self_evaluation", "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()}
            )
        except Exception as e:
            logger.warning(f"[AutonomousMind] Store evaluation failed: {e}")

    async def _schedule_next_wake(self, delay_minutes: int, parent_task_id: int):
        """Insert autonomous task baru ke database untuk siklus berikutnya."""
        db = SessionLocal()
        try:
            execute_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=delay_minutes)
            next_task = AutonomousTask(
                task_type="autonomous",
                priority=7,
                execute_at=execute_at,
                intent_description=f"Siklus otonom lanjutan dari task #{parent_task_id}. Delay {delay_minutes} menit.",
                context_snapshot={
                    "parent_task_id": parent_task_id,
                    "trace_id": self.trace_id,
                    "confidence": self.evaluation.get("confidence", 5) if self.evaluation else 5,
                },
                status="pending",
            )
            db.add(next_task)
            db.commit()
            logger.info(f"[AutonomousMind] Self-scheduled: task #{next_task.id} in {delay_minutes} min at {execute_at.isoformat()}")
        except Exception as e:
            db.rollback()
            logger.error(f"[AutonomousMind] Self-schedule failed: {e}")
        finally:
            db.close()
