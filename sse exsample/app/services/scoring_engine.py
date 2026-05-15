"""
Scoring Engine
==============
Deterministic mastery scoring pipeline.

Architecture (dari scoring_architecture.docx):
- Layer 1: Kode — preprocessing & agregasi per dimensi
- Layer 2: LLM — parse dimensi kualitatif → angka 0-1
- Layer 3: Kode — weighted formula → final score
- Layer 4: LLM — narasi untuk user

Final score SELALU dari kode, bukan LLM.

CHANGELOG (Bug Fixes):
- [FIX 1] MCQ Accuracy: Kalkulasi dinamis berbasis proporsi, bukan hardcode 0.7/0.3
- [FIX 2] Scoring Formula: Accuracy sebagai Base Score (0-100), trajectory & consistency sebagai bonus
- [FIX 3] Topics Sanitization: Sanitasi topics sebelum dilempar ke Layer 4
- [FIX 4] Empty Essay Bypass: Jawaban esai kosong langsung score 0.0 tanpa panggil AI
- [FIX 5] Save Essay Feedback: Feedback AI disimpan ke kolom post_narasi di QuestionSubmission
- [FIX 6] Smart Name Fallback: nickname → first word full_name → username → "Siswa"
- [FIX 7] Sub-topic Weakness: Identifikasi weak_topics (accuracy < 60%) per sub-topik
- [FIX 9]  Denominator Mismatch: denominator = len(questions) dari DB, bukan mcq+essay
- [FIX 10] Case-Insensitive Type Filter: "MCQ"/"Essay" typo tidak lagi lolos dari radar
- [FIX 11] wrong_mcq_subs log: soal tipe tidak dikenal di-warning ke logger
"""

import asyncio
import json
import logging
import httpx
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
import re

from app.core.config import get_settings
from app.db.models import (
    MasteryScore, QuizSubmission, QuizQuestion,
    QuestionSubmission, Quiz, ChatSession, RoomInsight, User
)

settings = get_settings()
logger = logging.getLogger(__name__)


# ================================================================
# CONSTANTS
# ================================================================

QUESTION_TIER_WEIGHTS = {
    "essay":        1.00,
    "mcq_complex":  0.75,
    "mcq_simple":   0.50,
    "mcq":          0.50,
}

# [FIX 2] Penalty & Bonus dalam satuan poin (0–100), bukan multiplier 0–1
ERROR_TYPE_PENALTY_POINTS = {
    "systematic": 10,   # Kurangi 10 poin
    "random":      5,   # Kurangi 5 poin
    "none":        0,
}

TRAJECTORY_BONUS_POINTS = {
    "high":    5,   # trajectory_val > 0.7 → +5 poin
    "medium":  2,   # trajectory_val > 0.5 → +2 poin
    "low":     0,
}

CONSISTENCY_BONUS_POINTS = {
    "high":    3,   # consistency_val >= 0.8 → +3 poin
    "medium":  1,   # consistency_val >= 0.5 → +1 poin
    "low":     0,
}

# Semaphore: maks 5 request AI bersamaan
semaphore = asyncio.Semaphore(5)


# ================================================================
# DATA STRUCTURES
# ================================================================

class RawExamData:
    """Container untuk raw data dari exam submission."""
    def __init__(
        self,
        quiz_id: str,
        user_id: str,
        questions: list,
        answers: list,
        attempt_number: int,
        previous_attempts: list,
        time_per_question: dict,
        streak_days: int,
        days_since_last_exam: int,
        chat_signal_score: float,
        essay_answers: list,
    ):
        self.quiz_id = quiz_id
        self.user_id = user_id
        self.questions = questions
        self.answers = answers
        self.attempt_number = attempt_number
        self.previous_attempts = previous_attempts
        self.time_per_question = time_per_question
        self.streak_days = streak_days
        self.days_since_last_exam = days_since_last_exam
        self.chat_signal_score = chat_signal_score
        self.essay_answers = essay_answers


class DimensionScores:
    """Container untuk scores per dimensi sebelum masuk weighted formula."""
    def __init__(self):
        self.weighted_accuracy: float = 0.0
        self.conceptual_clarity: float = 0.0
        self.error_pattern: float = 0.0
        self.improvement_trajectory: float = 0.0
        self.consistency: float = 0.0
        self.engagement: float = 0.0
        self.error_type: str = "random"
        self.error_details: dict = {}
        self.essay_scores: list = []


