"""
Exam Agent Service — Rewrite
=============================
Agentic exam generation dengan flow:

1. Agent collect context via parallel tool calls
2. decide_exam_composition() — LLM decide komposisi optimal
3. Build skeleton JSON
4. Build structured prompt → kirim ke Armisa
5. Armisa fill skeleton + narasi_pre_exam
6. Parse %%EXAM_START%% ... %%EXAM_END%%
7. Save ke DB → return result
"""

import asyncio
import json
import logging
import re
import httpx
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy import cast, String

from app.core.config import get_settings
from app.db.models import (
    Quiz, QuizQuestion, RoomInsight,
    ChatSession, ChatMessage, User
)
from app.services.rag_service import RAGService

settings = get_settings()
logger = logging.getLogger(__name__)


# ================================================================
# TOOL EXECUTORS
# ================================================================

def execute_get_user_mastery(room_name: str, user_id: str, db: Session) -> dict:
    insight = db.query(RoomInsight).filter(
        RoomInsight.user_id == user_id,
        RoomInsight.room_name == room_name
    ).order_by(RoomInsight.created_at.desc()).first()

    if not insight:
        return {
            "mastery_per_topic": {},
            "gaps": [],
            "overall_pct": 0,
            "narrative": "Belum ada data mastery."
        }

    try:
        data = json.loads(insight.insight_text)
        return {
            "mastery_per_topic": data.get("mastery_per_topic", {}),
            "gaps": data.get("gaps", []),
            "overall_pct": data.get("overall_pct", 0),
            "narrative": data.get("narrative", "")
        }
    except Exception:
        return {
            "mastery_per_topic": {},
            "gaps": [],
            "overall_pct": 0,
            "narrative": insight.insight_text
        }


def execute_get_relevant_chunks(
    room_name: str,
    topics: list,
    user_id: str,
    db: Session,
    rag_service: RAGService,
    n: int = 15
) -> dict:
    query = " ".join(topics)
    try:
        from app.db.models import Document
        from sqlalchemy import cast, String
        
        room_docs = db.query(Document.id).filter(
            Document.user_id == user_id,
            cast(Document.room_ids, String).like(f'%"{room_name}"%'),
            Document.status == "ready"
        ).all()
        
        room_doc_ids = [str(d.id) for d in room_docs]

        if not room_doc_ids:
            logger.info(f"[ExamAgent] No docs in room={room_name}, skipping RAG")
            return {"chunks": [], "total_found": 0}

        results = rag_service.search(
            user_id=user_id,
            query=query,
            n_results=n,
            doc_ids=room_doc_ids
        )
        chunks = [
            {
                "id": r.get("id", ""),
                "content": r.get("content", "")[:600],
                "topic_hint": r.get("metadata", {}).get("topic", "")
            }
            for r in results
        ]
        return {"chunks": chunks, "total_found": len(chunks)}
    except Exception as e:
        logger.error(f"RAG search error: {e}")
        return {"chunks": [], "total_found": 0}


def execute_get_previous_questions(
    room_name: str,
    user_id: str,
    db: Session,
    limit: int = 30
) -> dict:
    quiz_ids = [
        str(q.id) for q in db.query(Quiz).filter(
            Quiz.user_id == user_id,
            Quiz.room_id == room_name
        ).order_by(Quiz.created_at.desc()).limit(10).all()
    ]

    if not quiz_ids:
        return {"questions": [], "total": 0}

    questions = db.query(QuizQuestion).filter(
        QuizQuestion.quiz_id.in_(quiz_ids)
    ).limit(limit).all()

    return {
        "questions": [
            {"text": q.question_text[:150], "topic": q.topic}
            for q in questions
        ],
        "total": len(questions)
    }


def execute_get_session_context(session_id: str, db: Session) -> dict:
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id
    ).first()

    if not session or not session.summary:
        return {"topics_discussed": [], "session_name": ""}

    try:
        summary = json.loads(session.summary)
        return {
            "topics_discussed": summary.get("topics_discussed", []),
            "session_name": summary.get("session_name", ""),
            "chat_signal_score": summary.get(
                "chat_mastery_signals", {}
            ).get("signal_score", 0.5),
            "gaps": summary.get("gaps", [])
        }
    except Exception:
        return {"topics_discussed": [], "session_name": ""}


