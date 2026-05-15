"""
Progress & Analytics Endpoints
===============================
XP tracking, level progression, and learning statistics
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db_session
from app.db.models import User, ProgressLog, MasteryScore
from app.models.schemas import ProgressStats, ProgressUpdate
from app.api.deps import get_current_user_from_token

router = APIRouter(prefix="/progress", tags=["Progress"])


class ProgressService:
    """Service class for progress management."""

    def __init__(self, db: Session):
        self.db = db

    def get_or_create_log(self, user_id: str) -> ProgressLog:
        """Get or create progress log for user."""
        log = self.db.query(ProgressLog).filter(
            ProgressLog.user_id == user_id
        ).order_by(ProgressLog.created_at.desc()).first()

        if not log:
            log = ProgressLog(
                id=str(user_id),  # Use user_id as log_id for MVP
                user_id=user_id,
                total_xp=0,
                level=1
            )
            self.db.add(log)
            self.db.commit()

        return log

    def update_xp(self, user_id: str, xp_gained: int, session_type: str,
                  topics_engaged: Optional[List[str]] = None):
        """Update user XP and progress."""
        log = self.get_or_create_log(user_id)

        # Update XP
        log.xp_earned = xp_gained
        log.total_xp += xp_gained
        log.session_type = session_type
        log.topics_engaged = topics_engaged or []

        # Calculate level (simple: level = total_xp // 100)
        log.level = 1 + (log.total_xp // 100)

        self.db.commit()

    def get_stats(self, user_id: str) -> ProgressStats:
        """Get user progress statistics."""
        log = self.db.query(ProgressLog).filter(
            ProgressLog.user_id == user_id
        ).order_by(ProgressLog.created_at.desc()).first()

        if not log:
            return ProgressStats(
                level=1,
                total_xp=0,
                sessions_completed=0,
                correct_answers=0,
                inaccurate_answers=0,
                accuracy=None,
                streak=0
            )

        # Get recent session history
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        recent_logs = self.db.query(ProgressLog).filter(
            ProgressLog.user_id == user_id,
            ProgressLog.created_at >= seven_days_ago
        ).count()

        # Calculate streak (simplified)
        streak = 1 if recent_logs > 0 else 0

        # Calculate accuracy (simplified)
        accuracy = None
        total = log.correct_answers + log.incorrect_answers
        if total > 0:
            accuracy = (log.correct_answers / total) * 100

        return ProgressStats(
            level=log.level,
            total_xp=log.total_xp,
            sessions_completed=recent_logs,
            correct_answers=log.correct_answers,
            inaccurate_answers=log.incorrect_answers,
            accuracy=round(accuracy, 2) if accuracy else None,
            streak=streak,
            current_topic=log.topics_engaged[-1] if log.topics_engaged else None
        )

    def get_mastery_scores(self, user_id: str, subject: Optional[str] = None) -> List[dict]:
        """Get mastery scores per topic."""
        query = self.db.query(MasteryScore).filter(
            MasteryScore.user_id == user_id
        )

        if subject:
            query = query.filter(MasteryScore.subject == subject)

        scores = query.all()

        return [
            {
                "topic": s.topic,
                "subject": s.subject,
                "mastery_score": s.mastery_score,
                "confidence": s.confidence,
                "times_practiced": s.times_practiced,
                "next_review_at": s.next_review_at
            }
            for s in scores
        ]

    def update_mastery(self, user_id: str, topic: str, subject: str,
                       is_correct: bool, difficulty: str):
        """Update mastery score using Bayesian Knowledge Tracing (simplified)."""
        mastery = self.db.query(MasteryScore).filter(
            MasteryScore.user_id == user_id,
            MasteryScore.topic == topic
        ).first()

        # Simplified BKT update
        if not mastery:
            mastery = MasteryScore(
                id=str(user_id) + "_" + topic,
                user_id=user_id,
                topic=topic,
                subject=subject,
                mastery_score=0.3,  # Initial belief
                confidence=0.1,
                times_practiced=0
            )
            self.db.add(mastery)

        # Update mastery based on answer
        if is_correct:
            mastery.mastery_score = min(1.0, mastery.mastery_score + 0.1)
            mastery.times_practiced += 1
        else:
            mastery.mastery_score = max(0.0, mastery.mastery_score - 0.1)

        mastery.last_practiced_at = datetime.now(timezone.utc)

        # Set next review time (spaced repetition - simplified)
        if mastery.mastery_score > 0.7:
            mastery.next_review_at = datetime.now(timezone.utc) + timedelta(days=7)
        elif mastery.mastery_score > 0.4:
            mastery.next_review_at = datetime.now(timezone.utc) + timedelta(days=3)
        else:
            mastery.next_review_at = datetime.now(timezone.utc) + timedelta(hours=24)

        self.db.commit()
        return mastery


@router.get("/stats", response_model=ProgressStats)
async def get_progress_stats(
    user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db_session)
):
    """Get current user progress statistics."""
    service = ProgressService(db)
    return service.get_stats(str(user.id))


@router.post("/update")
async def update_progress(
    update_data: ProgressUpdate,
    user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db_session)
):
    """Manually update user progress (useful for offline XP calculation)."""
    service = ProgressService(db)
    service.update_xp(
        str(user.id),
        update_data.xp_gained,
        update_data.session_type,
        update_data.topics_engaged
    )

    return {"message": "Progress updated", "new_xp": update_data.xp_gained}


@router.get("/mastery")
async def get_mastery(
    user: User = Depends(get_current_user_from_token),
    subject: Optional[str] = None,
    db: Session = Depends(get_db_session)
):
    """Get mastery scores per topic."""
    service = ProgressService(db)
    return service.get_mastery_scores(str(user.id), subject)


@router.get("/dashboard")
async def get_dashboard(
    user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db_session)
):
    """Get comprehensive dashboard data."""
    service = ProgressService(db)

    stats = service.get_stats(str(user.id))
    mastery = service.get_mastery_scores(str(user.id))

    # Mock gamification data
    next_level_xp = (stats.level + 1) * 100
    xp_to_next = next_level_xp - stats.total_xp

    return {
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role
        },
        "stats": stats,
        "level_info": {
            "current_level": stats.level,
            "total_xp": stats.total_xp,
            "xp_to_next_level": xp_to_next,
            "level_progress": (stats.total_xp / next_level_xp) * 100
        },
        "mastery": mastery,
        "achievements": [],  # Ready for future implementation
        "streak_info": {
            "current_streak": stats.streak,
            "best_streak": stats.streak,  # Placeholder
            "total_sessions": stats.sessions_completed
        }
    }
