"""
Sismind.ID Backend API
=====================
FastAPI application entry point

Usage:
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


from apscheduler.schedulers.background import BackgroundScheduler
from app.services.insight_scheduler import run_insight_job_sync, register_jobs
from app.core.config import settings
from app.api.v1 import api_router
from app.db import engine
from app.db.models import Base

# Setup logging
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"{settings.PROJECT_NAME} v{settings.PROJECT_VERSION} starting...")
    logger.info(f"Database: {settings.DATABASE_URL[:30]}...")
    logger.info(f"Host: {settings.HOST}:{settings.PORT}")

    # Create DB tables
    Base.metadata.create_all(bind=engine)

    # Start APScheduler
    scheduler = BackgroundScheduler(timezone="Asia/Makassar")
    register_jobs(scheduler)
    scheduler.start()
    logger.info("[Scheduler] ✅ APScheduler started — 03:00, 12:00, 18:00 WITA")

    yield

    # Shutdown
    scheduler.shutdown(wait=False)
    logger.info(f"{settings.PROJECT_NAME} shutting down...")


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="Sismind.ID - Educational AI Platform API",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None
)


# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000", "https://sismind.balicivicai.site", "http://10.10.20.254:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception Handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors."""
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "errors": exc.errors()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Include API routers
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# Root endpoint
@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "status": "running",
        "docs": "/docs" if settings.DEBUG else "disabled"
    }


# Welcome route
@app.get("/welcome")
async def welcome():
    """Welcome message with quick start info."""
    return {
        "message": "Welcome to Sismind.ID API!",
        "next_steps": [
            "1. Register a user: POST /api/v1/auth/register",
            "2. Login: POST /api/v1/auth/login",
            "3. Start chatting: POST /api/v1/chat/",
            "4. Create quiz: POST /api/v1/quiz/",
            "5. Check progress: GET /api/v1/progress/stats"
        ],
        "docs": "/docs",
        "health": "/api/v1/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