def execute_get_user_profile(user_id: str, db: Session) -> dict:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"nickname": "kak", "kelas": "SMA", "hardest_subjects": [], "streak": 0}

    return {
        "nickname": user.nickname or "kak",
        "kelas": user.kelas or "SMA",
        "hardest_subjects": user.hardest_subjects or [],
        "grade_level": user.grade_level or "SMA",
        "streak": user.current_streak or 0
    }


# ================================================================
# PARALLEL TOOL EXECUTOR
# ================================================================

async def execute_all_tools_parallel(
    user_id: str,
    room_name: str,
    topics: list,
    session_id: str,
    db: Session,
    rag_service: RAGService
) -> dict:
    loop = asyncio.get_event_loop()

    async def run(fn, *args):
        return await loop.run_in_executor(None, fn, *args)

    mastery_task = run(execute_get_user_mastery, room_name, user_id, db)
    profile_task = run(execute_get_user_profile, user_id, db)
    session_task = run(execute_get_session_context, session_id, db)
    prev_q_task = run(execute_get_previous_questions, room_name, user_id, db)
    rag_task = loop.run_in_executor(
        None,
        lambda: execute_get_relevant_chunks(room_name, topics, user_id, db, rag_service, 15)
    )

    results = await asyncio.gather(
        mastery_task, profile_task, session_task, prev_q_task, rag_task,
        return_exceptions=True
    )

    mastery, profile, session_ctx, prev_questions, rag = results

    def safe(r, fallback):
        return r if not isinstance(r, Exception) else fallback

    mastery = safe(mastery, {"mastery_per_topic": {}, "gaps": []})
    profile = safe(profile, {"nickname": "kak", "kelas": "SMA", "hardest_subjects": [], "streak": 0})
    session_ctx = safe(session_ctx, {"topics_discussed": []})
    prev_questions = safe(prev_questions, {"questions": []})
    rag = safe(rag, {"chunks": []})

    rag_text = "\n\n".join(
        f"[{i+1}] {c['content']}"
        for i, c in enumerate(rag.get("chunks", [])[:10])
    ) or "Tidak ada materi tersedia."

    return {
        "mastery_per_topic": mastery.get("mastery_per_topic", {}),
        "gaps": mastery.get("gaps", []),
        "overall_pct": mastery.get("overall_pct", 0),
        "session_topics": session_ctx.get("topics_discussed", []),
        "chat_signal_score": session_ctx.get("chat_signal_score", 0.5),
        "previous_questions": prev_questions.get("questions", []),
        "rag_context": rag_text,
        "profile": profile
    }


# ================================================================
# COMPOSITION DECIDER
# ================================================================

def decide_exam_composition(user_context: dict, user_hint: str = "") -> dict:

    profile = user_context.get("profile", {})
    mastery = user_context.get("mastery_per_topic", {})
    gaps = user_context.get("gaps", [])
    streak = profile.get("streak", 0) or 0
    kelas_raw = profile.get("kelas", "") or ""
    session_topics = user_context.get("session_topics", [])
    overall_pct = user_context.get("overall_pct", 0)

    try:
        kelas = int(''.join(filter(str.isdigit, kelas_raw))) if kelas_raw else 10
    except Exception:
        kelas = 10

    llm_decision = _llm_decide_composition(
        kelas=kelas,
        mastery=mastery,
        gaps=gaps,
        streak=streak,
        session_topics=session_topics,
        overall_pct=overall_pct,
        user_hint=user_hint
    )

    n_total = llm_decision.get("n_total", 5)
    n_essay = llm_decision.get("n_essay", 0)
    n_mcq = llm_decision.get("n_mcq", n_total - n_essay)
    difficulty = llm_decision.get("difficulty", "medium")

    # Cap n_total kalau tidak ada RAG context — model harus generate dari kepala,
    # lebih verbose → risiko truncation. Max 7 tanpa dokumen.
    has_rag = bool(user_context.get("rag_context", "").strip() and
                   user_context.get("rag_context") != "Tidak ada materi tersedia.")
    if not has_rag and n_total > 7:
        logger.info(f"[ExamAgent] No RAG context — capping n_total {n_total}→7 to prevent truncation")
        n_total = 7
        n_essay = min(n_essay, int(n_total * 0.4))
        n_mcq = n_total - n_essay

    # Dynamic time limit: 4 menit per esai, 2 menit per MCQ
    time_limit = (n_essay * 4) + (n_mcq * 2)

    return {
        "n_total": n_total,
        "n_mcq": n_mcq,
        "n_essay": n_essay,
        "difficulty": difficulty,
        "time_limit_minutes": max(5, time_limit),
        "is_new_user": not mastery and streak == 0,
        "reasoning": llm_decision.get("reasoning", ""),
        "student_context": _build_student_context(user_context, is_new_user=(not mastery))
    }


