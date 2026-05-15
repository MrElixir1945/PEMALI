"""
Database Models
==============
SQLAlchemy ORM models — compatible with both SQLite and PostgreSQL
"""

from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Date, Text, Float,
    ForeignKey, Enum as SQLEnum, UniqueConstraint, Index,
    JSON
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, ARRAY
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.types import TypeDecorator, CHAR
import uuid
import enum


# Custom SQLite-compatible UUID and Array implementations
class GUID(TypeDecorator):
    """Platform-independent GUID type."""
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return str(uuid.UUID(value))
            else:
                return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                value = uuid.UUID(value)
            return value

class ArrayType(TypeDecorator):
    """Platform-independent Array type (uses JSON for SQLite)."""
    impl = JSON
    cache_ok = True

    def __init__(self, item_type=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.item_type = item_type
        
    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql' and self.item_type is not None:
            return dialect.type_descriptor(ARRAY(self.item_type))
        else:
            return dialect.type_descriptor(JSON())


Base = declarative_base()


class UserStatus(enum.Enum):
    """User account status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class User(Base):
    """User account model."""

    __tablename__ = "users"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=False)
    username = Column(String(100), unique=True, nullable=False, index=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(200), nullable=True)
    avatar_url = Column(String(500), nullable=True)

    # Role-based access control
    role = Column(String(50), default="student", nullable=False)  # student, teacher, admin

    # Account status
    status = Column(SQLEnum(UserStatus), default=UserStatus.ACTIVE)

    # Profile settings
    grade_level = Column(String(50), nullable=True)  # SMP, SMA, etc.
    preferred_subjects = Column(ArrayType(String), nullable=True)
    nickname = Column(String(100), nullable=True)
    kelas = Column(String(10), nullable=True)  # "10", "11", "12", dll
    birth_date = Column(Date, nullable=True)
    hardest_subjects = Column(ArrayType(String), nullable=True)
    onboarding_completed = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_login = Column(DateTime, nullable=True)
 
    # ===== PHASE 4: XP + LEVEL + STREAK SYSTEM (BARU) =====
    total_xp = Column(Integer, default=0)  # Total XP yang sudah dikumpulin
    level = Column(Integer, default=1)  # Level user
    current_streak = Column(Integer, default=0)  # Hari berturut-turut belajar
    longest_streak = Column(Integer, default=0)  # Streak terbaik
    last_activity_date = Column(Date, nullable=True)  # Terakhir aktif
 
    # Relationships
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    quizzes = relationship("Quiz", back_populates="author", foreign_keys="[Quiz.author_id]", cascade="all, delete-orphan")
    progress_logs = relationship("ProgressLog", back_populates="user", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    mastery_scores = relationship("MasteryScore", back_populates="user", cascade="all, delete-orphan")
 
    # Indexes
    __table_args__ = (
        Index("ix_users_email", "email"),
        Index("ix_users_username", "username"),
    )
 


class APIKey(Base):
    """API key for programmatic access."""

    __tablename__ = "api_keys"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, ForeignKey("users.id"), nullable=False)

    key = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=True)  # User-defined name for the key

    # Quota limits
    daily_quota = Column(Integer, default=1000)  # requests per day
    quota_used = Column(Integer, default=0)
    monthly_quota = Column(Integer, default=30000)  # requests per month
    monthly_quota_used = Column(Integer, default=0)

    # Key status
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_used_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="api_keys")

    def is_valid(self) -> bool:
        """Check if API key is currently valid."""
        if not self.is_active:
            return False
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        return True


class Document(Base):
    """Uploaded educational documents (PDF, PPT, etc.)."""

    __tablename__ = "documents"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, ForeignKey("users.id"), nullable=False)

    # File metadata
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=True)  # bytes
    file_type = Column(String(50), nullable=False)  # pdf, ppt, docx, etc.
    original_filename = Column(String, nullable=True) # atau nullable=False

    # Status
    status = Column(String(50), default="pending")  # pending, processing, completed, failed
    error_message = Column(Text, nullable=True)

    # Processing metadata
    total_pages = Column(Integer, nullable=True)
    total_chunks = Column(Integer, nullable=True)
    processed_at = Column(DateTime, nullable=True)

    # File storage (S3, etc.)
    file_path = Column(String(500), nullable=True)
    room_ids = Column(JSON, default=list) # Array penyimpan daftar nama room
    is_global = Column(Boolean, default=False) # True = Dokumen repository sistem
    is_selected = Column(Boolean, default=False) # True = Dokumen yang dipilih

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    """Text chunks from documents for RAG search."""

    __tablename__ = "document_chunks"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    document_id = Column(GUID, ForeignKey("documents.id"), nullable=False)
    parent_id = Column(GUID, nullable=True)  # Parent-Child RAG

    # Relationships
    document = relationship("Document", back_populates="chunks")

    # Content
    content = Column(Text, nullable=False)
    chunk_metadata = Column("metadata", JSON, nullable=True)  # topic, difficulty, tka_topic, etc.

    # Vector embeddings (stored separately in Qdrant or pgvector)
    embedding_vector = Column(ArrayType(Float), nullable=True)  # For pgvector (stored as JSON for SQLite compat)
    vector_id = Column(String(255), nullable=True)  # For Qdrant reference

    # Position in document
    chunk_index = Column(Integer, nullable=False)
    page_number = Column(Integer, nullable=True)

    # Topic metadata for intelligent search
    topics = Column(ArrayType(String), nullable=True)
    difficulty = Column(String(50), nullable=True)  # easy, medium, hard
    tka_topic = Column(String(100), nullable=True)  # TKA subject mapping

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Quiz(Base):
    """Quiz/exam sessions."""

    __tablename__ = "quizzes"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, ForeignKey("users.id"), nullable=False)
    author_id = Column(GUID, ForeignKey("users.id"), nullable=True)  # Can be self-generated

    # Quiz metadata
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    narasi = Column(Text, nullable=True)
    subject = Column(String(100), nullable=False)  # Math, Physics, Indonesian, etc.

    # Settings
    max_score = Column(Float, nullable=True)
    time_limit_minutes = Column(Integer, nullable=True)
    is_adaptive = Column(Boolean, default=False)
    room_id = Column(String(100), nullable=True)   # Link ke room
    exam_config = Column(JSON, nullable=True)
    difficulty = Column(String(50), nullable=True)  # auto-generated

    # Status
    status = Column(String(50), default="draft")  # draft, active, completed
    total_questions = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    author = relationship("User", foreign_keys=[author_id])
    questions = relationship("QuizQuestion", back_populates="quiz", cascade="all, delete-orphan")
    submissions = relationship("QuizSubmission", back_populates="quiz", cascade="all, delete-orphan")


class QuizQuestion(Base):
    """Individual quiz questions."""

    __tablename__ = "quiz_questions"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    quiz_id = Column(GUID, ForeignKey("quizzes.id"), nullable=False)

    # Question content
    question_text = Column(Text, nullable=False)
    question_type = Column(String(50), nullable=False)  # mcq, essay, true_false
    difficulty = Column(String(50), nullable=False)

    # For multiple choice
    options = Column(JSON, nullable=True)  # [A, B, C, D]

    # Correct answer
    correct_answer = Column(JSON, nullable=True)  # Depends on question type
    explanation = Column(Text, nullable=True)  # Why this is correct

    # Metadata
    topic = Column(String(100), nullable=True)
    source_chunk_ids = Column(ArrayType(String), nullable=True)  # RAG traceability
    reference_chunk_ids = Column(ArrayType(String), nullable=True)  # RAG source chunks

    # Order
    question_order = Column(Integer, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    quiz = relationship("Quiz", back_populates="questions")
    submissions = relationship("QuestionSubmission", back_populates="question", cascade="all, delete-orphan")


class QuizSubmission(Base):
    """User quiz submission/attempt."""

    __tablename__ = "quiz_submissions"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    quiz_id = Column(GUID, ForeignKey("quizzes.id"), nullable=False)
    user_id = Column(GUID, ForeignKey("users.id"), nullable=False)

    # Submission data
    answers = Column(JSON, nullable=False)  # {question_id: answer}
    score = Column(Float, nullable=True)
    max_score = Column(Float, nullable=True)
    percentage = Column(Float, nullable=True)
    post_narasi = Column(Text, nullable=True)
    status = Column(String(50), default="completed")  # Fix for quiz.py
    error_metadata = Column(JSON, nullable=True)

    # Time tracking
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    submitted_at = Column(DateTime, nullable=True)
    time_spent_seconds = Column(Integer, nullable=True)

    # Analysis
    performance_metrics = Column(JSON, nullable=True)  # topics mastered, weak areas

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    quiz = relationship("Quiz", back_populates="submissions")
    user = relationship("User")
    question_submissions = relationship("QuestionSubmission", back_populates="submission", cascade="all, delete-orphan")


class QuestionSubmission(Base):
    """Individual question answer from a submission."""

    __tablename__ = "question_submissions"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    submission_id = Column(GUID, ForeignKey("quiz_submissions.id"), nullable=False)
    question_id = Column(GUID, ForeignKey("quiz_questions.id"), nullable=False)

    # Answer data
    user_answer = Column(JSON, nullable=True)
    is_correct = Column(Boolean, nullable=True)
    error_metadata = Column(JSON, nullable=True)
    post_narasi = Column(Text, nullable=True)

    # Response time (seconds)
    response_time_seconds = Column(Integer, nullable=True)

    # Analysis
    error_type = Column(String(100), nullable=True)  # conceptual, careless, time_pressure

    # Relationships
    submission = relationship("QuizSubmission", back_populates="question_submissions")
    question = relationship("QuizQuestion", back_populates="submissions")

    __table_args__ = (
        UniqueConstraint("submission_id", "question_id", name="uq_question_per_submission"),
    )


class ProgressLog(Base):
    """User progress and learning analytics."""

    __tablename__ = "progress_logs"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, ForeignKey("users.id"), nullable=False)

    # Learning metrics
    xp_earned = Column(Integer, default=0)
    total_xp = Column(Integer, default=0)
    level = Column(Integer, default=1)

    # Session data
    session_id = Column(String(100), nullable=True)
    session_type = Column(String(50), nullable=True)  # chat, quiz, review

    # Topics worked on
    topics_engaged = Column(ArrayType(String), nullable=True)

    # Performance
    correct_answers = Column(Integer, default=0)
    incorrect_answers = Column(Integer, default=0)
    accuracy = Column(Float, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="progress_logs")


class MasteryScore(Base):
    """Mastery scores per topic/concept (Bayesian Knowledge Tracing)."""

    __tablename__ = "mastery_scores"

    __table_args__ = (
        UniqueConstraint("user_id", "topic", name="uq_user_topic_mastery"),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, ForeignKey("users.id"), nullable=False)

    # Topic identification
    topic = Column(String(100), nullable=False, index=True)
    subject = Column(String(100), nullable=False)

    # Mastery metrics (0-1 scale)
    mastery_score = Column(Float, default=0.0)  # Probability of mastery
    confidence = Column(Float, default=0.0)  # Confidence in mastery score
    times_practiced = Column(Integer, default=0)

    # Last activity
    last_practiced_at = Column(DateTime, nullable=True)
    next_review_at = Column(DateTime, nullable=True)  # Spaced repetition scheduler

    # Relationships
    user = relationship("User", back_populates="mastery_scores")

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class ChatSession(Base):
    """User chat sessions for RAG interaction."""

    __tablename__ = "chat_sessions"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, ForeignKey("users.id"), nullable=False)

    # Session metadata
    title = Column(String(255), nullable=True)
    mode = Column(String(50), default="OBROLAN")  # BELAJAR, OBROLAN, UJIAN, etc.

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    document_ids = Column(ArrayType(String), nullable=True)
    subject_id = Column(String(50), nullable=True)
    session_type = Column(String(20), default="sub")
    parent_session_id = Column(String(50), nullable=True)
    room_name = Column(String(100), nullable=True)
    summary = Column(Text, nullable=True)  # KEEP YANG INI
    summary_updated_at = Column(DateTime, nullable=True)


class ChatMessage(Base):
    """Chat messages in a session."""
 
    __tablename__ = "chat_messages"
 
    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    session_id = Column(GUID, ForeignKey("chat_sessions.id"), nullable=False)
    user_id = Column(GUID, ForeignKey("users.id"), nullable=False)
 
    # Message content
    role = Column(String(50), nullable=False)  # user, assistant
    content = Column(Text, nullable=False)
 
    # RAG context (reference chunks used)
    context_chunk_ids = Column(ArrayType(String), nullable=True)
    query_type = Column(String(50), nullable=True)  # simple, comparison, multi_topic, detailed
 
    # Mode info
    mode = Column(String(50), nullable=True)
    xp_gained = Column(Integer, default=0)
 
    # ===== PHASE 4: SM-2 SPACED REPETITION (BARU) =====
    rating = Column(Integer, default=0)  # User rating: 1-5
    sm2_ease_factor = Column(Float, default=2.5)  # SM-2 easiness factor
    sm2_repetitions = Column(Integer, default=0)  # Berapa kali review
    sm2_next_review = Column(DateTime, nullable=True)  # Kapan review lagi
    is_reviewable = Column(Boolean, default=True)  # Bisa review atau tidak
    last_reviewed_at = Column(DateTime, nullable=True)  # Terakhir review
 
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
 
    # Relationships
    session = relationship("ChatSession", back_populates="messages")

class RoomInsight(Base):
    """Armisa Insight per room — longitudinal memory."""
    
    __tablename__ = "room_insights"
    
    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, ForeignKey("users.id"), nullable=False)
    room_name = Column(String(100), nullable=False)
    
    # Insight content
    insight_text = Column(Text, nullable=False)
    topics_covered = Column(ArrayType(String), nullable=True)
    mastery_snapshot = Column(JSON, nullable=True)
    gaps_snapshot = Column(JSON, nullable=True)
    
    # Trigger info
    trigger_type = Column(String(50), nullable=True)  # beforeunload/gap/room_switch
    message_count_at_generation = Column(Integer, nullable=True)
    
    # Status
    is_seen = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        Index("ix_room_insights_user_room", "user_id", "room_name"),
    )