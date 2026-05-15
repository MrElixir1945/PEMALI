"""
Quiz Endpoints
==============
Quiz creation, management, and submission
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import asyncio
from app.services.scoring_engine import ScoringEngine
from app.db.models import ChatSession, ChatMessage
from app.services.xp_service import XP
import logging
from app.db import get_db_session
from app.db.models import User, Quiz, QuizQuestion, QuizSubmission, QuestionSubmission, UserStatus
from app.models.schemas import (
    QuizCreate, QuizResponse, QuizQuestionResponse,
    QuizAnswer, QuizSubmissionRequest, QuizSubmissionResponse
)
from app.api.deps import get_current_user_from_token
from app.services.rag_service import RAGService
import json
import httpx
from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional

router = APIRouter(prefix="/quiz", tags=["Quiz"])
logger = logging.getLogger(__name__)

def score_essay_answer(
    question_text: str,
    user_answer: str,
    model_answer: str,
    topic: str
) -> dict:
    """
    4-layer essay scoring.
    Return: { score_0_to_1, feedback, pattern }
    """

    # ── Layer 1: Deterministic ──
    if not user_answer or len(user_answer.strip()) < 10:
        return {
            "score": 0.0,
            "feedback": "Jawaban terlalu singkat atau kosong.",
            "pattern": "no_answer"
        }

    word_count = len(user_answer.split())
    length_ok = word_count >= 15  # minimal 15 kata

    # Keyword check dari model answer
    model_keywords = [
        w.lower() for w in model_answer.split()
        if len(w) > 4  # skip kata pendek
    ][:10]  # ambil 10 keyword pertama
    keyword_hits = sum(
        1 for kw in model_keywords
        if kw in user_answer.lower()
    )
    keyword_score = keyword_hits / len(model_keywords) if model_keywords else 0.5

    # Early exit kalau jawaban sangat kurang
    if not length_ok and keyword_score < 0.2:
        return {
            "score": 0.1,
            "feedback": "Jawaban perlu lebih lengkap dan detail.",
            "pattern": "too_short"
        }

    # ── Layer 2: Binary rubric LLM (temperature=0) ──
    rubric_result = _call_rubric_llm(
        question_text, user_answer, model_answer
    )
    binary_scores = rubric_result.get("results", [True, False, False, False])
    rubric_score = sum(binary_scores) / len(binary_scores)

    # ── Layer 3: Pattern detection (pure code) ──
    conceptual = rubric_scores_to_conceptual(binary_scores)
    completeness = (keyword_score + (1.0 if length_ok else 0.4)) / 2
    reasoning = rubric_scores_to_reasoning(binary_scores)

    pattern = detect_essay_pattern(conceptual, completeness, reasoning)

    # Final score: weighted combo
    final_score = round(
        (rubric_score * 0.5) +
        (keyword_score * 0.3) +
        (0.2 if length_ok else 0.0),
        3
    )
    final_score = min(1.0, max(0.0, final_score))

    # ── Layer 4: Narasi Armisa (temperature=0.5) ──
    feedback = _call_narrator_llm(
        question_text, user_answer, pattern,
        conceptual, completeness, reasoning, topic
    )

    return {
        "score": final_score,
        "feedback": feedback,
        "pattern": pattern
    }


async def _call_scalar_rubric_llm(question: str, answer: str, model_answer: str) -> dict:
    """Point 2: Mengambil skor skalar 0.0 - 1.0 untuk akurasi, penalaran, dan kelengkapan."""
    import httpx
    from app.core.config import get_settings
    settings = get_settings()

    prompt = f"""Evaluasi jawaban essay ini terhadap kunci jawaban.
    
    Soal: {question}
    Jawaban Siswa: {answer}
    Kunci Jawaban: {model_answer}

    Berikan penilaian dalam skala 0.0 sampai 1.0 untuk:
    1. accuracy: Ketepatan fakta/konsep.
    2. reasoning: Alur logika dan penjelasan "mengapa".
    3. completeness: Seberapa lengkap poin kunci disebut.

    Output HANYA JSON:
    {{"accuracy": float, "reasoning": float, "completeness": float}}"""

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.OPENROUTER_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}"},
                json={
                    "model": settings.CHAT_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0,
                    "response_format": { "type": "json_object" }
                },
                timeout=20.0
            )
            data = response.json()
            return json.loads(data["choices"][0]["message"]["content"])
        except Exception as e:
            logger.error(f"[EssayScoring] Scalar LLM Error: {e}")
            return {"accuracy": 0.5, "reasoning": 0.5, "completeness": 0.5}

def _call_narrator_llm(
    question: str, answer: str, pattern: str,
    conceptual: float, completeness: float, reasoning: float,
    topic: str
) -> str:
    """Layer 4 — narasi feedback, temperature=0.5."""
    import httpx
    from app.core.config import get_settings
    settings = get_settings()

    prompt = f"""Kamu adalah Armisa — AI tutor, gaya kakak tingkat yang santai.