def _llm_decide_composition(
    kelas: int,
    mastery: dict,
    gaps: list,
    streak: int,
    session_topics: list,
    overall_pct: float,
    user_hint: str
) -> dict:
    mastery_summary = "\n".join(
        f"- {t}: {v}/5 ({'lemah' if v < 2.5 else 'cukup' if v < 3.5 else 'solid'})"
        for t, v in mastery.items()
    ) or "- Belum ada data"

    gaps_summary = ", ".join(
        g if isinstance(g, str) else g.get("topic", "")
        for g in gaps[:5]
    ) or "tidak ada gap spesifik"

    jenjang = "SMP" if kelas <= 9 else "SMA"

    prompt = f"""Kamu adalah exam composer untuk platform belajar siswa Indonesia di sekolah unggulan.

Data siswa:
- Kelas: {kelas} ({jenjang})
- Overall mastery: {overall_pct}%
- Mastery per topik:
{mastery_summary}
- Gap/kelemahan: {gaps_summary}
- Streak: {streak} hari
- Topik baru di sesi ini: {', '.join(session_topics) or 'tidak ada'}
- Request user: "{user_hint}"

Tugas: Tentukan komposisi ujian yang PALING OPTIMAL.

Rules WAJIB:
- n_total: min 3, max 15
- n_essay: max 40% dari n_total (bulatkan ke bawah)
- n_mcq: min 60% dari n_total
- STANDAR KESULITAN SEKOLAH UNGGULAN:
  * Mastery rendah (<2.5) → difficulty "medium" (Setara soal UTS analitik). DILARANG pakai "easy".
  * Mastery cukup (2.5 - 3.5) → difficulty "hard" (Multi-step problem).
  * Mastery tinggi (>3.5) → difficulty "expert" (Setara HOTS/SNBT/Olimpiade dasar).
- Topik baru di sesi → tambah MCQ untuk assess dulu
- Kalau user hint ada angka soal/essay → HORMATI sebagai acuan

STRICT HIERARCHY: Jika user_hint berisi angka soal atau tipe soal (misal: "esai aja"), abaikan Pedagogical Logic dan ikuti user_hint 100%. Jangan memberikan soal MCQ jika user meminta "Hanya Esai".

Output ONLY valid JSON:
{{
    "n_total": 7,
    "n_mcq": 5,
    "n_essay": 2,
    "difficulty": "hard",
    "reasoning": "alasan singkat max 20 kata kenapa komposisi ini"
}}"""

    try:
        response = httpx.post(
            f"{settings.OPENROUTER_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek/deepseek-v3.2",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "max_tokens": 500,
                "response_format": {"type": "json_object"}
            },
            timeout=10.0
        )
        data = response.json()
        raw = data["choices"][0]["message"]["content"].strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception as e:
        logger.error(f"[ExamAgent] LLM compose error: {e}")
        avg_mastery = sum(mastery.values()) / len(mastery) if mastery else 2.5
        n_total = 5
        n_essay = 1 if kelas <= 9 else 0
        # Fallback sekarang minimal Medium, maksimal Expert
        difficulty = "medium" if avg_mastery < 3.0 else "hard" if avg_mastery < 4.0 else "expert"
        return {
            "n_total": n_total,
            "n_mcq": n_total - n_essay,
            "n_essay": n_essay,
            "difficulty": difficulty,
            "reasoning": "Fallback — LLM tidak tersedia"
        }


