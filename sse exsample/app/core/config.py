"""
Sismind.ID Configuration
========================
Central configuration management using pydantic-settings
All settings from .env file - NO HARDCODED VALUES
"""

from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, List


class Settings(BaseSettings):

    # PROJECT
    PROJECT_NAME: str = "Sismind.ID API"
    PROJECT_VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"

    # FastAPI
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = Field(
        default="sqlite:///./sismind.db",
        description="Database connection URL"
    )

    # Vector Database
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "sismind_chunks"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    SECRET_KEY: str = Field(default="", description="Secret key for JWT")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # API Keys
    API_KEY_EXPIRY_DAYS: int = 365

    # OpenRouter
    OPENROUTER_API_KEY: str
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    # Models
    VLM_MODEL: str = Field(
        default="qwen/qwen2.5-vl-32b-instruct",
        description="VLM model for PDF extraction"
    )
    CHAT_MODEL: str = Field(
        default="arcee-ai/trinity-large-preview:free",
        description="Main chat model"
    )
    FAST_CHAT_MODEL: str = Field(
        default="qwen/qwen-2.5-7b-instruct:free",
        description="Fast model for simple queries"
    )
    EMBEDDING_MODEL: str = Field(
        default="BAAI/bge-m3",
        description="Local embedding model"
    )
    RERANKER_MODEL: str = Field(
        default="cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",
        description="Reranker model"
    )

    # RAG
    CHUNK_SIZE: int = 1500
    CHUNK_OVERLAP: int = 300
    MAX_CONTEXT_LENGTH: int = 4000
    VECTOR_SEARCH_TOP_K: int = 20
    BM25_TOP_K: int = 20
    RERANK_TOP_K: int = 20
    RERANK_FINAL_TOP_K: int = 6
    DEFAULT_N_RESULTS: int = 6
    USE_RERANKER: bool = True

    # Security
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000"
    ]
    RATE_LIMIT_REQUESTS: int = 60
    RATE_LIMIT_WINDOW: int = 60

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/sismind.log"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()