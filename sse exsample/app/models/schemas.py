"""
Pydantic Schemas
===============
Request/Response models for FastAPI endpoints
"""

from datetime import datetime
from typing import Optional, List, Any, Dict
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ==============================================================================
# Authentication Schemas
# ==============================================================================

class UserCreate(BaseModel):
    """Schema for user registration."""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    grade_level: Optional[str] = None


class UserLogin(BaseModel):
    """Schema for user login."""

    email: EmailStr
    password: str


class Token(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class UserResponse(BaseModel):
    """User response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    username: str
    full_name: Optional[str] = None
    role: str
    status: str
    created_at: datetime
    last_login: Optional[datetime] = None


class TokenRefresh(BaseModel):
    """Schema for refresh token."""

    refresh_token: str


class APIKeyCreate(BaseModel):
    """Schema for creating API key."""

    name: Optional[str] = None
    daily_quota: int = 1000
    monthly_quota: int = 30000
    expires_days: Optional[int] = 365


class APIKeyResponse(BaseModel):
    """API key response schema."""

    id: UUID
    name: Optional[str]
    key: str  # Only returned on creation
    is_active: bool
    daily_quota: int
    monthly_quota: int
    created_at: datetime
    expires_at: Optional[datetime] = None


# ==============================================================================
# Document Schemas
# ==============================================================================

class DocumentCreate(BaseModel):
    """Schema for document upload request."""

    filename: str
    file_type: str
    total_pages: Optional[int] = None


class DocumentResponse(BaseModel):
    """Document response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    original_filename: str
    file_type: str
    status: str
    total_pages: Optional[int] = None
    total_chunks: Optional[int] = None
    created_at: datetime


class DocumentStatus(BaseModel):
    """Document processing status update."""

    id: UUID
    status: str
    error_message: Optional[str] = None
    total_chunks: Optional[int] = None


# ==============================================================================
# RAG & Chat Schemas
# ==============================================================================

# Query types
QueryType = str  # "simple", "comparison", "multi_topic", "detailed"
ChatMode = str  # "BELAJAR", "OBROLAN", "UJIAN", "DEBAT", "CASUAL"


class ChatRequest(BaseModel):
    """Chat query request."""

    user_input: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[UUID] = None  # Create new session if None
    mode: Optional[ChatMode] = None  # Auto-detect if not provided
    include_context: bool = True  # Include RAG context

    # For streaming
    stream: bool = False

    # Metadata
    source: Optional[str] = None  # "web", "mobile", "api"
    user_agent: Optional[str] = None
    doc_ids: Optional[List[str]] = None


class ChatResponse(BaseModel):
    """Chat response schema."""

    reply: str
    mode: ChatMode
    query_type: QueryType
    session_id: UUID
    xp_gained: int
    cached: bool
    visuals: List[dict] = []  # Image/diagram info


class ChatStreamingChunk(BaseModel):
    """SSE streaming chunk for chat."""

    event: str  # "token", "metadata", "done", "error"
    data: dict

class RoomCreate(BaseModel):
    room_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None

class RoomResponse(BaseModel):
    room_name: str
    chats_count: int = 0
    docs_count: int = 0

class SubChatCreate(BaseModel):
    chat_name: str = Field(..., min_length=1, max_length=100)

class SubChatResponse(BaseModel):
    chat_id: str
    chat_name: str
    room_name: str

class SearchQuery(BaseModel):
    """Text search query."""

    query: str = Field(..., min_length=1)
    n_results: int = Field(default=6, ge=1, le=20)
    subject: Optional[str] = None
    topics: Optional[List[str]] = None


class SearchResult(BaseModel):
    """RAG search result."""

    content: str
    metadata: dict
    score: float
    rerank_score: Optional[float] = None
    visual_summary: Optional[str] = None


# ==============================================================================
# Quiz Schemas
# ==============================================================================

class QuizCreate(BaseModel):
    """Quiz creation request."""

    title: str = Field(..., min_length=1)
    description: Optional[str] = None
    subject: str
    total_questions: int = Field(default=10, ge=1, le=100)
    difficulty: Optional[str] = None
    time_limit_minutes: Optional[int] = None
    is_adaptive: bool = False


class QuizQuestionCreate(BaseModel):
    """Individual question creation."""

    question_text: str
    question_type: str = "mcq"  # mcq, essay
    options: Optional[List[str]] = None  # For MCQ (must be 4)
    correct_answer: Any  # Index or text depending on type
    explanation: Optional[str] = None
    difficulty: str
    topic: Optional[str] = None


class QuizResponse(BaseModel):
    """Quiz response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: Optional[str]
    subject: str
    total_questions: int
    difficulty: Optional[str]
    time_limit_minutes: Optional[int]
    status: str
    created_at: datetime


class QuizQuestionResponse(BaseModel):
    """Single question response."""

    submission_id: UUID
    score: float
    max_score: float
    percentage: float
    correct_answers: float # Ubah ke float karena ada Guessing Penalty (0.5)
    total_questions: int
    narasi: Optional[str] = None
    post_narasi: str # Tambahkan ini
    performance_metrics: Optional[dict] = None # Pastikan ini ada untuk data skalar & pattern
    submitted_at: datetime

class QuizAnswer(BaseModel):
    """User answer to a quiz question."""
    question_id: UUID
    answer: Any

class TimePerQuestion(BaseModel):
    time_on_question: int = 0
    reread_count: int = 0
    scroll_events: int = 0

class QuizSubmissionRequest(BaseModel):
    """Quiz submission request."""

    quiz_id: UUID
    answers: List[QuizAnswer]
    time_per_question: Optional[Dict[str, TimePerQuestion]] = None
    total_time_seconds: Optional[int] = None


class QuizSubmissionResponse(BaseModel):
    """Quiz submission result."""

    submission_id: UUID
    score: float
    max_score: float
    percentage: float
    correct_answers: int
    total_questions: int
    performance_metrics: Optional[dict] = None
    submitted_at: datetime


# ==============================================================================
# Progress Schemas
# ==============================================================================

class ProgressStats(BaseModel):
    """User progress statistics."""

    level: int
    total_xp: int
    sessions_completed: int
    correct_answers: int
    inaccurate_answers: int
    accuracy: Optional[float] = None
    streak: int = 0
    current_topic: Optional[str] = None


class ProgressUpdate(BaseModel):
    """XP update request."""

    xp_gained: int
    session_type: str
    topics_engaged: Optional[List[str]] = None


# ==============================================================================
# Error Schemas
# ==============================================================================

class ErrorDetail(BaseModel):
    """Error detail schema."""

    code: str
    message: str
    field: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str
    error_code: Optional[str] = None
    errors: Optional[List[ErrorDetail]] = None


# ==============================================================================
# System Schemas
# ==============================================================================

class HealthCheck(BaseModel):
    """System health check response."""

    status: str
    version: str
    timestamp: datetime


class ServerInfo(BaseModel):
    """Server information."""

    name: str
    version: str
    mode: str  # development, production
    databases: dict


class InfoResponse(BaseModel):
    """API info response."""

    name: str
    version: str
    documentation_url: str
    servers: List[dict]


class UserProfileUpdate(BaseModel):
    nickname: Optional[str] = None
    kelas: Optional[str] = None
    birth_date: Optional[str] = None  # format "YYYY-MM-DD"
    hardest_subjects: Optional[List[str]] = None
    preferred_subjects: Optional[List[str]] = None
    grade_level: Optional[str] = None
    onboarding_completed: Optional[bool] = None