Topik soal: {topic}
Pattern jawaban siswa: {pattern}
Skor dimensi: konsep={round(conceptual*100)}%, kelengkapan={round(completeness*100)}%, penalaran={round(reasoning*100)}%
Jawaban siswa (ringkas): {answer[:200]}

Tulis 2 kalimat feedback yang:
- Spesifik tentang apa yang kurang atau bagus
- Santai, tidak menghakimi
- JANGAN sebut nama pattern atau angka dimensi
- JANGAN mulai dengan "Armisa" atau "Kamu adalah"""

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
                "temperature": 0.5,
                "max_tokens": 120,
            },
            timeout=15.0
        )
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"[EssayScoring] Narrator LLM error: {e}")
        return "Jawaban kamu ada poinnya, tapi coba lengkapin lagi ya!"


def rubric_scores_to_conceptual(results: list) -> float:
    """Kriteria 1 (konsep inti) → conceptual score."""
    if not results:
        return 0.5
    return 1.0 if results[0] else 0.2


def rubric_scores_to_reasoning(results: list) -> float:
    """Kriteria 2 (proses/mekanisme) → reasoning score."""
    if len(results) < 2:
        return 0.5
    return 1.0 if results[1] else 0.3


def detect_essay_pattern(
    conceptual: float,
    completeness: float,
    reasoning: float
) -> str:
    """Layer 3 — pure code pattern detection."""
    if conceptual < 0.5 and completeness > 0.7:
        return "hafal_tapi_tidak_paham"
    elif conceptual > 0.7 and reasoning < 0.4:
        return "paham_tapi_tidak_bisa_jelaskan"
    elif all(s < 0.5 for s in [conceptual, completeness, reasoning]):
        return "perlu_review_total"
    elif all(s > 0.7 for s in [conceptual, completeness, reasoning]):
        return "solid"
    return "partial"




@router.post("/", response_model=QuizResponse, status_code=status.HTTP_201_CREATED)
async def create_quiz(
    quiz_data: QuizCreate,
    user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db_session)
):
    """
    Create a new quiz.

    - **title**: Quiz title
    - **description**: Optional description
    - **subject**: Subject name (Math, Physics, Indonesian, etc.)
    - **total_questions**: Number of questions (1-100)
    - **difficulty**: Optional difficulty level
    - **time_limit_minutes**: Optional time limit
    - **is_adaptive**: Enable adaptive difficulty
    """
    quiz = Quiz(
        id=str(uuid4()),
        user_id=str(user.id),
        author_id=str(user.id),
        title=quiz_data.title,
        description=quiz_data.description,
        subject=quiz_data.subject,
        total_questions=quiz_data.total_questions,
        difficulty=quiz_data.difficulty,
        time_limit_minutes=quiz_data.time_limit_minutes,
        is_adaptive=quiz_data.is_adaptive,
        status="draft",
        created_at=datetime.now(timezone.utc)
    )

    db.add(quiz)
    db.commit()
    db.refresh(quiz)

    return {
        "id": quiz.id,
        "title": quiz.title,
        "description": quiz.description,
        "subject": quiz.subject,
        "total_questions": quiz.total_questions,
        "difficulty": quiz.difficulty,
        "time_limit_minutes": quiz.time_limit_minutes,
        "status": quiz.status,
        "created_at": quiz.created_at
    }


