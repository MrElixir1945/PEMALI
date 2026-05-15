"""
System Endpoints
================
Health check, version, and system information
"""

from datetime import datetime, timezone
from typing import List, Dict
from fastapi import APIRouter, HTTPException, status
from fastapi import FastAPI
from app.core.config import settings
from app.models.schemas import HealthCheck, InfoResponse

router = APIRouter(tags=["System"])


async def start_application():
    """Startup event for FastAPI application."""
    global app
    print(f"{settings.PROJECT_NAME} v{settings.PROJECT_VERSION} starting...")


async def shutdown_application():
    """Shutdown event for FastAPI application."""
    print(f"{settings.PROJECT_NAME} shutting down...")


@router.get("/health", response_model=HealthCheck)
async def health_check():
    """
    Health check endpoint.
    Returns system status and uptime.
    """
    return HealthCheck(
        status="healthy",
        version=settings.PROJECT_VERSION,
        timestamp=datetime.now(timezone.utc)
    )


@router.get("/info", response_model=InfoResponse)
async def get_info():
    """
    Get API information.
    Returns version, documentation URL, and available servers.
    """
    return InfoResponse(
        name=settings.PROJECT_NAME,
        version=settings.PROJECT_VERSION,
        documentation_url="http://localhost:8000/docs",
        servers=[
            {"url": "http://localhost:8000", "description": "Development"}
        ]
    )


@router.get("/server-info")
async def server_info():
    """
    Get detailed server information.
    Includes database status, etc.
    """
    from app.db import engine

    # Placeholder for actual database connection check
    is_db_connected = True # In a real app, this would check engine.connect()

    # Extract database type from URL (e.g., "postgresql", "sqlite")
    db_type = settings.DATABASE_URL.split(":")[0] if ":" in settings.DATABASE_URL else "unknown"

    # Remove credentials from the URL for display purposes
    # This is a generic way to remove anything before the last '@' if present,
    # or just return the URL if no '@' is found (e.g., for sqlite)
    display_db_url = settings.DATABASE_URL
    if "@" in display_db_url:
        display_db_url = display_db_url.split("@")[-1]

    return {
        "name": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "mode": "development" if settings.DEBUG else "production",
        "database_connected": is_db_connected,
        "database_type": db_type,
        "databases": {
            db_type: {
                "url": display_db_url,
                "status": "connected" if is_db_connected else "disconnected"
            }
        }
    }