def _build_student_context(user_context: dict, is_new_user: bool) -> dict:
    mastery = user_context.get("mastery_per_topic", {})
    gaps = user_context.get("gaps", [])
    profile = user_context.get("profile", {})
    streak = profile.get("streak", 0) or 0
    session_topics = user_context.get("session_topics", [])

    if is_new_user:
        return {
            "status": "new_user",
            "message": "User baru — belum ada data mastery. Berikan Assessment Test (Medium-Hard) dengan penalaran analitis untuk mengkalibrasi baseline kemampuannya yang sesungguhnya.",
            "kelas": profile.get("kelas", ""),
            "streak_label": "Baru mulai belajar",
            "session_topics_label": "Belum ada riwayat sesi"
        }

    mastery_snapshot = {}
    for topic, score in mastery.items():
        gap = next(
            (g for g in gaps if (g if isinstance(g, str) else g.get("topic", "")) == topic),
            None
        )
        if score < 2.0:
            label = "Lemah"
        elif score < 3.0:
            label = "Cukup"
        elif score < 4.0:
            label = "Solid"
        else:
            label = "Sangat baik"

        if gap and isinstance(gap, dict) and gap.get("description"):
            label += f" — {gap['description']}"

        mastery_snapshot[topic] = {"score": score, "out_of": 5, "label": label}

    if streak == 0:
        streak_label = "Belum ada streak — baru balik belajar"
    elif streak < 3:
        streak_label = f"{streak} hari — baru mulai konsisten"
    elif streak < 7:
        streak_label = f"{streak} hari — mulai bagus"
    elif streak < 30:
        streak_label = f"{streak} hari — konsisten 🔥"
    else:
        streak_label = f"{streak} hari — luar biasa konsisten 👑"

    session_label = (
        f"Baru saja bahas: {', '.join(session_topics)} — topik fresh, perlu di-assess"
        if session_topics else "Tidak ada topik baru di sesi ini"
    )

    return {
        "status": "returning_user",
        "kelas": profile.get("kelas", ""),
        "mastery_snapshot": mastery_snapshot,
        "gaps": gaps,
        "streak_label": streak_label,
        "session_topics_label": session_label
    }


# ================================================================
# LAPIS 3 — SKELETON & PROMPT BUILDER
# Fix: key seragam "correct_answer" untuk semua tipe soal.
#      options essay eksplisit [] bukan None.
# ================================================================

def build_question_skeleton(n_mcq: int, n_essay: int) -> list:
    skeleton = []
    idx = 1

    for _ in range(n_mcq):
        skeleton.append({
            "id": idx,
            "type": "mcq",
            "topic": "...",
            "question": "...",
            "options": [
                {"text": "A. ...", "is_correct": False, "error_category": "..."},
                {"text": "B. ...", "is_correct": False, "error_category": "..."},
                {"text": "C. ...", "is_correct": False, "error_category": "..."},
                {"text": "D. ...", "is_correct": False, "error_category": "..."}
            ],
            # FIX: pakai "correct_answer" (integer 0-3) konsisten dengan essay
            "correct_answer": 0,
            "explanation": "..."
        })
        idx += 1

    for _ in range(n_essay):
        skeleton.append({
            "id": idx,
            "type": "essay",
            "topic": "...",
            "question": "...",
            # FIX: eksplisit [] bukan None — AI tidak bingung soal tipe data
            "options": [],
            # FIX: key sama persis dengan MCQ, tapi berisi string model answer
            "correct_answer": "...",
            "explanation": "..."
        })
        idx += 1

    return skeleton