# @router.post("/{quiz_id}/submit")
# async def submit_quiz(
#     quiz_id: str,
#     submission_data: QuizSubmissionRequest,
#     user: User = Depends(get_current_user_from_token),
#     db: Session = Depends(get_db_session)
# ):
#     from app.services.scoring_engine import ScoringEngine
#     from app.db.models import MasteryScore

#     quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
#     if not quiz:
#         raise HTTPException(status_code=404, detail="Quiz not found")

#     questions = db.query(QuizQuestion).filter(
#         QuizQuestion.quiz_id == quiz_id
#     ).order_by(QuizQuestion.question_order).all()

#     # ── Save submission dulu ──
#     submission = QuizSubmission(
#         id=str(uuid4()),
#         quiz_id=quiz_id,
#         user_id=str(user.id),
#         answers={a.question_id: a.answer for a in submission_data.answers},
#         started_at=datetime.now(timezone.utc)
#     )
#     db.add(submission)
#     db.flush()

#     # ── Score MCQ (auto) ──
#     correct_count = 0
#     for ans in submission_data.answers:
#         question = next(
#             (q for q in questions if str(q.id) == str(ans.question_id)),
#             None
#         )
#         if not question:
#             continue

#         is_correct = False
#         if question.question_type == "mcq":
#             if isinstance(ans.answer, int):
#                 is_correct = ans.answer == question.correct_answer
#             elif isinstance(ans.answer, str):
#                 is_correct = ans.answer == str(question.correct_answer)

#         if is_correct:
#             correct_count += 1

#         db.add(QuestionSubmission(
#             id=str(uuid4()),
#             submission_id=submission.id,
#             question_id=str(question.id),
#             user_answer=ans.answer,
#             is_correct=is_correct
#         ))

#     total_questions = len(questions)
#     raw_percentage = (correct_count / total_questions * 100) if total_questions > 0 else 0

#     submission.score = correct_count
#     submission.max_score = total_questions
#     submission.percentage = raw_percentage
#     submission.submitted_at = datetime.now(timezone.utc)
#     quiz.status = "completed"
#     quiz.completed_at = datetime.now(timezone.utc)
#     db.commit()

#     # ── ScoringEngine (sync — user nunggu) ──
#     try:
#         # Ambil chat signal dari session summary
#         chat_signal_score = 0.5
#         chat_summary = ""
#         if quiz.exam_config:
#             session_topics = quiz.exam_config.get("session_topics", [])

#         scoring_result = await ScoringEngine.score_exam(
#             quiz_id=quiz_id,
#             user_id=str(user.id),
#             db=db,
#             chat_signal_score=chat_signal_score,
#             chat_history_summary=chat_summary
#         )
#     except Exception as e:
#         logger.error(f"[Submit] ScoringEngine error: {e}")
#         # Fallback — return raw score kalau scoring engine gagal
#         scoring_result = {
#             "final_score": int(raw_percentage),
#             "mastery_per_topic": {},
#             "narrative": f"Kamu jawab {correct_count} dari {total_questions} soal dengan benar!",
#             "difficulty_recommendation": {"recommended_difficulty": "medium"},
#             "components": {},
#             "essay_feedbacks": []
#         }

#     return {
#         "submission_id": submission.id,
#         "score": correct_count,
#         "max_score": total_questions,
#         "percentage": round(raw_percentage, 2),
#         "final_mastery_score": scoring_result["final_score"],
#         "mastery_per_topic": scoring_result["mastery_per_topic"],
#         "narrative": scoring_result["narrative"],
#         "difficulty_recommendation": scoring_result["difficulty_recommendation"],
#         "essay_feedbacks": scoring_result.get("essay_feedbacks", []),
#         "components": scoring_result.get("components", {}),
#         "submitted_at": submission.submitted_at
#     }

