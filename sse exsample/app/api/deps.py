"""
Dependency Injection
===================
FastAPI dependencies for authentication, database, and services
"""

from app.services.chat_service import ChatService
from functools import lru_cache
from typing import Generator, Optional
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db import SessionLocal, get_db
from app.db.models import User, APIKey
from app.core.config import settings
from app.core.security import decode_token
from app.services.rag_service import RAGService

@lru_cache(maxsize=1)
def get_chat_service() -> ChatService:
    return ChatService()


# ==============================================================================
# Database Dependencies
# ==============================================================================

def get_db_session() -> Generator[Session, None, None]:
    """Database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==============================================================================
# Authentication Dependencies
# ==============================================================================

security = HTTPBearer(auto_error=False)


def verify_jwt(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Verify JWT token from Authorization header.
    Returns decoded payload.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


async def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db_session)
) -> User:
    """
    Get current authenticated user from JWT token.

    Raises:
        HTTPException: If token is invalid or user not found
    """
    payload = verify_jwt(credentials)
    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


async def verify_api_key(
    x_api_key: Optional[str],
    db: Session
) -> Optional[APIKey]:
    """
    Verify API key from X-API-Key header.

    Used for programmatic access (third-party integrations).
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    api_key = db.query(APIKey).filter(APIKey.key == x_api_key).first()

    if not api_key or not api_key.is_valid():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Check daily quota
    if api_key.quota_used >= api_key.daily_quota:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily quota exceeded",
        )

    # Update quota usage
    api_key.quota_used += 1
    api_key.last_used_at = db.func.now()
    db.commit()

    return api_key


# ==============================================================================
# Service Dependencies
# ==============================================================================

@lru_cache(maxsize=1)
def get_rag_service() -> RAGService:
    return RAGService()

# ==============================================================================
# Combined Authentication (User needs JWT OR API key)
# ==============================================================================

async def get_authenticated_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    x_api_key: Optional[str] = Header(default=None),
    db: Session = Depends(get_db_session)
) -> User:
    """
    Get authenticated user from either JWT or API Key.
    Uses JWT if available, falls back to API key.
    """
    # Try JWT authentication first
    if credentials:
        try:
            return await get_current_user_from_token(credentials, db)
        except HTTPException:
            # JWT failed, try API key
            pass

    # Try API key authentication
    if x_api_key:
        api_key = await verify_api_key(x_api_key, db)
        if api_key:
            return api_key.user

    # Neither succeeded
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No valid authentication provided",
        headers={"WWW-Authenticate": "Bearer, ApiKey"},
    )