def build_armisa_prompt(
    user_context: dict,
    skeleton: list,
    topics: list,
    difficulty_override: Optional[str],
    student_context: dict = None,
    composition_reasoning: str = "",
    is_new_user: bool = False
) -> str:
    profile = user_context.get("profile", {})
    nickname = profile.get("nickname", "kak")
    kelas = profile.get("kelas", "SMA")
    hardest = ", ".join(profile.get("hardest_subjects", [])) or "belum diketahui"

    if is_new_user or not student_context:
        student_block = """[STATUS SISWA]
Ini ujian PERTAMA siswa ini di Sismind — belum ada data mastery.
Berikan soal dengan standar "Medium-Hard" (HOTS) untuk menguji baseline kemampuan analitisnya secara real.
Narasi pre-exam harus menyambut hangat, tapi tegaskan bahwa kuis ini dirancang menantang untuk melihat potensinya."""
    else:
        mastery_snap = student_context.get("mastery_snapshot", {})
        mastery_lines = "\n".join(
            f"  - {topic}: {data['score']}/5 — {data['label']}"
            for topic, data in mastery_snap.items()
        ) or "  - Belum ada data"

        gaps = student_context.get("gaps", [])
        gaps_text = ", ".join(
            g if isinstance(g, str) else g.get("topic", "")
            for g in gaps
        ) or "tidak ada"

        student_block = f"""[STATUS SISWA]
Kelas: {kelas}
{student_context.get('streak_label', '')}
{student_context.get('session_topics_label', '')}

Mastery per topik:
{mastery_lines}

Gap/kelemahan: {gaps_text}
Kenapa komposisi soal ini: {composition_reasoning}"""

    prev_q_text = "\n".join(
        f"- {q['text'][:100]}"
        for q in user_context.get("previous_questions", [])[:5]
    ) or "- Belum ada soal sebelumnya"

    skeleton_json = json.dumps({
        "narasi_pre_exam": "...",
        "exam": True,
        "questions": skeleton
    }, indent=2, ensure_ascii=False)

    tone_note = (
        "Tone: menyambut hangat dan menantang, ini ujian baseline pertama mereka!"
        if is_new_user
        else "Tone: personal — sebut 1 hal spesifik tentang progress/gap siswa ini. Jangan generik."
    )

    n_soal = len(skeleton)

    return f"""=== KONTEKS USER ===
Nama: {nickname} | Kelas: {kelas}
Mapel tersulit: {hardest}

{student_block}

Soal yang pernah dibuat (hindari duplikat):
{prev_q_text}

Materi dari dokumen:
{user_context.get("rag_context", "Tidak ada materi tersedia.")}
===================

Kamu adalah Armisa, guru penguji standar tingkat tinggi. Isi JSON skeleton berikut.

ATURAN WAJIB & STANDAR KESULITAN (HOTS):
You must generate the quiz in strictly valid JSON format. Follow these rules exactly:
1. For MCQ:
   - "type" MUST be exactly "mcq".
   - "options" MUST contain exactly 4 choices.
   - "correct_answer" MUST be the exact integer index (0, 1, 2, or 3). NEVER use null.
   - KUALITAS DISTRACTOR: Opsi salah (A, B, C, D) HARUS SANGAT LOGIS dan menjebak. Buat berdasarkan miskonsepsi umum atau kesalahan komputasi yang sering terjadi. DILARANG membuat opsi yang jelas-jelas salah/konyol.
2. For Essay Questions:
   - "type" MUST be exactly "essay".
   - "options" MUST be an empty list [].
   - "correct_answer" MUST contain the keyword or main concept expected in the answer as a STRING.
   - KUALITAS ESSAY: Berikan skenario kasus atau problem-solving yang butuh minimal 2 langkah penyelesaian/analisis.
3. KOGNITIF LEVEL: Hindari soal hafalan murni/teori dasar (C1-C2). Prioritaskan penalaran dan penerapan (C3-C6) sesuai level: {difficulty_override or 'hard'}.
- Topik fokus: {', '.join(topics)}
- Hindari duplikat soal yang pernah ada
- narasi_pre_exam: Tulis 2 kalimat pembuka yang personal. 
  * Berikan 1 tips belajar spesifik berdasarkan [TOPIK LEMAH] siswa.
  * Sebut level kesulitan {difficulty_override} dengan gaya santai. {tone_note}
- Output: narasi singkat lalu %%EXAM_START%% lalu JSON lalu %%EXAM_END%%
4. KUALITAS PEMBAHASAN (EXPLANATION): 
   - Maksimal 2-3 kalimat per soal. Padat, langsung ke inti.
   - Sebutkan kenapa jawaban benar itu tepat, dan 1 jebakan utama yang sering salah.
   - DILARANG menulis ulang soal atau opsi di dalam explanation.
   - DILARANG menulis "step-by-step" yang panjang — cukup hasil & alasan inti.

TOKEN BUDGET: Kamu generate {n_soal} soal. Jaga agar total output JSON muat dalam satu response. Jangan bertele-tele.

JSON SKELETON:
{skeleton_json}"""