async def generate_post_exam_narasi(
    nickname: str,
    percentage: float,
    per_topic_mastery: dict,
    wrong_questions: list,
    essay_feedbacks: list,
    is_passed: bool
) -> str:
    import httpx
    from app.core.config import get_settings
    settings = get_settings()

    topic_lines = "\n".join(
        f"- {topic}: {round(score * 100)}%"
        for topic, score in per_topic_mastery.items()
    ) or "- tidak ada data"

    wrong_topics = list(set(
        wq.get("topic", "") for wq in wrong_questions if wq.get("topic")
    ))
    wrong_text = ", ".join(wrong_topics) or "tidak ada"

    essay_text = ""
    if essay_feedbacks:
        essay_lines = "\n".join(
            f"- {ef.get('topic', '')}: {round(ef.get('score', 0) * 100)}% — {ef.get('pattern', '')}"
            for ef in essay_feedbacks
        )
        essay_text = f"\nHasil essay:\n{essay_lines}"

    status = "lulus" if is_passed else "belum lulus"

    prompt = f"""Kamu adalah Armisa — AI tutor Sismind, gaya kakak tingkat yang santai dan supportif.

Siswa baru selesai ujian. Data hasil:
- Nama: {nickname}
- Nilai: {round(percentage)}% ({status})
- Mastery per topik:
{topic_lines}
- Topik yang salah: {wrong_text}{essay_text}

Tulis narasi post-exam untuk {nickname}. Aturan:
- 3-4 kalimat maksimal
- Tone: santai, supportif, tidak menghakimi
- Sebut 1 hal yang bagus SPESIFIK
- Sebut 1 hal yang perlu diperbaiki SPESIFIK
- JANGAN sebut angka persentase ke user
- JANGAN mulai dengan "Halo" atau "Hai" """

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.OPENROUTER_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.CHAT_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.5,
                    "max_tokens": 200,
                },
                timeout=15.0
            )
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"[PostExam] Narrator error: {e}")
            if is_passed:
                return f"Good job {nickname}! Ujian selesai dengan hasil yang bagus. Keep it up ya!"
            return f"Semangat {nickname}! Masih ada ruang buat improve, review topik yang salah tadi ya!"


@router.get("/{quiz_id}", response_model=QuizResponse)
async def get_quiz(
    quiz_id: str,
    user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db_session)
):
    """Get quiz details with questions."""
    quiz = db.query(Quiz).filter(
        Quiz.id == quiz_id,
        (Quiz.user_id == str(user.id)) | (Quiz.author_id == str(user.id))
    ).first()

    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )

    # Get questions
    questions = db.query(QuizQuestion).filter(
        QuizQuestion.quiz_id == quiz_id
    ).order_by(QuizQuestion.question_order).all()

    return {
        **{
            "id": quiz.id,
            "title": quiz.title,
            "narasi": quiz.narasi,
            "description": quiz.description,
            "subject": quiz.subject,
            "total_questions": quiz.total_questions,
            "difficulty": quiz.difficulty,
            "time_limit_minutes": quiz.time_limit_minutes,
            "status": quiz.status,
            "created_at": quiz.created_at
        },
        "questions": [
            {
                "id": q.id,
                "question_text": q.question_text,
                "question_type": q.question_type,
                "options": q.options,
                "difficulty": q.difficulty,
                "topic": q.topic
            }
            for q in questions
        ]
    }


@router.post("/{quiz_id}/questions", response_model=QuizQuestionResponse)
async def add_question(
    quiz_id: str,
    question_data: dict,
    user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db_session)
):
    """Add a question to quiz (raw dict for flexibility)."""
    quiz = db.query(Quiz).filter(
        Quiz.id == quiz_id,
        Quiz.author_id == str(user.id)
    ).first()

    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )

    question = QuizQuestion(
        id=str(uuid4()),
        quiz_id=quiz_id,
        question_text=question_data.get("question_text", ""),
        question_type=question_data.get("question_type", "mcq"),
        options=question_data.get("options"),
        correct_answer=question_data.get("correct_answer"),
        explanation=question_data.get("explanation"),
        difficulty=question_data.get("difficulty", "medium"),
        topic=question_data.get("topic"),
        question_order=len(db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz_id).all()) + 1
    )

    db.add(question)
    db.commit()
    db.refresh(question)

    return {
        "id": question.id,
        "question_text": question.question_text,
        "question_type": question.question_type,
        "options": question.options,
        "difficulty": question.difficulty,
        "topic": question.topic
    }


