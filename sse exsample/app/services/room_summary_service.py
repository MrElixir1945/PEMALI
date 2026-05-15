"""
Room Summary Service — Longitudinal Memory
==========================================
Generate Armisa Insight yang ingat history belajar user.
Simpan ke room_insights table.

FIXES:
- ThreadPoolExecutor: tiap thread punya DB session sendiri (SQLAlchemy not thread-safe)
- Skip re-summary kalau session belum ada update baru sejak summary terakhir
"""

import json
import httpx
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.db.models import ChatSession, ChatMessage, RoomInsight
from app.services.session_summary_service import SessionSummaryService
from app.core.config import settings

STALE_DAYS = 3
TOP_N_SESSIONS = 10


class RoomSummaryService:

    # ================================================================
    # PRIVATE: LLM Call
    # ================================================================

    @staticmethod
    def _call_llm(prompt: str) -> str:
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
                    "temperature": 0.4,
                    "max_tokens": 600,
                },
                timeout=30.0
            )
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception:
            return ""

    # ================================================================
    # Smart selector — filter stale + top N
    # ================================================================

    @staticmethod
    def smart_select_sessions(
        all_sessions: List[ChatSession],
        db: Session
    ) -> List[ChatSession]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=STALE_DAYS)
        scored = []

        for session in all_sessions:
            last_msg = db.query(ChatMessage).filter(
                ChatMessage.session_id == session.id
            ).order_by(ChatMessage.created_at.desc()).first()

            if not last_msg:
                continue

            last_msg_time = last_msg.created_at
            if last_msg_time.tzinfo is None:
                last_msg_time = last_msg_time.replace(tzinfo=timezone.utc)

            if last_msg_time < cutoff:
                continue

            scored.append((session, last_msg_time))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [s for s, _ in scored[:TOP_N_SESSIONS]]

    # ================================================================
    # Cek apakah session punya pesan baru sejak summary terakhir
    # Kalau tidak ada pesan baru → skip re-summary untuk hemat token
    # ================================================================

    @staticmethod
    def _session_needs_summary(session: ChatSession, db: Session) -> bool:
        """
        Return True kalau session perlu di-summary ulang.
        
        Logic:
        - Belum pernah di-summary → True
        - summary_updated_at ada + tidak ada pesan baru sejak itu → False (skip)
        - Ada pesan baru sejak summary terakhir → True
        """
        if not session.summary or not session.summary_updated_at:
            return True

        summary_time = session.summary_updated_at
        if summary_time.tzinfo is None:
            summary_time = summary_time.replace(tzinfo=timezone.utc)

        # Cek apakah ada pesan baru setelah summary terakhir
        new_msg = db.query(ChatMessage).filter(
            ChatMessage.session_id == session.id,
            ChatMessage.created_at > summary_time
        ).first()

        return new_msg is not None

    # ================================================================
    # FIX UTAMA: process_session dengan DB session sendiri per thread
    # ================================================================

    @staticmethod
    def _process_session_in_thread(session_id: str, session_type: str, session_title: str, session_summary: Optional[str], session_summary_updated_at) -> Optional[Dict]:
        """
        Dijalankan di thread pool. Punya DB session sendiri — thread-safe.
        
        Kenapa pass primitive/string bukan object ChatSession?
        → SQLAlchemy objects tidak boleh di-pass antar thread karena
          mereka bound ke satu Session. Kita pass data primitive saja,
          lalu buka Session baru di dalam thread ini.
        """
        db = SessionLocal()
        try:
            # Re-query session object di thread ini dengan session baru
            session = db.query(ChatSession).filter(
                ChatSession.id == session_id
            ).first()

            if not session:
                return None

            # Ambil messages
            messages = db.query(ChatMessage).filter(
                ChatMessage.session_id == session_id
            ).order_by(ChatMessage.created_at.asc()).all()

            if not messages:
                return None

            # Cek apakah perlu di-summary ulang
            needs_summary = RoomSummaryService._session_needs_summary(session, db)

            summary = None
            if needs_summary:
                # Ada pesan baru atau belum pernah di-summary → generate fresh
                summary = SessionSummaryService.build_session_summary(session_id, messages, db)
            else:
                # Tidak ada update baru → pakai cache yang ada
                try:
                    summary = json.loads(session.summary)
                except Exception:
                    summary = {}

            if not summary:
                return None

            return {
                "session_id": session_id,
                "title": session_title or "Obrolan",
                "type": session_type,
                "messages_count": len(messages),
                "summary": summary,
                "was_regenerated": needs_summary
            }

        except Exception as e:
            # Log error tapi jangan crash seluruh batch
            import logging
            logging.getLogger(__name__).error(
                f"[RoomSummary] Error processing session {session_id}: {e}"
            )
            return None
        finally:
            db.close()

    # ================================================================
    # Get previous insights untuk longitudinal context
    # ================================================================

    @staticmethod
    def get_previous_insights(
        room_name: str,
        user_id: str,
        db: Session,
        limit: int = 3
    ) -> List[Dict]:
        insights = db.query(RoomInsight).filter(
            RoomInsight.user_id == user_id,
            RoomInsight.room_name == room_name
        ).order_by(RoomInsight.created_at.desc()).limit(limit).all()

        return [
            {
                "insight_text": i.insight_text,
                "topics_covered": i.topics_covered or [],
                "mastery_snapshot": i.mastery_snapshot or {},
                "gaps_snapshot": i.gaps_snapshot or [],
                "created_at": i.created_at.isoformat()
            }
            for i in reversed(insights)
        ]

    # ================================================================
    # Cek apakah ada pesan baru sejak insight terakhir
    # ================================================================

    @staticmethod
    def has_new_messages_since_last_insight(
        room_name: str,
        user_id: str,
        db: Session
    ) -> bool:
        last_insight = db.query(RoomInsight).filter(
            RoomInsight.user_id == user_id,
            RoomInsight.room_name == room_name
        ).order_by(RoomInsight.created_at.desc()).first()

        if not last_insight:
            return True

        sessions = db.query(ChatSession).filter(
            ChatSession.user_id == user_id,
            ChatSession.room_name == room_name
        ).all()

        for session in sessions:
            new_msg = db.query(ChatMessage).filter(
                ChatMessage.session_id == session.id,
                ChatMessage.created_at > last_insight.created_at
            ).first()
            if new_msg:
                return True

        return False

    # ================================================================
    # Simpan insight ke DB
    # ================================================================

    @staticmethod
    def save_insight(
        room_name: str,
        user_id: str,
        insight_text: str,
        topics: List[str],
        mastery: Dict,
        gaps: List[Dict],
        trigger_type: str,
        message_count: int,
        db: Session
    ) -> RoomInsight:
        insight = RoomInsight(
            user_id=user_id,
            room_name=room_name,
            insight_text=insight_text,
            topics_covered=topics,
            mastery_snapshot=mastery,
            gaps_snapshot=gaps,
            trigger_type=trigger_type,
            message_count_at_generation=message_count,
            is_seen=False
        )
        db.add(insight)
        db.commit()
        db.refresh(insight)
        return insight

    # ================================================================
    # Generate longitudinal insight (narrative)
    # ================================================================

    @staticmethod
    def _generate_longitudinal_insight(
        overall_pct: float,
        all_topics: List[str],
        avg_mastery: Dict,
        gaps: List[Dict],
        session_summaries: List[Dict],
        previous_insights: List[Dict],
        total_messages: int,
        rated_messages: int,
        username: str = "kak",
        room_name: str = ""
    ) -> str:
        if total_messages < 3:
            return f"Hei kak! Ruang {room_name} baru mulai. Yuk chat lebih banyak! 🌱"

        history_text = ""
        if previous_insights:
            history_parts = []
            for i, prev in enumerate(previous_insights, 1):
                try:
                    prev_data = json.loads(prev["insight_text"])
                    prev_narrative = prev_data.get("narrative", prev["insight_text"])
                except Exception:
                    prev_narrative = prev["insight_text"]
                history_parts.append(
                    f"Insight {i} ({prev['created_at'][:10]}):\n{prev_narrative}"
                )
            history_text = "\n\n".join(history_parts)
        else:
            history_text = "Ini adalah insight pertama untuk room ini."

        mastery_text = "\n".join(
            [f"- {t}: {s}/5" for t, s in avg_mastery.items()]
        ) if avg_mastery else "Belum ada data mastery"

        gaps_text = "\n".join(
            [f"- {g['topic']} ({g['score']}/5)" for g in gaps]
        ) if gaps else "Tidak ada gap signifikan"

        prompt = f"""Kamu adalah Armisa — teman belajar yang pintar dan sabar untuk pelajar SMA/SMP Indonesia.
Gaya: semi santai, kayak kakak tingkat yang peduli, bahasa Indonesia yang enak dibaca.
Nama User: {username}
Tugasmu: tulis insight personal untuk user berdasarkan progress belajar mereka di room "{room_name}".

=== DATA PROGRESS ===
Overall mastery: {overall_pct}%
Total pesan: {total_messages}

Mastery per topik:
{mastery_text}

Gap/kelemahan:
{gaps_text}
=====================

=== HISTORY INSIGHT SEBELUMNYA ===
{history_text}
==================================

Tulis insight dengan struktur PERSIS seperti ini:

Halo [panggil "kak" saja]!

Menurut aku kamu sekarang kurang di [sebutkan kelemahan SPESIFIK — nama topik, bukan kata umum].
Tapi yang bagus, kamu udah solid di [sebutkan kelebihan SPESIFIK].
Saran aku: [saran konkret dan actionable — bukan "belajar lebih giat"].

[Kalau ada history insight sebelumnya → tambah 1 kalimat tentang progress dibanding sebelumnya.
Contoh: "Dibanding minggu lalu, kamu udah lumayan naik di [topik] — lanjutkan!"]

Aturan WAJIB:
- Kelemahan dan kelebihan HARUS spesifik (nama topik nyata, bukan "beberapa topik")
- Saran HARUS actionable (contoh: "coba kerjain 5 soal [topik] dulu", bukan "perbanyak latihan")
- Kalau mastery semua topik 0% atau belum ada data → minta user chat dulu, jangan karang-karang data
- Maksimal 4-5 kalimat total — padat, jelas, personal
- JANGAN pakai bullet point — tulis natural kayak orang ngomong
- JANGAN mulai dengan "Sebagai AI..." atau kalimat formal
- Bahasa harus enak dibaca, bukan laporan"""

        result = RoomSummaryService._call_llm(prompt)

        if not result:
            if overall_pct >= 70:
                return f"Progress {room_name} kamu udah {overall_pct}% — bagus banget kak! 🔥"
            elif gaps:
                return f"Udah {overall_pct}% untuk {room_name}. Fokus ke {gaps[0]['topic']} dulu ya kak! 💪"
            else:
                return f"Lagi membangun fondasi {room_name} nih kak. Tetap konsisten! 🌱"

        return result.strip()

    # ================================================================
    # MAIN: Build room summary
    # ================================================================

    @staticmethod
    def build_room_summary(
        room_name: str,
        user_id: str,
        db: Session,
        trigger_type: str = "manual"
    ) -> Dict:
        """
        Main function — build room summary dengan longitudinal memory.
        
        ThreadPoolExecutor sekarang thread-safe:
        tiap worker buka DB session sendiri via _process_session_in_thread()
        """

        # 1. Cek apakah ada pesan baru sejak insight terakhir
        if not RoomSummaryService.has_new_messages_since_last_insight(
            room_name, user_id, db
        ):
            last = db.query(RoomInsight).filter(
                RoomInsight.user_id == user_id,
                RoomInsight.room_name == room_name
            ).order_by(RoomInsight.created_at.desc()).first()

            if last:
                try:
                    cached_data = json.loads(last.insight_text)
                    narrative = cached_data.get("narrative", last.insight_text)
                except Exception:
                    narrative = last.insight_text
                    cached_data = {}

                return {
                    "room_name": room_name,
                    "armisa_insight": narrative,
                    "insight_data": cached_data,
                    "topics_discussed": last.topics_covered or [],
                    "mastery_per_topic": last.mastery_snapshot or {},
                    "gaps": last.gaps_snapshot or [],
                    "recommendations": cached_data.get("recommendations", []),
                    "overall_mastery_pct": cached_data.get("overall_pct", 0),
                    "total_messages": last.message_count_at_generation or 0,
                    "rated_messages": 0,
                    "cached": True,
                    "generated_at": last.created_at.isoformat()
                }

        # 2. Ambil semua sessions dalam room
        all_sessions = db.query(ChatSession).filter(
            ChatSession.user_id == user_id,
            ChatSession.room_name == room_name
        ).all()

        if not all_sessions:
            return {
                "room_name": room_name,
                "armisa_insight": f"Ruang {room_name} masih kosong nih kak. Yuk mulai belajar! 🌱",
                "insight_data": {},
                "overall_mastery_pct": 0,
                "topics_discussed": [],
                "mastery_per_topic": {},
                "gaps": [],
                "recommendations": [],
                "total_messages": 0,
                "rated_messages": 0,
                "cached": False,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }

        # 2b. Smart selector — filter stale + top 10
        sessions = RoomSummaryService.smart_select_sessions(all_sessions, db)

        if not sessions:
            return {
                "room_name": room_name,
                "armisa_insight": f"Belum ada aktivitas baru di {room_name} dalam 3 hari terakhir kak. Yuk belajar lagi! 💪",
                "insight_data": {},
                "overall_mastery_pct": 0,
                "topics_discussed": [],
                "mastery_per_topic": {},
                "gaps": [],
                "recommendations": [],
                "total_messages": 0,
                "rated_messages": 0,
                "cached": False,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }

        # 3. Parallel session summary — THREAD-SAFE
        # Pass hanya primitive data ke thread, bukan SQLAlchemy objects
        # Tiap thread buka DB session sendiri di _process_session_in_thread()
        session_tasks = [
            (
                str(session.id),
                session.session_type,
                session.title,
                session.summary,
                session.summary_updated_at
            )
            for session in sessions
        ]

        results = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(
                    RoomSummaryService._process_session_in_thread,
                    session_id,
                    session_type,
                    session_title,
                    session_summary,
                    summary_updated_at
                ): session_id
                for session_id, session_type, session_title, session_summary, summary_updated_at
                in session_tasks
            }

            for future in as_completed(futures):
                session_id = futures[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(
                        f"[RoomSummary] Thread future error for session {session_id}: {e}"
                    )

        # 4. Agregasi hasil parallel
        all_topics: List[str] = []
        all_mastery: Dict[str, List[float]] = {}
        total_messages = 0
        rated_messages = 0
        session_summaries = []

        for result in results:
            summary = result.get("summary", {})
            if not summary:
                continue

            total_messages += result.get("messages_count", 0)

            for topic in summary.get("topics_discussed", []):
                if topic and topic not in all_topics:
                    all_topics.append(topic)

            for topic, score in summary.get("mastery_per_topic", {}).items():
                if topic not in all_mastery:
                    all_mastery[topic] = []
                all_mastery[topic].append(float(score))

            rated_messages += summary.get("rated_messages", 0)

            session_summaries.append({
                "title": result.get("title", "Obrolan"),
                "type": result.get("type"),
                "topics": summary.get("topics_discussed", []),
                "avg_rating": summary.get("avg_rating", 0),
                "gaps": summary.get("gaps", [])
            })

        # 5. Hitung agregat
        avg_mastery = {
            topic: round(sum(scores) / len(scores), 2)
            for topic, scores in all_mastery.items()
        }

        gaps = [
            {
                "topic": t,
                "score": s,
                "severity": "critical" if s < 2.0 else "high" if s < 2.5 else "medium"
            }
            for t, s in avg_mastery.items() if s < 3.0
        ]
        gaps.sort(key=lambda x: x["score"])

        overall_pct = round(
            (sum(avg_mastery.values()) / (len(avg_mastery) * 5) * 100)
            if avg_mastery else 0, 1
        )

        # 6. Ambil previous insights untuk longitudinal context
        previous_insights = RoomSummaryService.get_previous_insights(
            room_name, user_id, db, limit=3
        )

        # 7. Generate narrative insight
        armisa_insight = RoomSummaryService._generate_longitudinal_insight(
            room_name=room_name,
            overall_pct=overall_pct,
            all_topics=all_topics,
            avg_mastery=avg_mastery,
            gaps=gaps,
            session_summaries=session_summaries,
            previous_insights=previous_insights,
            total_messages=total_messages,
            rated_messages=rated_messages
        )

        # 8. Rekomendasi
        recommendations = [f"Review {g['topic']}" for g in gaps[:3]]
        if not recommendations:
            recommendations.append("Penguasaan udah solid! Coba soal TKA level tinggi.")

        # 9. Build hybrid insight_data + simpan ke DB
        insight_data = {
            "narrative": armisa_insight,
            "mastery_per_topic": avg_mastery,
            "gaps": gaps,
            "topics": all_topics,
            "overall_pct": overall_pct,
            "recommendations": recommendations,
        }

        RoomSummaryService.save_insight(
            room_name=room_name,
            user_id=user_id,
            insight_text=json.dumps(insight_data),
            topics=all_topics,
            mastery=avg_mastery,
            gaps=gaps,
            trigger_type=trigger_type,
            message_count=total_messages,
            db=db
        )

        return {
            "room_name": room_name,
            "overall_mastery_pct": overall_pct,
            "total_messages": total_messages,
            "rated_messages": rated_messages,
            "topics_discussed": all_topics,
            "mastery_per_topic": avg_mastery,
            "gaps": gaps,
            "recommendations": recommendations,
            "armisa_insight": armisa_insight,
            "insight_data": insight_data,
            "cached": False,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }