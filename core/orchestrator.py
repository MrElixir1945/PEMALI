import json
import asyncio
import httpx
import datetime
import os
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from core.database import SessionLocal, AgentMemory, AuditLog
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

    async def _run_tool(self, client: httpx.AsyncClient, tool_name: str, params: Dict) -> Dict:
        """Jalankan satu tool, return hasilnya."""
        print(f"[Orchestrator] ⚙ Tool: {tool_name}")
        try:
            r = await client.post(
                f"{API_BASE}/execute",
                json={"session_id": self.session_id, "tool_name": tool_name, "parameters": params},
                timeout=20
            )
            data = r.json()
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

    def _extract_location(self, prompt: str) -> str:
        """Simple extraction of location from prompt."""
        keywords = ["di ", "kawasan ", "wilayah ", "daerah ", "lokasi "]
        for kw in keywords:
            if kw in prompt.lower():
                idx = prompt.lower().index(kw) + len(kw)
                return prompt[idx:idx+50].strip().rstrip(".,")
        return prompt[:50]

    async def run(self, prompt: Optional[str] = None):
        db = SessionLocal()
        try:
            # Save user message
            if prompt:
                self._save(db, "user", prompt)
                # Quick ack to user
                ack = f"Baik, saya akan melakukan audit di lokasi yang disebutkan. Mengumpulkan data satelit dan informasi publik..."
                self._save(db, "assistant", ack)

            location = self._extract_location(prompt or "Bali")

            # ═══════════════════════════════════════
            # FASE 1: Jalankan SEMUA tools PARALEL
            # ═══════════════════════════════════════
            async with httpx.AsyncClient() as client:
                print("[Orchestrator] Phase 1: Running all data tools in PARALLEL...")
                satellite_task = self._run_tool(client, "satellite_audit", {
                    "lokasi": location, "koordinat": "", "periode_bulan": 12
                })
                osint_task = self._run_tool(client, "osint_intel", {
                    "query": f"{location} alih fungsi lahan lingkungan",
                    "lokasi": location,
                    "max_artikel": 10
                })
                community_task = self._run_tool(client, "community_engagement", {
                    "lokasi": location,
                    "fokus_analisis": "subak dan alih fungsi lahan"
                })

                # All 3 run at the same time!
                sat_data, osint_data, comm_data = await asyncio.gather(
                    satellite_task, osint_task, community_task
                )
                print("[Orchestrator] Phase 1 complete — all data collected")

                # ═══════════════════════════════════════
                # FASE 2: Satu AI call untuk tulis laporan
                # ═══════════════════════════════════════
                print("[Orchestrator] Phase 2: AI writing final report...")

                report_prompt = f"""Kamu adalah PEMALI AI, auditor ekologi otonom berbasis Tri Hita Karana.

Data audit untuk lokasi **{location}** telah dikumpulkan:

### Data Satelit Sentinel-2:
{json.dumps(sat_data, indent=2, ensure_ascii=False)[:2000]}

### Data OSINT & Berita:
{json.dumps(osint_data, indent=2, ensure_ascii=False)[:1500]}

### Data Keterlibatan Komunitas:
{json.dumps(comm_data, indent=2, ensure_ascii=False)[:1000]}

Tulis LAPORAN AUDIT KOMPREHENSIF dalam Bahasa Indonesia dengan format Markdown yang mencakup:

## I. RINGKASAN EKSEKUTIF
(2-3 paragraf ringkasan temuan kritis)

## II. PALEMAHAN (Hubungan Manusia – Alam)
### A. Analisis Citra Satelit (Sentinel-2)
(Tabel metrik: NDVI, konversi lahan, area terbangun)

## III. PAWONGAN (Hubungan Antar Manusia)
### A. Dinamika Sosial dari OSINT
(Tabel artikel berita + sentimen)
### B. Analisis Komunitas
(Tabel indikator keterlibatan)

## IV. PARAHYANGAN (Hubungan Manusia – Tuhan/Nilai Spiritual)
(Dimensi spiritual dari temuan)

## V. KESIMPULAN & REKOMENDASI
(Bullet points rekomendasi konkret + status prioritas)

Laporan harus otoritatif, ilmiah, dan berdasarkan data yang diberikan di atas."""

                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "Kamu adalah auditor ekologi ilmiah yang menulis laporan formal berdasarkan data yang diberikan. Selalu tulis dalam Bahasa Indonesia dengan format Markdown yang rapi."},
                        {"role": "user", "content": report_prompt}
                    ],
                    "max_tokens": 3000,
                    "temperature": 0.3
                }

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
                    ndvi = sat_inner.get("ndvi_mean", 0.4) if isinstance(sat_inner, dict) else 0.4
                    thk = "Palemahan" if ndvi < 0.5 else "Pawongan"
                    issue = sat_inner.get("issue_type", "Alih Fungsi Lahan") if isinstance(sat_inner, dict) else "Alih Fungsi Lahan & Konflik Sosial-Ekologis"

                # Save narrative to memory
                self._save(db, "assistant", narrative)

                # ═══════════════════════════════════════
                # FASE 3: Simpan ke DB langsung
                # ═══════════════════════════════════════
                self._save_audit_log(db, location, issue, narrative, thk)

                return narrative

        except Exception as e:
            print(f"[Orchestrator] Fatal Error: {e}")
            import traceback
            traceback.print_exc()
            return f"Error sistem: {e}"
        finally:
            db.close()
