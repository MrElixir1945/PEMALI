import json
import asyncio
import httpx
import datetime
import os
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from core.database import SessionLocal, AgentMemory, AuditLog
from core.registry import registry
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_URL = os.getenv("OPENROUTER_URL", "https://openrouter.ai/api/v1/chat/completions")
API_BASE = os.getenv("API_BASE", "http://localhost:8000")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")

if not OPENROUTER_KEY:
    print("[Warning] OPENROUTER_KEY not found!")


class PemaliOrchestrator:
    def __init__(self, session_id: str, model: str = None):
        self.session_id = session_id
        self.model = model or OPENROUTER_MODEL
        print(f"[Orchestrator] Session: {self.session_id} | Model: {self.model}")
        self.headers = {
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://pemali.id",
            "X-Title": "PEMALI Audit Platform"
        }

    def _save(self, db: Session, role: str, content: str, name: str = None):
        db.add(AgentMemory(session_id=self.session_id, role=role, content=content, name=name))
        db.commit()

    async def _run_tool(self, tool_name: str, params: Dict) -> Dict:
        """Jalankan satu tool secara langsung via registry."""
        print(f"[Orchestrator] ⚙ Tool: {tool_name}")
        try:
            result = await registry.execute_tool(
                tool_name, 
                params, 
                session_id=self.session_id
            )
            # Convert ModuleOutput to dict for consistency with Phase 2 logic
            data = result.model_dump()
            print(f"[Orchestrator] ✓ Done: {tool_name}")
            return data
        except Exception as e:
            print(f"[Orchestrator] ✗ Failed: {tool_name} — {e}")
            return {"status": "error", "tool": tool_name, "error": str(e)}

    def _save_audit_log(self, db: Session, location: str, issue: str, narrative: str, thk: str):
        """Langsung simpan AuditLog ke DB."""
        try:
            log = AuditLog(
                session_id=self.session_id,
                location=location,
                issue_type=issue,
                narrative_report=narrative,
                thk_alignment=thk,
                metadata_json={"source": "PEMALI_Direct_Pipeline"}
            )
            db.add(log)
            db.commit()
            print(f"[Orchestrator] ✅ AuditLog saved: id={log.id}")
            return log.id
        except Exception as e:
            print(f"[Orchestrator] ✗ AuditLog save failed: {e}")
            db.rollback()
            return None

    async def _analyze_intent(self, prompt: str) -> Dict[str, Any]:
        """Gunakan AI untuk menentukan apakah user ingin audit atau hanya menyapa."""
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system", 
                    "content": (
                        "You are the PEMALI Intent Engine. Analyze the user's input for an environmental audit platform in Bali.\n"
                        "Return ONLY a clean JSON object with this structure:\n"
                        "{\n"
                        "  \"intent\": \"audit\" | \"greeting\" | \"vague\",\n"
                        "  \"location\": \"string (name of area in Bali) or null\",\n"
                        "  \"focus\": \"string (e.g., water quality, land conversion) or null\",\n"
                        "  \"fast_reply\": \"string (a warm, professional greeting in Indonesian) or null\"\n"
                        "}\n\n"
                        "Rules:\n"
                        "- If it's just a greeting (halo, hi), set intent: greeting.\n"
                        "- If it's an audit request without a clear location, set intent: vague.\n"
                        "- If it's an audit request with a location, set intent: audit.\n"
                        "- Fast_reply should be short, professional, and invite the user to specify a location if intent is not audit."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"}
        }
        async with httpx.AsyncClient() as client:
            try:
                res = await client.post(OPENROUTER_URL, headers=self.headers, json=payload, timeout=30)
                content = res.json()["choices"][0]["message"]["content"]
                # Robust parsing
                data = json.loads(content)
                if isinstance(data, list) and len(data) > 0:
                    data = data[0]
                return data
            except Exception as e:
                print(f"[Orchestrator] Intent Analysis Error: {e}")
                return {"intent": "audit", "location": None}

    def _extract_location(self, prompt: str) -> Optional[str]:
        """Simple extraction of location from prompt. Returns None if not found."""
        keywords = ["di ", "kawasan ", "wilayah ", "daerah ", "lokasi ", "kawasan "]
        lower_prompt = prompt.lower()
        for kw in keywords:
            if kw in lower_prompt:
                idx = lower_prompt.index(kw) + len(kw)
                return prompt[idx:idx+40].strip().rstrip(".,")
        return None

    async def run(self, prompt: Optional[str] = None):
        db = SessionLocal()
        try:
            if not prompt: return "Prompt kosong."
            self._save(db, "user", prompt)

            # ═══════════════════════════════════════
            # FASE 0: Analisis Niat (Intent Analysis)
            # ═══════════════════════════════════════
            print(f"[Orchestrator] Phase 0: Analyzing intent for '{prompt[:20]}...'")
            intent_data = await self._analyze_intent(prompt)
            
            intent = intent_data.get("intent", "audit")
            location = intent_data.get("location") or self._extract_location(prompt)

            # Strict check: if it's a greeting or location is empty/junk, ask for clarification
            is_junk_location = location and location.lower() in ["halo", "hi", "hello", "p", "test", "bro"]
            
            if intent in ["greeting", "vague"] or not location or is_junk_location:
                reply = intent_data.get("fast_reply")
                if not reply:
                    reply = "Halo. Saya adalah PEMALI, asisten audit ekologi Anda. Di kawasan mana di Bali Anda ingin saya melakukan pemantauan hari ini?"
                
                self._save(db, "assistant", reply)
                return reply

            # Jika niatnya audit dan lokasi ada, lanjut ke pipeline
            self._save(db, "system", "intent_analyzed", name="orchestrator")
            
            # PENTING: Simpan entri awal ke AuditLog agar muncul di History Sidebar seketika
            self._save_audit_log(db, location, "Audit Sedang Berjalan", "Menunggu konfirmasi rencana...", "Pending")
            
            # ═══════════════════════════════════════
            # FASE 0.5: Planning & Approval
            # ═══════════════════════════════════════
            
            # Check if we already sent a plan and user is confirming
            last_assistant_mem = db.query(AgentMemory).filter(
                AgentMemory.session_id == self.session_id, 
                AgentMemory.role == "assistant"
            ).order_by(AgentMemory.id.desc()).first()
            
            is_confirmation = any(word in prompt.lower() for word in ["setuju", "lanjut", "gas", "ok", "oke", "ya", "yes", "boleh"])
            has_plan_sent = last_assistant_mem and "PROTOKOL AUDIT" in last_assistant_mem.content.upper()

            if not has_plan_sent:
                print(f"[Orchestrator] Proposing plan for {location}...")
                plan_msg = (
                    f"Saya telah merancang **PROTOKOL AUDIT** untuk kawasan **{location}**.\n\n"
                    "Strategi pemantauan mencakup:\n"
                    "1. **Analisis Spasial**: Deteksi tutupan lahan & indeks vegetasi via Sentinel-2.\n"
                    "2. **Intelijen Media**: Penelusuran isu lingkungan & berita lokal terkini.\n"
                    "3. **Audit Sosial**: Evaluasi kearifan lokal & partisipasi komunitas.\n"
                    "4. **Sintesis THK**: Penyusunan laporan komprehensif berbasis Tri Hita Karana.\n\n"
                    "Apakah Anda memberikan otorisasi untuk memulai proses ini?"
                )
                
                self._save(db, "assistant", plan_msg)
                return plan_msg

            if has_plan_sent and not is_confirmation:
                reply = "Menunggu otorisasi. Silakan ketik **'Setuju'** atau **'Lanjutkan'** untuk memicu eksekusi modul teknis."
                self._save(db, "assistant", reply)
                return reply

            # If we are here, it means we have a plan sent AND user confirmed
            ack = f"Otorisasi diterima. Memulai sinkronisasi data untuk **{location}**..."
            self._save(db, "assistant", ack)

            # ═══════════════════════════════════════
            # FASE 1: Jalankan SEMUA tools PARALEL
            # ═══════════════════════════════════════
            # Save "started" state for UI
            self._save(db, "tool", "started", name="satellite_audit")
            self._save(db, "tool", "started", name="osint_intel")
            self._save(db, "tool", "started", name="community_engagement")

            print("[Orchestrator] Phase 1: Running all data tools in PARALLEL (Direct Call)...")
            satellite_task = self._run_tool("satellite_audit", {
                "lokasi": location, "koordinat": "", "periode_bulan": 12
            })
            osint_task = self._run_tool("osint_intel", {
                "query": f"{location} alih fungsi lahan lingkungan",
                "lokasi": location,
                "max_artikel": 10
            })
            community_task = self._run_tool("community_engagement", {
                "lokasi": location,
                "fokus_analisis": "subak dan alih fungsi lahan"
            })

            # All 3 run at the same time!
            sat_data, osint_data, comm_data = await asyncio.gather(
                satellite_task, osint_task, community_task
            )
            
            # Save "done" state for UI
            self._save(db, "tool", json.dumps(sat_data), name="satellite_audit")
            self._save(db, "tool", json.dumps(osint_data), name="osint_intel")
            self._save(db, "tool", json.dumps(comm_data), name="community_engagement")

            print("[Orchestrator] Phase 1 complete — all data collected")

            # ═══════════════════════════════════════
            # FASE 2: Satu AI call untuk tulis laporan
            # ═══════════════════════════════════════
            self._save(db, "tool", "started", name="reporting_mod")
            print("[Orchestrator] Phase 2: AI writing final report...")

            report_prompt = f"""You are PEMALI AI, a high-authority Autonomous Ecological Auditor.
Write a COMPREHENSIVE AUDIT REPORT for **{location}** based on the following verified datasets:

[SATELLITE DATA]:
{json.dumps(sat_data, indent=2, ensure_ascii=False)}

[OSINT DATA]:
{json.dumps(osint_data, indent=2, ensure_ascii=False)}

[COMMUNITY DATA]:
{json.dumps(comm_data, indent=2, ensure_ascii=False)}

Report Structure (Use Markdown):
# FINAL AUDIT REPORT: {location.upper()}

## I. EXECUTIVE SUMMARY
(Otoritatif, ringkas, dan tajam)

## II. PALEMAHAN (Environmental Integrity)
(Analisis perubahan lahan, NDVI, dan status ekosistem)

## III. PAWONGAN (Social & Community Dynamics)
(Analisis sentimen berita dan keterlibatan masyarakat)

## IV. PARAHYANGAN (Spiritual & Cultural Value)
(Bagaimana temuan ini berdampak pada nilai kearifan lokal/THK)

## V. AUDITOR'S CONCLUSION & DIRECTIVES
(Kesimpulan final dan rekomendasi strategis)

Language: Indonesian. 
Tone: Scientific, Professional, Decisive."""

            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "Kamu adalah auditor ekologi ilmiah yang menulis laporan formal berdasarkan data yang diberikan. Selalu tulis dalam Bahasa Indonesia dengan format Markdown yang rapi."},
                    {"role": "user", "content": report_prompt}
                ],
                "max_tokens": 3000,
                "temperature": 0.3
            }

            print(f"[Orchestrator] AI is reasoning and writing the audit report for {location} using model {self.model}...")

            async with httpx.AsyncClient() as client:
                res_raw = await client.post(
                    OPENROUTER_URL,
                    headers=self.headers,
                    json=payload,
                    timeout=120
                )
                res = res_raw.json()

            if "error" in res:
                print(f"[Orchestrator] API Error: {res['error']}")
                narrative = f"Error dari AI: {res['error'].get('message', 'Unknown')}"
                thk = "Palemahan"
                issue = "Error Sistem"
            elif "choices" not in res:
                narrative = "Gagal mendapatkan respons dari AI."
                thk = "Palemahan"
                issue = "Error Sistem"
            else:
                narrative = res["choices"][0]["message"]["content"]
                print(f"[Orchestrator] ✓ Report generated ({len(narrative)} chars)")

                # Determine THK and issue from satellite data
                sat_inner = sat_data.get("data", sat_data) if isinstance(sat_data, dict) else {}
                ndvi = sat_inner.get("ndvi", {}).get("rata_rata", 0.4) if isinstance(sat_inner, dict) else 0.4
                thk = "Palemahan" if ndvi < 0.5 else "Pawongan"
                issue = sat_inner.get("tutupan_lahan", {}).get("perubahan_pct", 0)
                issue_type = "Alih Fungsi Lahan" if issue > 5 else "Konservasi"

            # Save narrative to memory
            self._save(db, "assistant", narrative)
            self._save(db, "tool", "done", name="reporting_mod")

            # ═══════════════════════════════════════
            # FASE 3: Simpan ke DB langsung
            # ═══════════════════════════════════════
            self._save_audit_log(db, location, issue_type if 'issue_type' in locals() else "Audit Lingkungan", narrative, thk)

            return narrative

        except Exception as e:
            print(f"[Orchestrator] Fatal Error: {e}")
            import traceback
            traceback.print_exc()
            return f"Error sistem: {e}"
        finally:
            db.close()