@router.post("/{quiz_id}/start", response_model=QuizResponse)
async def start_quiz(
    quiz_id: str,
    user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db_session)
):
    """Mark quiz as started."""
    quiz = db.query(Quiz).filter(
        Quiz.id == quiz_id,
        (Quiz.user_id == str(user.id)) | (Quiz.author_id == str(user.id))
    ).first()

    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )

    quiz.status = "active"
    quiz.started_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "id": quiz.id,
        "title": quiz.title,
        "description": quiz.description,
        "subject": quiz.subject,
        "total_questions": quiz.total_questions,
        "difficulty": quiz.difficulty,
        "time_limit_minutes": quiz.time_limit_minutes,
        "status": quiz.status,
        "created_at": quiz.created_at
    }

# @router.post("/{quiz_id}/submit", response_model=QuizSubmissionResponse)
# async def submit_quiz(
#     quiz_id: str,
#     submission_data: QuizSubmissionRequest,
#     user: User = Depends(get_current_user_from_token),
#     db: Session = Depends(get_db_session)
# ):
#     """
#     Final fixed version: Auto-update mastery, SM-2 implementation, and XP accumulation.
#     """
#     from app.db.models import MasteryScore, ChatSession, ChatMessage, QuestionSubmission

#     quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
#     if not quiz:
#         raise HTTPException(status_code=404, detail="Quiz not found")

#     questions = db.query(QuizQuestion).filter(
#         QuizQuestion.quiz_id == quiz_id
#     ).order_by(QuizQuestion.question_order).all()

#     # 1. Create submission record
#     submission = QuizSubmission(
#         id=str(uuid4()),
#         quiz_id=quiz_id,
#         user_id=str(user.id),
#         answers={str(a.question_id): a.answer for a in submission_data.answers},
#         started_at=datetime.now(timezone.utc)
#     )
#     db.add(submission)
#     db.flush()

#     # 2. Scoring Logic
#     correct_count = 0.0
#     per_topic_results = {}  
#     wrong_questions = []
#     essay_feedbacks = []  

#     for ans in submission_data.answers:
#         question = next((q for q in questions if q.id == ans.question_id), None)
#         if not question: 
#             continue

#         time_data = submission_data.time_per_question.get(str(ans.question_id), {})
#         # Safety check for dict access
#         time_spent = time_data.get("time_on_question", 0) if isinstance(time_data, dict) else 0
#         is_guessing = time_spent < 3
        
#         is_correct = False
#         error_meta = "none"
#         score_gain = 0.0

#         # --- MCQ Logic ---
#         if question.question_type == "mcq":
#             selected_option = next(
#                 (opt for i, opt in enumerate(question.options) if i == ans.answer), 
#                 None
#             )
        
#             if selected_option:
#                 is_correct = selected_option.get("is_correct", False)
#                 error_meta = selected_option.get("error_category", "none") if not is_correct else "none"

#                 # Score calculation with Guessing Penalty
#                 score_gain = 1.0 if is_correct else 0.0
#                 if is_guessing and is_correct: 
#                     score_gain = 0.5 
                
#                 correct_count += score_gain
                
#                 if not is_correct:
#                     wrong_questions.append({
#                         "question_id": str(question.id),
#                         "topic": question.topic,
#                         "question_text": question.question_text[:100],
#                         "error_type": error_meta
#                     })

#         # --- Essay Logic ---
#         elif question.question_type == "essay":
#             # Optimized: Single AI call
#             essay_res = score_essay_answer(
#                 question.question_text, 
#                 str(ans.answer) if ans.answer else "", 
#                 question.correct_answer or question.explanation or "", 
#                 question.topic or "General"
#             )
            
#             score_gain = essay_res["score"] # Scalar value 0.0 - 1.0
#             is_correct = score_gain >= 0.7
#             error_meta = essay_res["pattern"]
            
#             correct_count += score_gain

#             essay_feedbacks.append({
#                 "question_id": str(question.id),
#                 "topic": question.topic,
#                 "score": score_gain,
#                 "feedback": essay_res["feedback"],
#                 "pattern": error_meta
#             })
            
#             if not is_correct:
#                 wrong_questions.append({
#                     "question_id": str(question.id),
#                     "topic": question.topic,
#                     "question_text": question.question_text[:100],
#                     "error_type": "conceptual"
#                 })

