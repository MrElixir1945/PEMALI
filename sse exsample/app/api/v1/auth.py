"""
Authentication Endpoints
========================
User registration, login, token refresh, and API key management
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db import get_db, SessionLocal
from app.db.models import User, APIKey, UserStatus
from app.models.schemas import (
    UserCreate, UserLogin, Token, UserResponse,
    APIKeyCreate, APIKeyResponse, UserProfileUpdate
)
from app.core.config import settings
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_token,
    get_current_user
)
from app.api.deps import get_current_user_from_token, verify_api_key

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.patch("/profile")
async def update_profile(
    data: UserProfileUpdate,
    user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    if data.nickname is not None:
        user.nickname = data.nickname
    if data.kelas is not None:
        user.kelas = data.kelas
    if data.birth_date is not None:
        from datetime import date
        user.birth_date = date.fromisoformat(data.birth_date)
    if data.hardest_subjects is not None:
        user.hardest_subjects = data.hardest_subjects
    if data.preferred_subjects is not None:
        user.preferred_subjects = data.preferred_subjects
    if data.grade_level is not None:
        user.grade_level = data.grade_level
    if data.onboarding_completed is not None:
        user.onboarding_completed = data.onboarding_completed

    db.commit()
    db.refresh(user)

    return {
        "success": True,
        "nickname": user.nickname,
        "kelas": user.kelas,
        "grade_level": user.grade_level,
        "hardest_subjects": user.hardest_subjects,
        "preferred_subjects": user.preferred_subjects,
        "onboarding_completed": user.onboarding_completed
    }


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Register a new user.

    - **email**: User email (must be unique)
    - **username**: Username (must be unique, 3-100 chars)
    - **password**: Password (min 8 chars)
    - **full_name**: Optional full name
    - **grade_level**: Optional (SMP/SMA)
    """
    # Check if email exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Check if username exists
    existing_username = db.query(User).filter(User.username == user_data.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    # Create user
    user = User(
        id=str(uuid4()),
        email=user_data.email,
        username=user_data.username,
        password_hash=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        grade_level=user_data.grade_level,
        role="student",
        status=UserStatus.ACTIVE,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login with email and password.
    Returns JWT access token.
    """
    # Find user by email
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active"
        )

    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )

    # Update last login
    user.last_login = datetime.now(timezone.utc)
    db.commit()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": int(access_token_expires.total_seconds())
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    (Implement refresh token rotation if needed)
    """
    # For now, just verify old token and create new
    payload = decode_token(refresh_token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    # Create new access token
    access_token = create_access_token(
        data={"sub": user_id}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": int(settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    }


@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    api_key_data: APIKeyCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new API key for the authenticated user.
    API keys are used for programmatic access.
    """
    from app.core.security import get_password_hash

    # Generate API key
    api_key = str(uuid4()).replace("-", "")  # Simple key generation
    key_prefix = "sk-prod-" + api_key[:32]

    # Calculate expiry
    expires_at = None
    if api_key_data.expires_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=api_key_data.expires_days)

    # Create API key record
    db_key = APIKey(
        id=str(uuid4()),
        user_id=user.id,
        key=key_prefix,
        name=api_key_data.name or "Default API Key",
        daily_quota=api_key_data.daily_quota,
        monthly_quota=api_key_data.monthly_quota,
        is_active=True,
        expires_at=expires_at,
    )

    db.add(db_key)
    db.commit()
    db.refresh(db_key)

    return {
        "id": db_key.id,
        "name": db_key.name,
        "key": db_key.key,  # Only returned once!
        "is_active": db_key.is_active,
        "daily_quota": db_key.daily_quota,
        "monthly_quota": db_key.monthly_quota,
        "created_at": db_key.created_at,
        "expires_at": db_key.expires_at,
    }


@router.get("/api-keys", response_model=list[APIKeyResponse])
async def list_api_keys(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all API keys for the authenticated user."""
    keys = db.query(APIKey).filter(APIKey.user_id == user.id).all()

    return [
        {
            "id": k.id,
            "name": k.name,
            "key": k.key,
            "is_active": k.is_active,
            "daily_quota": k.daily_quota,
            "monthly_quota": k.monthly_quota,
            "created_at": k.created_at,
            "expires_at": k.expires_at,
        }
        for k in keys
    ]


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revoke (delete) an API key."""
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == user.id
    ).first()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    db.delete(api_key)
    db.commit()

    return {"message": "API key revoked successfully"}
