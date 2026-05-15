"""
Session Summary Service — v3 (Precision & Cognitive Engine)
=========================================================
Sistem memori progresif berbasis Semantic Delta, Unresolved Questions, & Vibe Tracking.
Optimasi: Qwen3.5-Flash, Regex JSON Parser, Safe Truncation (1000 chars).
"""

import json
import httpx
import logging
import re
from datetime import datetime, timezone
from typing import List, Dict, Optional
from sqlalchemy.orm import Session as DBSession

from app.db.models import ChatMessage, ChatSession
from app.core.config import settings

logger = logging.getLogger(__name__)

class SessionSummaryService:
    # Threshold 20 pesan (10 turns) sinkron dengan short-term memory limit
    PROGRESSIVE_INTERVAL = 20 

    @staticmethod
    def _call_llm(prompt: str, max_tokens: int = 1500) -> str:
        """Internal LLM call via OpenRouter. Low temperature untuk ekstraksi data rigid."""
        try:
            response = httpx.post(
                f"{settings.OPENROUTER_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.CHAT_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2, 
                    "max_tokens": max_tokens,
                },
                timeout=45.0
            )
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"[SummaryService] LLM Call Failed: {e}")
            return ""

    @staticmethod
    def _parse_json_response(raw: str) -> Optional[Dict]:
        """Robust parser menggunakan Regex untuk bypass <think> tags atau text format."""
        try:
            clean = raw.strip()
            # Ekstrak valid JSON object bypass markdown/reasoning logs
            match = re.search(r'(\{.*\})', clean, re.DOTALL)
            if match:
                clean = match.group(1)
            return json.loads(clean)
        except Exception as e:
            logger.warning(f"[SummaryService] Failed parsing JSON: {e}")
            return None

    @staticmethod
    def _format_conversation(messages: List[ChatMessage], limit: int = 20) -> str:
        """Format history dengan Safe Truncation (1000 chars) untuk presisi akademik."""
        lines = []
        for msg in messages[-limit:]:
            role = "Siswa" if msg.role == "user" else "Armisa"
            # 1000 chars menjamin rumus matematika/konteks krusial tidak terpotong
            content = msg.content[:1000].replace("\n", " ")
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    @staticmethod
    def _save_to_db(session_id: str, summary_dict: Dict, db: DBSession):
        """Persist summary & Auto-sync session title untuk sidebar UI."""
        session = db.query(ChatSession).filter(ChatSession.id == str(session_id)).first()
        if session:
            session.summary = json.dumps(summary_dict)
            session.summary_updated_at = datetime.now(timezone.utc)
            
            # SESSION TITLE SYNC: Update sidebar otomatis
            new_title = summary_dict.get("session_name")
            if new_title and len(new_title.strip()) > 3:
                session.title = new_title.strip()
            
            db.commit()

    @staticmethod
    def build_session_summary(session_id: str, messages: List[ChatMessage], db: DBSession) -> Dict:
        """Inisialisasi metadata sesi pertama kali (First Contact Analysis)."""
        if not messages: return {}
        
        conversation_text = SessionSummaryService._format_conversation(messages, limit=50)
        total_msgs = len(messages)

        prompt = f"""Kamu adalah sistem analisa metadata Sismind.id.
            Buat profil awal sesi belajar ini secara mendalam.

            === PERCAKAPAN BELAJAR ===
            {conversation_text}
            
            OUTPUT WAJIB JSON:
            {{
                "session_name": "Judul natural 2-5 kata",
                "learning_vibe": "focused | frustrated | curious | confused",
                "topics_discussed": ["topik spesifik"],
                "mastery_per_topic": {{"topik": 1.0-5.0}},
                "gaps": [{{ "topic": "string", "severity": "high/medium/low" }}],
                "unresolved_questions": ["daftar pertanyaan menggantung"],
                "recommendations": ["max 3 saran konkret"]
            }}"""

        raw = SessionSummaryService._call_llm(prompt)
        result = SessionSummaryService._parse_json_response(raw)

        if result:
            result.update({
                "session_id": str(session_id),
                "message_count": total_msgs,
                "generated_at": datetime.now(timezone.utc).isoformat()
            })
            SessionSummaryService._save_to_db(session_id, result, db)
            return result
        return {}

    @staticmethod
    def update_progressive_summary(session_id: str, all_messages: List[ChatMessage], db: DBSession) -> Dict:
        """
        Progressive Engine: Melacak Semantic Delta, hutang konteks, dan Vibe.
        """
        if not all_messages: return {}

        session = db.query(ChatSession).filter(ChatSession.id == str(session_id)).first()
        old_summary = json.loads(session.summary) if session and session.summary else None

        # Fallback ke build jika data lama korup atau belum ada
        if not old_summary:
            return SessionSummaryService.build_session_summary(session_id, all_messages, db)

        # Delta context: 20 pesan terbaru
        new_convo = SessionSummaryService._format_conversation(all_messages, limit=20)
        total_msgs = len(all_messages)

        prompt = f"""Kamu adalah sistem metadata Sismind.id. 
        Update summary berdasarkan DELTA (perubahan) terbaru dari interaksi Siswa.

        === CURRENT STATE (Summary Lama) ===
        {json.dumps(old_summary)}

        === NEW DELTA (Percakapan Terbaru) ===
        {new_convo}

        INSTRUKSI SEMANTIC DELTA:
        1. **Tracking Progress**: Cek jika Siswa sudah paham topik di 'gaps'. Jika iya, naikkan 'mastery' dan hapus dari 'gaps'.
        2. **Unresolved**: Update 'unresolved_questions'. Hapus jika Armisa sudah menjawab, tambah jika ada pertanyaan baru.
        3. **Vibe**: Deteksi 'learning_vibe' terkini (focused/frustrated/curious/confused).
        4. **Evolution**: Update 'session_name' jika fokus diskusi bergeser.

        OUTPUT WAJIB JSON (Struktur konsisten dengan summary lama).
        Pastikan output valid JSON object."""

        raw = SessionSummaryService._call_llm(prompt)
        result = SessionSummaryService._parse_json_response(raw)

        if result:
            result.update({
                "session_id": str(session_id),
                "message_count": total_msgs,
                "generated_at": datetime.now(timezone.utc).isoformat()
            })
            SessionSummaryService._save_to_db(session_id, result, db)
            return result
        
        return old_summary

    @staticmethod
    def get_context_for_prompt(session_id: str, db: DBSession) -> Optional[str]:
        """Injeksi long-term context ke System Prompt Armisa."""
        session = db.query(ChatSession).filter(ChatSession.id == str(session_id)).first()
        if not session or not session.summary: return None

        try:
            s = json.loads(session.summary)
            vibe = s.get("learning_vibe", "neutral")
            unresolved = "\n".join([f"  - {q}" for q in s.get("unresolved_questions", [])])
            gaps = ", ".join([g["topic"] for g in s.get("gaps", [])])
            
            return (
                f"[LONG-TERM MEMORY]\n"
                f"- User Vibe: {vibe.upper()}\n"
                f"- Topik Dikuasai: {', '.join(s.get('topics_discussed', []))}\n"
                f"- Kelemahan (Gaps): {gaps if gaps else 'Belum terdeteksi'}\n"
                f"- Unresolved Questions:\n{unresolved if unresolved else '  - Nihil'}\n"
                f"→ Sesuaikan tone dengan Vibe user. Prioritaskan Unresolved Questions jika relevan."
            )
        except Exception:
            return None