# ================================================================
# ARMISA LLM CALL
# ================================================================

def call_armisa(prompt: str) -> str:
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
                "max_tokens": 4000,
            },
            timeout=60.0
        )
        data = response.json()
        if "choices" not in data:
            logger.error(f"[ExamAgent] OpenRouter response missing 'choices': {data}")
            return ""
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"[ExamAgent] Armisa call error: {e}")
        return ""


# ================================================================
# LAPIS 1 — PARSER
# Fix: strip <think> blocks + ekstraksi JSON via regex { ... }
# ================================================================

def _fix_latex_escapes(json_str: str) -> str:
    # Model sering nulis LaTeX raw backslash tanpa di-escape di dalam JSON string.
    # Fix: double semua backslash yang bukan valid JSON escape sequences.
    VALID_ESCAPES = set('"\\/bfnrtu')
    result = []
    i = 0
    in_string = False
    while i < len(json_str):
        ch = json_str[i]
        if ch == '"'and (i == 0 or json_str[i-1] != '\\'):
            in_string = not in_string
            result.append(ch)
            i += 1
        elif in_string and ch == '\\':
            next_ch = json_str[i+1] if i+1 < len(json_str) else ''
            if next_ch in VALID_ESCAPES:
                result.append(ch)
                result.append(next_ch)
                i += 2
            else:
                # Invalid escape — double it
                result.append('\\\\')
                i += 1
        else:
            result.append(ch)
            i += 1
    return ''.join(result)


def _safe_json_loads(json_str: str) -> dict:
    """Try parse, jika gagal karena invalid escape → fix dan retry."""
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        if 'escape' in str(e).lower():
            logger.warning(f"[ExamAgent] Invalid escape detected, attempting fix...")
            fixed = _fix_latex_escapes(json_str)
            return json.loads(fixed)
        raise


def parse_exam_response(raw: str) -> tuple[str, dict]:
    # --- Strip blok <think>...</think> (deep reasoning models) ---
    clean_raw = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL).strip()

    narasi = ""
    exam_data = {}

    if "%%EXAM_START%%" in clean_raw and "%%EXAM_END%%" in clean_raw:
        parts = clean_raw.split("%%EXAM_START%%")
        narasi = parts[0].strip()
        json_part = parts[1].split("%%EXAM_END%%")[0].strip()

        # Ekstraksi JSON absolut: cari { pertama sampai } terakhir
        match = re.search(r'(\{.*\})', json_part, re.DOTALL)
        if not match:
            raise ValueError("Tidak ditemukan JSON valid di antara marker.")
        try:
            exam_data = _safe_json_loads(match.group(1))
        except Exception as e:
            logger.error(f"[ExamAgent] JSON parse error: {e}")
            raise ValueError("Armisa gagal generate soal dengan format yang benar.")
    else:
        # Fallback: coba ekstrak JSON langsung dari seluruh output
        match = re.search(r'(\{.*\})', clean_raw, re.DOTALL)
        if not match:
            raise ValueError("Format response Armisa tidak valid — tidak ada JSON ditemukan.")
        try:
            exam_data = _safe_json_loads(match.group(1))
            narasi = exam_data.pop("narasi", "")
        except Exception as e:
            logger.error(f"[ExamAgent] Fallback JSON parse error: {e}")
            raise ValueError("Format response Armisa tidak valid.")

    narasi_pre_exam = exam_data.pop("narasi_pre_exam", narasi or "")
    if not narasi:
        narasi = narasi_pre_exam

    # Normalisasi ringan tipe field (validasi ketat ada di save_exam_to_db)
    questions = exam_data.get("questions", [])
    for q in questions:
        if q.get("type") == "essay":
            if q.get("options") is None:
                q["options"] = []

    return narasi_pre_exam, exam_data


# ================================================================
# LAPIS 2 — GATEKEEPER VALIDATION
# Fix: sanitasi per-soal sebelum masuk DB, skip soal cacat.
# ================================================================