# ================================================================
# LAYER 1 — PREPROCESSING (DETERMINISTIC MATH)
# ================================================================
class Layer1Preprocessor:

    @staticmethod
    def calculate_improvement_trajectory(current_score: float, previous_attempts: list) -> float:
        if not previous_attempts:
            return 0.5  # Neutral jika belum ada histori

        all_scores = previous_attempts + [current_score]
        improvements = [all_scores[i+1] - all_scores[i] for i in range(len(all_scores) - 1)]
        avg_improvement = sum(improvements) / len(improvements)

        if avg_improvement > 0.10:    return 0.90
        elif avg_improvement > 0.0:   return 0.70
        elif avg_improvement > -0.05: return 0.40
        else:                          return 0.20

    @staticmethod
    def calculate_consistency(streak_days: int) -> float:
        if streak_days >= 14: return 1.0
        elif streak_days >= 7: return 0.8
        elif streak_days >= 3: return 0.5
        elif streak_days >= 1: return 0.2
        return 0.0

    # [FIX DENOMINATOR] Denominator = total semua soal dari DB, bukan MCQ+esai saja
    @staticmethod
    def calculate_weighted_accuracy(
        mcq_correct: int,
        total_all_questions: int,   # len(questions) — seluruh soal tanpa filter tipe
        essay_scores: list          # list of float (0.0–1.0 per soal esai)
    ) -> float:
        """
        weighted_accuracy = (Benar MCQ + Akumulasi Skor Esai) / TOTAL SEMUA SOAL

        Denominator pakai total_all_questions (bukan mcq_total + essay_total) sehingga
        soal dengan tipe tidak dikenal / typo tetap dihitung sebagai soal yang ada,
        mencegah pembagian ke angka yang lebih kecil dari seharusnya.
        """
        if total_all_questions == 0:
            return 0.0

        total_earned = mcq_correct + sum(essay_scores)
        return total_earned / total_all_questions


# ================================================================
# LAYER 2 — LLM PARSERS (ROBUST JSON EXTRACTION)
# ================================================================
class Layer2LLMParser:

    @staticmethod
    def _extract_json_safely(raw_text: str) -> str:
        """Bersihkan tag <think> dan markdown agar aman di-parse."""
        # 1. Hapus tag <think> bawaan model reasoning
        clean_text = re.sub(r'<think>.*?</think>', '', raw_text, flags=re.DOTALL).strip()

        # 2. Ekstrak dari kurung kurawal pertama sampai terakhir
        start_idx = clean_text.find('{')
        end_idx = clean_text.rfind('}') + 1

        if start_idx != -1 and end_idx != 0:
            return clean_text[start_idx:end_idx]

        # 3. Fallback bersihkan markdown biasa
        return clean_text.replace("```json", "").replace("```", "").strip()

    @staticmethod
    async def _call_llm_async(prompt: str, temperature: float = 0.1) -> str:
        async with semaphore:
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.post(
                        f"{settings.OPENROUTER_BASE_URL}/chat/completions",
                        headers={"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}"},
                        json={
                            "model": settings.CHAT_MODEL,
                            "messages": [{"role": "user", "content": prompt}],
                            "temperature": temperature,
                        },
                        timeout=60.0
                    )
                    data = response.json()

                    if "error" in data:
                        logger.error(f"[Layer2] OpenRouter Error: {data['error']}")
                        return "{}"

                    if "choices" not in data or len(data["choices"]) == 0:
                        logger.error(f"[Layer2] Balasan API tidak valid: {data}")
                        return "{}"

                    return data["choices"][0]["message"]["content"]
                except Exception as e:
                    logger.error(f"[Layer2] Request ke API Gagal: {e}")
                    return "{}"

    @staticmethod
    async def parse_essay_scores(essay_inputs: list) -> list:
        """
        [FIX 4] Jawaban esai kosong langsung diberi score 0.0 tanpa memanggil AI,
        menghemat token dan menghindari pemborosan API quota.
        """
        if not essay_inputs:
            return []

        results = []
        # Pisahkan soal yang perlu dinilai AI vs yang langsung 0
        ai_indices = []      # index di essay_inputs yang perlu dinilai AI
        ai_inputs = []       # subset essay_inputs untuk AI

        for i, item in enumerate(essay_inputs):
            answer = (item.get("answer") or "").strip()
            if not answer:
                # [FIX 4] Bypass AI, langsung beri nilai 0
                results.append({
                    "score": 0.0,
                    "feedback": "Jawaban kosong.",
                    "topic": "General",
                    "_original_index": i
                })
            else:
                ai_indices.append(i)
                ai_inputs.append(item)
                results.append(None)  # placeholder

        # Panggil AI hanya jika ada soal yang perlu dinilai
        if ai_inputs:
            prompt = """Evaluate student essays. You MUST return ONLY a JSON object exactly in this format:
{"results": [{"score": 0.0, "feedback": "...", "topic": "..."}]}
Score is between 0.0 and 1.0. Even if the answer is short (1-2 words), evaluate its correctness based on the Key. Do not write anything outside the JSON.
"""
            for i, item in enumerate(ai_inputs):
                prompt += f"\n\n--- Essay {i+1} ---\nQuestion: {item['question']}\nStudent Answer: {item['answer']}\nCorrect Key: {item['explanation']}"

            raw = await Layer2LLMParser._call_llm_async(prompt)
            try:
                clean_raw = Layer2LLMParser._extract_json_safely(raw)
                data = json.loads(clean_raw)
                ai_results = data.get("results", [])

                if len(ai_results) != len(ai_inputs):
                    ai_results = [
                        {"score": 0.0, "feedback": "AI gagal menilai format jawaban.", "topic": "General"}
                        for _ in ai_inputs
                    ]
            except Exception as e:
                logger.error(f"[Layer2] Essay Parse Error: {e} | Raw Reply: {raw[:100]}")
                ai_results = [
                    {"score": 0.0, "feedback": "Gagal diproses AI. Jawaban kamu telah direkam.", "topic": "General"}
                    for _ in ai_inputs
                ]

            # Isi kembali placeholder dengan hasil AI
            for idx_in_ai, original_idx in enumerate(ai_indices):
                results[original_idx] = ai_results[idx_in_ai]

        return results

    @staticmethod
    async def parse_error_pattern(wrong_answers: list, questions: list) -> dict:
        if not wrong_answers:
            return {"error_type": "none", "pattern_description": "Jawaban sempurna."}

        q_texts = [
            next((q.question_text[:100] for q in questions if str(q.id) == str(ans.question_id)), "Unknown")
            for ans in wrong_answers
        ]
        prompt = f"""Analyze these incorrect questions: {q_texts}. 
Return ONLY a JSON object: {{"error_type": "systematic" or "random", "pattern_description": "Short explanation of their weakness"}}"""

        raw = await Layer2LLMParser._call_llm_async(prompt)
        try:
            clean_raw = Layer2LLMParser._extract_json_safely(raw)
            return json.loads(clean_raw)
        except:
            return {"error_type": "random", "pattern_description": "Pola kesalahan bervariasi."}


