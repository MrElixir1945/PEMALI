"""
Room Management Endpoints
==========================
CRUD operations for rooms (subject_dictionary)
Rooms = Global ChatSessions (session_type="global")
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime, timezone

from app.services.room_summary_service import RoomSummaryService
from app.db import get_db_session
from app.db.models import User, ChatSession
from app.api.deps import get_current_user_from_token
from app.models.schemas import RoomCreate, RoomResponse

router = APIRouter(prefix="/subject_dictionary", tags=["Rooms"])


@router.post("", response_model=RoomResponse, status_code=status.HTTP_201_CREATED, operation_id="create_room")
async def create_room(
    room_data: RoomCreate,
    user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db_session)
):
    """Create a new room (global chat session)."""
    
    # Check if room already exists
    existing = db.query(ChatSession).filter(
        ChatSession.user_id == user.id,
        ChatSession.room_name == room_data.room_name,
        ChatSession.session_type == "global"
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Room '{room_data.room_name}' already exists"
        )
    
    # Create global session (= room)
    room = ChatSession(
        id=str(uuid4()),
        user_id=user.id,
        room_name=room_data.room_name,
        title=f"{room_data.room_name} - General",
        session_type="global",
        mode="OBROLAN",
        created_at=datetime.now(timezone.utc)
    )
    
    db.add(room)
    db.commit()
    db.refresh(room)
    
    return RoomResponse(
        room_name=room.room_name,
        chats_count=0,
        docs_count=0
    )


@router.get("", response_model=dict, operation_id="list_rooms")
async def list_rooms(
    user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db_session)
):
    """List all rooms for user."""
    
    # Get all global sessions (rooms)
    rooms = db.query(ChatSession).filter(
        ChatSession.user_id == user.id,
        ChatSession.session_type == "global"
    ).order_by(ChatSession.created_at.desc()).all()
    
    room_list = []
    
    for room in rooms:
        # Count sub-chats for this room
        chats_count = db.query(ChatSession).filter(
            ChatSession.user_id == user.id,
            ChatSession.room_name == room.room_name,
            ChatSession.session_type == "sub"
        ).count()
        
        # TODO: Count docs for this room
        docs_count = 0
        
        room_list.append({
            "id": str(room.id),
            "subject_name": room.room_name,
            "chats_count": chats_count,
            "docs_count": docs_count,
            "created_at": room.created_at.isoformat(),
            "updated_at": room.updated_at.isoformat() if room.updated_at else None
        })
    
    return {"rooms": room_list}


@router.get("/{room_name}", response_model=RoomResponse, operation_id="get_room")
async def get_room(
    room_name: str,
    user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db_session)
):
    """Get room details (chats count, docs count, etc)."""
    
    room = db.query(ChatSession).filter(
        ChatSession.user_id == user.id,
        ChatSession.room_name == room_name,
        ChatSession.session_type == "global"
    ).first()
    
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    chats_count = db.query(ChatSession).filter(
        ChatSession.user_id == user.id,
        ChatSession.room_name == room_name,
        ChatSession.session_type == "sub"
    ).count()
    
    docs_count = 0
    
    return RoomResponse(
        room_name=room_name,
        chats_count=chats_count,
        docs_count=docs_count
    )

@router.put("/{room_name}", response_model=dict, operation_id="update_room")
async def update_room(
    room_name: str,
    room_data: RoomCreate,
    user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db_session)
):
    """Update room name."""
    
    # Get room
    room = db.query(ChatSession).filter(
        ChatSession.user_id == user.id,
        ChatSession.room_name == room_name,
        ChatSession.session_type == "global"
    ).first()
    
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    # Check if new name already exists
    existing = db.query(ChatSession).filter(
        ChatSession.user_id == user.id,
        ChatSession.room_name == room_data.room_name,
        ChatSession.session_type == "global",
        ChatSession.id != room.id  # Exclude current room
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Room '{room_data.room_name}' already exists"
        )
    
    # Update room name
    old_name = room.room_name
    room.room_name = room_data.room_name
    room.title = f"{room_data.room_name} - General"
    room.updated_at = datetime.now(timezone.utc)
    
    # Update all sub-chats for this room
    sub_chats = db.query(ChatSession).filter(
        ChatSession.room_name == old_name,
        ChatSession.session_type == "sub"
    ).all()
    
    for sub in sub_chats:
        sub.room_name = room_data.room_name
    
    db.commit()
    
    return {
        "message": "Room updated",
        "room_name": room.room_name
    }


@router.delete("/{room_name}", response_model=dict, operation_id="delete_room")
async def delete_room(
    room_name: str,
    user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db_session)
):
    """Delete room and all related sessions/chats."""
    
    # Get room
    room = db.query(ChatSession).filter(
        ChatSession.user_id == user.id,
        ChatSession.room_name == room_name,
        ChatSession.session_type == "global"
    ).first()
    
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    # Delete all sessions for this room (global + subs)
    sessions = db.query(ChatSession).filter(
        ChatSession.user_id == user.id,
        ChatSession.room_name == room_name
    ).all()
    
    for session in sessions:
        db.delete(session)
    
    db.commit()
    
    return {"message": "Room deleted"}