def _validate_and_sanitize_question(q: dict, difficulty: str, idx: int) -> Optional[dict]:
    """
    Validasi satu soal. Return dict bersih, atau None jika soal harus di-skip.
    """
    q_type = q.get("type", "mcq")
    question_text = (q.get("question") or "").strip()

    if not question_text:
        logger.warning(f"[ExamAgent] Soal #{idx} dibuang — question kosong.")
        return None

    if q_type == "mcq":
        options = q.get("options")
        if not isinstance(options, list) or len(options) < 2:
            logger.warning(f"[ExamAgent] Soal #{idx} (MCQ) dibuang — options tidak valid: {options}")
            return None

        raw_correct = q.get("correct_answer")
        try:
            correct_answer = int(raw_correct)
            if correct_answer < 0 or correct_answer >= len(options):
                raise ValueError("index di luar jangkauan")
        except (TypeError, ValueError):
            logger.warning(
                f"[ExamAgent] Soal #{idx} (MCQ) correct_answer '{raw_correct}' tidak valid — fallback ke 0."
            )
            correct_answer = 0

        return {
            "type": "mcq",
            "question_text": question_text,
            "options": options,
            "correct_answer": correct_answer,
            "explanation": (q.get("explanation") or "").strip(),
            "topic": (q.get("topic") or "").strip(),
            "difficulty": difficulty,
        }

    elif q_type == "essay":
        raw_correct = q.get("correct_answer")
        if isinstance(raw_correct, str) and raw_correct.strip():
            correct_answer = raw_correct.strip()
        else:
            fallback = (q.get("explanation") or "").strip()
            correct_answer = fallback if fallback else "Kunci jawaban standar."
            logger.warning(
                f"[ExamAgent] Soal #{idx} (essay) correct_answer kosong/null — pakai fallback."
            )

        return {
            "type": "essay",
            "question_text": question_text,
            "options": [],           # selalu array kosong untuk essay
            "correct_answer": correct_answer,
            "explanation": (q.get("explanation") or "").strip(),
            "topic": (q.get("topic") or "").strip(),
            "difficulty": difficulty,
        }

    else:
        logger.warning(f"[ExamAgent] Soal #{idx} dibuang — type tidak dikenal: '{q_type}'")
        return None


# ================================================================
# SAVE TO DB
# ================================================================

def save_exam_to_db(
    quiz_id: str,
    user_id: str,
    room_name: str,
    title: str,
    narasi: str,
    exam_data: dict,
    exam_config: dict,
    difficulty: str,
    time_limit_minutes: int,
    db: Session
) -> list:
    questions_raw = exam_data.get("questions", [])
    if not questions_raw:
        raise ValueError("Tidak ada soal yang di-generate.")

    # --- Lapis 2: validasi & sanitasi sebelum masuk DB ---
    clean_questions = []
    for i, q in enumerate(questions_raw):
        sanitized = _validate_and_sanitize_question(q, difficulty, idx=i + 1)
        if sanitized:
            clean_questions.append(sanitized)

    if not clean_questions:
        raise ValueError("Semua soal gagal validasi — tidak ada soal valid untuk disimpan.")

    logger.info(
        f"[ExamAgent] Gatekeeper: {len(questions_raw)} soal masuk, "
        f"{len(clean_questions)} lolos validasi, "
        f"{len(questions_raw) - len(clean_questions)} dibuang."
    )

    quiz = Quiz(
        id=quiz_id,
        user_id=user_id,
        author_id=user_id,
        title=title,
        narasi=narasi,
        subject=room_name,
        room_id=room_name,
        total_questions=len(clean_questions),
        difficulty=difficulty,
        time_limit_minutes=time_limit_minutes,
        exam_config=exam_config,
        status="active",
        created_at=datetime.now(timezone.utc)
    )
    db.add(quiz)
    db.flush()

    saved_questions = []
    for i, q in enumerate(clean_questions):
        question = QuizQuestion(
            id=str(uuid4()),
            quiz_id=quiz_id,
            question_text=q["question_text"],
            question_type=q["type"],
            options=q["options"],
            correct_answer=q["correct_answer"],
            explanation=q["explanation"],
            difficulty=q["difficulty"],
            topic=q["topic"],
            question_order=i + 1
        )
        db.add(question)
        saved_questions.append({
            "id": str(question.id),
            "question_text": question.question_text,
            "question_type": question.question_type,
            "options": question.options,
            "difficulty": question.difficulty,
            "topic": question.topic,
            "question_order": i + 1
        })

    db.commit()
    return saved_questions