# ================================================================
# LAYER 4 — NARRATOR (PERSONALIZED FEEDBACK)
# ================================================================
class Layer4Narrator:

    # [FIX 3] Sanitasi topics menjadi list of strings yang bersih
    @staticmethod
    def _sanitize_topics(topics) -> list:
        """
        Pastikan topics selalu berupa list of strings.
        Menangani kasus di mana topics adalah string tunggal dengan koma
        atau format lain dari exam_config database.
        """
        if not topics:
            return ["General"]

        # Jika string tunggal, split by koma
        if isinstance(topics, str):
            return [t.strip() for t in topics.split(",") if t.strip()]

        # Jika list, pastikan setiap item adalah string
        if isinstance(topics, list):
            cleaned = []
            for t in topics:
                if isinstance(t, str):
                    cleaned.append(t.strip())
                elif t is not None:
                    cleaned.append(str(t).strip())
            return [t for t in cleaned if t] or ["General"]

        # Fallback
        return [str(topics)]

    @staticmethod
    async def generate_result_narrative(
        final_score: int,
        error_pattern: dict,
        nickname: str,
        trajectory_val: float,
        topics,                     # bisa str atau list — akan disanitasi
        score_breakdown: dict,      # [NEW] {"base_score", "penalty_points", "bonus_points"}
        wrong_q_summaries: list,    # [NEW] Max 3 ringkasan soal yang salah
        weak_topics: list           # [NEW] Sub-topik dengan akurasi < 60%
    ) -> str:
        # [FIX 3] Sanitasi sebelum dikirim ke AI
        clean_topics = Layer4Narrator._sanitize_topics(topics)

        trend = "meningkat 📈" if trajectory_val > 0.6 else "butuh fokus 📉" if trajectory_val < 0.4 else "stabil"

        # Format bullet soal salah & topik lemah untuk prompt
        wrong_list = "\n".join([f"- {q}" for q in wrong_q_summaries]) if wrong_q_summaries else "- Nilai sempurna di MCQ!"
        weak_list  = ", ".join(weak_topics) if weak_topics else "Tidak ada"

        prompt = f"""Kamu adalah Armisa, AI Tutor Sismind.id.
Siswa: {nickname} | Fokus: {clean_topics}
Skor Akhir: {final_score}/100 | Trend: {trend}

[ANALISA SISTEM]
- Base Accuracy: {score_breakdown['base_score']}
- Penalty (Concept Error): -{score_breakdown['penalty_points']}
- Bonus (Growth/Streak): +{score_breakdown['bonus_points']}
- Weak Sub-topics: {weak_list}
- Pattern: {error_pattern.get('pattern_description')}
- Sample Wrong Questions:
{wrong_list}

Tugas: Tulis review performa dalam 2 paragraf santai (Indo-English mix).
Paragraf 1: Bedah kenapa skornya bisa {final_score}. Sebutkan pengaruh akurasi dan pinalti/bonusnya secara logis.
Paragraf 2 (Judul "📌 Area Evaluasi:"): Sebutkan sub-topik {weak_list} dan jelaskan kenapa soal yang salah itu penting untuk diperbaiki."""

        raw = await Layer2LLMParser._call_llm_async(prompt, temperature=0.7)
        # Bersihkan tag <think> — output teks bebas, tidak perlu parse JSON
        return re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL).strip()

    @staticmethod
    async def generate_difficulty_recommendation(
        final_score: int,
        topics  # bisa str atau list — akan disanitasi
    ) -> dict:
        # [FIX 3] Sanitasi sebelum dikirim ke AI
        clean_topics = Layer4Narrator._sanitize_topics(topics)

        prompt = f"""Based on score {final_score}/100 in topics {clean_topics}, suggest next difficulty.
Return ONLY JSON: {{"recommended_difficulty": "easy"|"medium"|"hard", "focus_topics": ["topic1"]}}"""

        raw = await Layer2LLMParser._call_llm_async(prompt)
        try:
            clean_raw = Layer2LLMParser._extract_json_safely(raw)
            return json.loads(clean_raw)
        except:
            rec = "hard" if final_score >= 80 else "easy" if final_score < 60 else "medium"
            return {"recommended_difficulty": rec, "focus_topics": clean_topics[:1]}


