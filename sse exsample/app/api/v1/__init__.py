"""
API v1 Router
=============
Collects all API v1 endpoints
"""

from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.progress import router as progress_router
from app.api.v1.quiz import router as quiz_router
from app.api.v1.documents import router as documents_router
from app.api.v1.system import router as system_router
from app.api.v1.scheduler import router as scheduler_router
from app.api.v1 import rooms, rooms_chats, rooms_documents

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(chat_router)
api_router.include_router(progress_router)
api_router.include_router(quiz_router)
api_router.include_router(documents_router)
api_router.include_router(system_router)
api_router.include_router(scheduler_router)
api_router.include_router(rooms.router)
api_router.include_router(rooms_chats.router)
api_router.include_router(rooms_documents.router)