#         # 3. Aggregate results per topic
#         topic = question.topic or "General"
#         if topic not in per_topic_results:
#             per_topic_results[topic] = {"correct": 0.0, "total": 0}

#         per_topic_results[topic]["total"] += 1
#         per_topic_results[topic]["correct"] += score_gain

#         # Save individual question history
#         db.add(QuestionSubmission(
#             id=str(uuid4()),
#             submission_id=submission.id,
#             question_id=question.id,
#             user_answer=ans.answer,
#             is_correct=is_correct,
#             error_metadata={"category": error_meta, "is_guessing": is_guessing, "score": score_gain}
#         ))

@router.post("/{quiz_id}/submit")
async def submit_quiz(
    quiz_id: str,
    submission_data: QuizSubmissionRequest,
    user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db_session)
):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    questions = db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz_id).all()

    # 1. Inisialisasi Submission
    submission = QuizSubmission(
        id=str(uuid4()),
        quiz_id=quiz_id,
        user_id=str(user.id),
        answers={str(a.question_id): a.answer for a in submission_data.answers},
        started_at=datetime.now(timezone.utc),
        status="processing"
    )
    db.add(submission)
    db.flush()

    # 2. Save Individual Answers Mentah (Tidak perlu hitung benar/salah di sini)
    for ans in submission_data.answers:
        question = next((q for q in questions if str(q.id) == str(ans.question_id)), None)
        if not question: continue

        db.add(QuestionSubmission(
            id=str(uuid4()),
            submission_id=submission.id,
            question_id=question.id,
            user_answer=ans.answer,
            is_correct=False, # Akan di-update oleh engine nanti
            error_metadata={"is_guessing": False}
        ))
        
    # WAJIB COMMIT agar ScoringEngine bisa menemukan data jawaban esai!
    db.commit()

    # 3. Triger AI Scoring Engine (Engine ini yang mikir 100% dan update DB)
    try:
        engine_result = await ScoringEngine.score_exam(quiz_id=quiz_id, user_id=str(user.id), db=db)
    except Exception as e:
        logger.error(f"Scoring failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Gagal memproses nilai ujian.")

    # 4. Award XP & Level
    final_score = engine_result.get("final_score", 0)
    xp_gained = max(10, int(final_score / 10) * 5)
    user.total_xp = (user.total_xp or 0) + xp_gained
    user.level = (user.total_xp // 100) + 1
    db.commit()

    # 5. Sesuaikan parameter output untuk Frontend UI
    engine_result["max_score"] = len(questions)
    engine_result["total_questions"] = len(questions)
    engine_result["score"] = engine_result.get("correct_answers", 0)
    engine_result["performance_metrics"]["xp_gained"] = xp_gained

    # RETURN ABSOLUT dari engine, jangan di-rebuild ulang JSON-nya!
    return engine_result
@router.get("/{quiz_id}/submissions")
async def get_quiz_submissions(
    quiz_id: str,
    user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db_session)
):
    """Get all submissions for a quiz (teacher view)."""
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )

    submissions = db.query(QuizSubmission).filter(
        QuizSubmission.quiz_id == quiz_id
    ).all()

    return [
        {
            "id": s.id,
            "user_id": s.user_id,
            "score": s.score,
            "max_score": s.max_score,
            "percentage": s.percentage,
            "submitted_at": s.submitted_at
        }
        for s in submissions
    ]


@router.get("/", response_model=list[QuizResponse])
async def list_quizzes(
    subject: Optional[str] = None,
    status_filter: Optional[str] = None,
    user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db_session)
):
    """List quizzes for the user."""
    query = db.query(Quiz).filter(
        (Quiz.user_id == str(user.id)) | (Quiz.author_id == str(user.id))
    )

    if subject:
        query = query.filter(Quiz.subject == subject)

    if status_filter:
        query = query.filter(Quiz.status == status_filter)

    quizzes = query.all()

    return [
        {
            "id": q.id,
            "title": q.title,
            "description": q.description,
            "narasi": q.narasi,
            "subject": q.subject,
            "total_questions": q.total_questions,
            "difficulty": q.difficulty,
            "status": q.status,
            "created_at": q.created_at
        }
        for q in quizzes
    ]