# ================================================================
# MAIN ORCHESTRATOR
# ================================================================
class ScoringEngine:
    @staticmethod
    async def score_exam(quiz_id: str, user_id: str, db: Session):
        logger.info(f"[ScoringEngine] Executing Full Parallel Scoring for Quiz {quiz_id}")

        # ─── 1. DATA GATHERING ───
        quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
        submission = (
            db.query(QuizSubmission)
            .filter(QuizSubmission.quiz_id == quiz_id, QuizSubmission.user_id == user_id)
            .order_by(QuizSubmission.created_at.desc())
            .first()
        )
        questions = db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz_id).all()
        user_subs = db.query(QuestionSubmission).filter(QuestionSubmission.submission_id == submission.id).all()

        if not quiz or not submission:
            raise ValueError("Kuis atau data submission tidak ditemukan.")

        essay_inputs = []           # untuk AI
        essay_question_ids = []     # mapping: index → question_id (untuk FIX 5)
        wrong_mcq_subs = []

        # [FIX CASING] Normalisasi question_type ke lowercase agar kebal typo ("MCQ", "Essay", dll.)
        mcq_questions   = [q for q in questions if (q.question_type or "").lower() == "mcq"]
        essay_questions = [q for q in questions if (q.question_type or "").lower() == "essay"]

        # Deteksi soal dengan tipe tidak dikenal — tetap dihitung di denominator, tapi di-log
        known_types = {"mcq", "essay"}
        unknown_type_qs = [q for q in questions if (q.question_type or "").lower() not in known_types]
        if unknown_type_qs:
            logger.warning(
                f"[ScoringEngine] {len(unknown_type_qs)} soal tipe tidak dikenal "
                f"(masuk denominator sebagai salah): "
                f"{[(str(q.id), q.question_type) for q in unknown_type_qs]}"
            )

        for q in mcq_questions:
            ans = next((s for s in user_subs if str(s.question_id) == str(q.id)), None)
            if ans and not ans.is_correct:
                wrong_mcq_subs.append(ans)

        for q in essay_questions:
            ans = next((s for s in user_subs if str(s.question_id) == str(q.id)), None)
            essay_inputs.append({
                "question": q.question_text,
                # [FIX 4] Kosong tetap dimasukkan ke list tapi akan di-bypass di parse_essay_scores
                "answer": str(ans.user_answer).strip() if ans and ans.user_answer else "",
                "explanation": q.correct_answer or q.explanation or ""
            })
            essay_question_ids.append(str(q.id))

        # ─── 2. PARALLEL ANALYSIS (Layer 2) ───
        analysis_tasks = [
            Layer2LLMParser.parse_essay_scores(essay_inputs),
            Layer2LLMParser.parse_error_pattern(wrong_mcq_subs, questions)
        ]
        essay_results, error_pattern = await asyncio.gather(*analysis_tasks)

        if not isinstance(essay_results, list):
            essay_results = [{"score": 0.0, "feedback": "Fallback: Penilaian gagal.", "topic": "General"}] * len(essay_inputs)

        if not isinstance(error_pattern, dict):
            error_pattern = {"error_type": "random", "pattern_description": "Pola kesalahan tidak diketahui."}

        # ─── 3. COMPLEX MATH (Layer 1 & 3) ───

        # [FIX 1] Hitung MCQ benar
        mcq_correct_count = sum(
            1 for s in user_subs
            if s.is_correct and any(str(q.id) == str(s.question_id) for q in mcq_questions)
        )

        # [FIX 1] Ambil skor esai per soal sebagai list float
        essay_score_list = [r.get("score", 0.0) for r in essay_results]

        # [FIX DENOMINATOR] Akurasi gabungan: denominator = semua soal di DB (bukan mcq+essay saja)
        weighted_accuracy = Layer1Preprocessor.calculate_weighted_accuracy(
            mcq_correct=mcq_correct_count,
            total_all_questions=len(questions),   # ← denominator utama: total soal dari DB
            essay_scores=essay_score_list
        )

        # Trajectory & Consistency
        user_obj = db.query(User).filter(User.id == user_id).first()
        prev_scores = [
            s.percentage / 100
            for s in db.query(QuizSubmission)
            .filter(QuizSubmission.user_id == user_id, QuizSubmission.status == "completed")
            .order_by(QuizSubmission.created_at.desc())
            .limit(5)
            .all()
            if s.percentage
        ]

        trajectory_val = Layer1Preprocessor.calculate_improvement_trajectory(weighted_accuracy, prev_scores)
        consistency_val = Layer1Preprocessor.calculate_consistency(getattr(user_obj, 'current_streak', 0))

        # [FIX 2] Formula Baru: Base Score murni dari accuracy
        base_score = round(weighted_accuracy * 100)

        # [FIX 2] Penalty dari pola error (dalam poin)
        error_type = error_pattern.get("error_type", "random")
        penalty_points = ERROR_TYPE_PENALTY_POINTS.get(error_type, 5)

        # [FIX 2] Bonus dari trajectory
        if trajectory_val > 0.7:
            trajectory_bonus = TRAJECTORY_BONUS_POINTS["high"]
        elif trajectory_val > 0.5:
            trajectory_bonus = TRAJECTORY_BONUS_POINTS["medium"]
        else:
            trajectory_bonus = TRAJECTORY_BONUS_POINTS["low"]

        # [FIX 2] Bonus dari consistency
        if consistency_val >= 0.8:
            consistency_bonus = CONSISTENCY_BONUS_POINTS["high"]
        elif consistency_val >= 0.5:
            consistency_bonus = CONSISTENCY_BONUS_POINTS["medium"]
        else:
            consistency_bonus = CONSISTENCY_BONUS_POINTS["low"]

        # [FIX 2] Final Score = Base - Penalty + Bonus, di-cap 0–100
        final_score = max(0, min(100, base_score - penalty_points + trajectory_bonus + consistency_bonus))

        logger.info(
            f"[ScoringEngine] Score breakdown — base: {base_score}, "
            f"penalty: -{penalty_points}, traj_bonus: +{trajectory_bonus}, "
            f"consist_bonus: +{consistency_bonus}, final: {final_score}"
        )

        # ─── 4. PARALLEL NARRATION (Layer 4) ───
        # [FIX 3] Sanitasi topics sebelum diteruskan ke Layer 4
        raw_topics = quiz.exam_config.get("topics", [quiz.subject]) if quiz.exam_config else [quiz.subject]
        topics = Layer4Narrator._sanitize_topics(raw_topics)

        # [NEW] Identifikasi sub-topik lemah (accuracy < 60%)
        unique_topics = list(set([q.topic for q in questions if q.topic]))
        weak_topics = [
            t for t in unique_topics
            if _get_topic_accuracy(t, questions, user_subs) < 0.6
        ]

        # [NEW] Ringkasan max 3 soal MCQ yang salah untuk bahan evaluasi AI
        wrong_q_summaries = [
            f"{q.question_text[:60]}... (Materi: {q.topic})"
            for q in mcq_questions
            for s in wrong_mcq_subs
            if str(s.question_id) == str(q.id)
        ][:3]

        # [NEW] Breakdown angka yang akan dijelaskan Armisa secara transparan
        score_breakdown = {
            "base_score": base_score,
            "penalty_points": penalty_points,
            "bonus_points": trajectory_bonus + consistency_bonus,
        }

        # [FIX NAME] Fallback cerdas: nickname → first word of full_name → username → "Siswa"
        user_display_name = (
            user_obj.nickname
            or (user_obj.full_name.split()[0] if getattr(user_obj, "full_name", None) else None)
            or getattr(user_obj, "username", None)
            or "Siswa"
        )

        narration_tasks = [
            Layer4Narrator.generate_result_narrative(
                final_score, error_pattern,
                user_display_name,
                trajectory_val, topics,
                score_breakdown, wrong_q_summaries, weak_topics  # DATA LENGKAP
            ),
            Layer4Narrator.generate_difficulty_recommendation(final_score, topics)
        ]

        try:
            narrative, recommendation = await asyncio.gather(*narration_tasks)
        except Exception as e:
            logger.error(f"[ScoringEngine] Layer 4 Error: {e}")
            narrative = f"Ujian selesai! Skor akhir kamu {final_score}/100."
            recommendation = {"recommended_difficulty": "medium", "focus_topics": topics[:1]}

        # ─── 5. PERSISTENCE ───
        good_essays_count = sum(1 for res in essay_results if res.get("score", 0) >= 0.6)
        total_correct_for_ui = mcq_correct_count + good_essays_count

        submission.score = float(final_score)
        submission.percentage = float(final_score)
        submission.post_narasi = narrative
        submission.status = "completed"
        submission.submitted_at = datetime.now(timezone.utc)
        submission.performance_metrics = {
            "error_pattern": error_pattern,
            "recommendation": recommendation,
            "essay_feedbacks": essay_results,
            "components": {
                "accuracy": weighted_accuracy,
                "trajectory": trajectory_val,
                "consistency": consistency_val,
                "base_score": base_score,
                "penalty_points": penalty_points,
                "trajectory_bonus": trajectory_bonus,
                "consistency_bonus": consistency_bonus,
            }
        }

        quiz.status = "completed"
        quiz.completed_at = datetime.now(timezone.utc)

        # [FIX 5] Simpan feedback esai per soal ke tabel QuestionSubmission
        # agar halaman "Review Jawaban" bisa merender narasi per soal
        if essay_results and essay_question_ids:
            for idx, qid in enumerate(essay_question_ids):
                if idx >= len(essay_results):
                    break

                essay_result = essay_results[idx]
                qs_row = next(
                    (s for s in user_subs if str(s.question_id) == qid),
                    None
                )
                if qs_row:
                    essay_score = essay_result.get("score", 0.0)
                    qs_row.post_narasi = essay_result.get("feedback", "")
                    qs_row.is_correct = essay_score >= 0.6
                    # Simpan skor numerik jika kolom tersedia
                    if hasattr(qs_row, "score"):
                        qs_row.score = essay_score

        db.commit()

        return {
            "submission_id": str(submission.id),
            "final_score": final_score,
            "narrative": narrative,
            "percentage": final_score,
            "correct_answers": total_correct_for_ui,
            "passing_score": 60,
            "post_narasi": narrative,
            "performance_metrics": submission.performance_metrics,
        }


# ================================================================
# HELPER UTILITIES
# ================================================================

def _get_topic_accuracy(
    topic: str,
    questions: list,
    answers: list
) -> float:
    """Hitung accuracy untuk 1 topik spesifik."""
    topic_questions = [q for q in questions if q.topic == topic]
    if not topic_questions:
        return 0.5

    correct = 0
    total = 0
    for q in topic_questions:
        ans = next(
            (a for a in answers if str(a.question_id) == str(q.id)),
            None
        )
        if ans:
            total += 1
            if ans.is_correct:
                correct += 1

    return correct / total if total > 0 else 0.5