# ================================================================
# MAIN ENTRY POINT
# ================================================================

async def generate_exam_agentic(
    user_id: str,
    room_name: str,
    session_id: str,
    topics: list,
    db: Session,
    rag_service: RAGService,
    user_hint: str = ""
) -> dict:
    logger.info(f"[ExamAgent] Generating exam — user={user_id} room={room_name} topics={topics}")

    # Step 1: Parallel tool calls
    logger.info("[ExamAgent] Step 1 — parallel tool calls")
    user_context = await execute_all_tools_parallel(
        user_id=user_id,
        room_name=room_name,
        topics=topics,
        session_id=session_id,
        db=db,
        rag_service=rag_service
    )

    # Step 1.5: Decide composition
    logger.info("[ExamAgent] Step 1.5 — decide composition")
    composition = decide_exam_composition(user_context, user_hint=user_hint)
    logger.info(
        f"[ExamAgent] Composition: {composition['n_mcq']} MCQ + {composition['n_essay']} essay, "
        f"difficulty={composition['difficulty']}, reason={composition['reasoning']}"
    )

    # Step 2: Build skeleton
    logger.info("[ExamAgent] Step 2 — build skeleton")
    skeleton = build_question_skeleton(composition["n_mcq"], composition["n_essay"])

    # Step 3: Build prompt
    logger.info("[ExamAgent] Step 3 — build Armisa prompt")
    armisa_prompt = build_armisa_prompt(
        user_context=user_context,
        skeleton=skeleton,
        topics=topics,
        difficulty_override=composition["difficulty"],
        student_context=composition["student_context"],
        composition_reasoning=composition["reasoning"],
        is_new_user=composition["is_new_user"]
    )

    # Step 4: Call Armisa
    logger.info("[ExamAgent] Step 4 — call Armisa")
    loop = asyncio.get_event_loop()
    raw_response = await loop.run_in_executor(None, call_armisa, armisa_prompt)

    if not raw_response:
        raise ValueError("Armisa tidak merespons. Coba lagi.")

    # Step 5: Parse response
    logger.info("[ExamAgent] Step 5 — parse response")
    narasi, exam_data = parse_exam_response(raw_response)

    # Step 6: Save to DB
    logger.info("[ExamAgent] Step 6 — save to DB")
    quiz_id = str(uuid4())
    title = f"Ujian {', '.join(topics)} — {datetime.now(timezone.utc).strftime('%d %b %Y')}"

    exam_config = {
        "topics": topics,
        "n_mcq": composition["n_mcq"],
        "n_essay": composition["n_essay"],
        "difficulty_override": composition["difficulty"],
        "time_limit_minutes": composition["time_limit_minutes"],
        "mastery_snapshot": user_context.get("mastery_per_topic", {}),
        "gaps_used": user_context.get("gaps", []),
        "session_topics": user_context.get("session_topics", []),
        "is_new_user": composition["is_new_user"],
        "composition_reasoning": composition["reasoning"],
        "generated_at": datetime.now(timezone.utc).isoformat()
    }

    saved_questions = save_exam_to_db(
        quiz_id=quiz_id,
        user_id=user_id,
        room_name=room_name,
        title=title,
        narasi=narasi,
        exam_data=exam_data,
        exam_config=exam_config,
        difficulty=composition["difficulty"],
        time_limit_minutes=composition["time_limit_minutes"],
        db=db
    )

    logger.info(f"[ExamAgent] ✅ Quiz {quiz_id} — {len(saved_questions)} soal")

    return {
        "quiz_id": quiz_id,
        "title": title,
        "narasi": narasi,
        "questions": saved_questions,
        "exam_config": exam_config,
        "total_questions": len(saved_questions),
        "time_limit_minutes": composition["time_limit_minutes"],
        "is_new_user": composition["is_new_user"]
    }