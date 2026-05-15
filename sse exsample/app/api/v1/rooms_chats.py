import json
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime, timezone

from app.services.room_summary_service import RoomSummaryService
from app.db import get_db_session
from app.db.models import User, ChatSession, RoomInsight
from app.api.deps import get_current_user_from_token
from app.models.schemas import SubChatCreate, SubChatResponse

router = APIRouter(prefix="/rooms", tags=["Sub-Chats"])


# ============================================================
# INSIGHT ENDPOINTS
# ============================================================

@router.post("/{room_name}/generate-insight")
async def generate_insight(
    room_name: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db_session)
):

    last_insight = db.query(RoomInsight).filter(
        RoomInsight.user_id == str(user.id),
        RoomInsight.room_name == room_name
    ).order_by(RoomInsight.created_at.desc()).first()

    if last_insight:
        age = datetime.now(timezone.utc) - last_insight.created_at.replace(tzinfo=timezone.utc)

        if age.total_seconds() < 2 * 3600:
            return {
                "status": "throttled",
                "message": "Ini adalah insight terbaru kak! Tunggu insight selanjutnya ya biar datanya makin akurat 😊",
                "next_available_in_minutes": int((2 * 3600 - age.total_seconds()) / 60),
                "generated_at": last_insight.created_at.isoformat()
            }

    user_id = str(user.id)

    def _generate():
        from app.db import SessionLocal
        bg_db = SessionLocal()
        try:
            RoomSummaryService.build_room_summary(
                room_name=room_name,
                user_id=user_id,
                db=bg_db,
                trigger_type="manual"
            )
        finally:
            bg_db.close()

    background_tasks.add_task(_generate)

    return {"status": "generating"}


# ============================================================
# GET ROOM SUMMARY
# ============================================================

@router.get("/{room_name}/summary")
async def get_room_summary(
    room_name: str,
    user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db_session)
):

    last_insight = db.query(RoomInsight).filter(
        RoomInsight.user_id == str(user.id),
        RoomInsight.room_name == room_name,
        RoomInsight.insight_text.isnot(None)
    ).order_by(RoomInsight.created_at.desc()).first()

    # --------------------------------------------------------
    # Jika belum ada insight sama sekali
    # --------------------------------------------------------

    if not last_insight:
        return {
            "room_name": room_name,
            "armisa_insight": None,
            "insight_data": {},
            "needs_generation": True,
            "cached": False,
            "topics_discussed": [],
            "mastery_per_topic": {},
            "gaps": [],
            "recommendations": [],
            "overall_mastery_pct": 0,
            "total_messages": 0,
            "rated_messages": 0,
        }

    # --------------------------------------------------------
    # Insight ditemukan
    # --------------------------------------------------------

    age = datetime.now(timezone.utc) - last_insight.created_at.replace(tzinfo=timezone.utc)
    is_fresh = age.total_seconds() < 8 * 3600

    raw = last_insight.insight_text or ""

    try:
        parsed = json.loads(raw)

        armisa_narrative = parsed.get("narrative", raw)
        topics = parsed.get("topics", last_insight.topics_covered or [])
        mastery = parsed.get("mastery_per_topic", last_insight.mastery_snapshot or {})
        gaps = parsed.get("gaps", last_insight.gaps_snapshot or [])
        recommendations = parsed.get("recommendations", [])
        overall_pct = parsed.get("overall_pct", 0)

    except Exception:

        armisa_narrative = raw
        topics = last_insight.topics_covered or []
        mastery = last_insight.mastery_snapshot or {}
        gaps = last_insight.gaps_snapshot or []
        recommendations = []
        overall_pct = 0

    last_insight.is_seen = True
    db.commit()

    return {
        "room_name": room_name,
        "armisa_insight": armisa_narrative,
        "insight_data": {},
        "topics_discussed": topics,
        "mastery_per_topic": mastery,
        "gaps": gaps,
        "recommendations": recommendations,
        "overall_mastery_pct": overall_pct,
        "total_messages": last_insight.message_count_at_generation or 0,
        "rated_messages": 0,
        "cached": True,
        "needs_generation": not is_fresh,
        "generated_at": last_insight.created_at.isoformat()
    }


# ============================================================
# FORCE GENERATE
# ============================================================

@router.post("/{room_name}/generate-insight-sync")
async def generate_insight_sync(
    room_name: str,
    user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db_session)
):

    summary = RoomSummaryService.build_room_summary(
        room_name=room_name,
        user_id=str(user.id),
        db=db,
        trigger_type="on_demand"
    )

    return summary


# ============================================================
# SUBCHAT ENDPOINTS
# ============================================================

@router.post("/{room_name}/chats", response_model=SubChatResponse)
async def create_subchat(
    room_name: str,
    chat_data: SubChatCreate,
    user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db_session)
):

    parent = db.query(ChatSession).filter(
        ChatSession.user_id == user.id,
        ChatSession.room_name == room_name,
        ChatSession.session_type == "global"
    ).first()

    if not parent:
        raise HTTPException(status_code=404, detail="Room not found")

    sub_chat = ChatSession(
        id=str(uuid4()),
        user_id=user.id,
        room_name=room_name,
        session_type="sub",
        parent_session_id=str(parent.id),
        title=chat_data.chat_name,
        mode="OBROLAN",
        created_at=datetime.now(timezone.utc)
    )

    db.add(sub_chat)
    db.commit()

    return SubChatResponse(
        chat_id=str(sub_chat.id),
        chat_name=chat_data.chat_name,
        room_name=room_name
    )


@router.get("/{room_name}/chats")
async def list_chats(
    room_name: str,
    user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db_session)
):

    chats = db.query(ChatSession).filter(
        ChatSession.user_id == user.id,
        ChatSession.room_name == room_name
    ).all()

    if not chats:
        raise HTTPException(status_code=404, detail="Room not found")

    result = {"global_chat": None, "sub_chats": []}

    for chat in chats:

        if chat.session_type == "global":

            result["global_chat"] = {
                "chat_id": str(chat.id),
                "chat_name": chat.title,
                "type": "global"
            }

        else:

            result["sub_chats"].append({
                "chat_id": str(chat.id),
                "chat_name": chat.title,
                "type": "sub"
            })

    return result


@router.put("/{room_name}/chats/{chat_id}")
async def update_chat(
    room_name: str,
    chat_id: str,
    chat_data: SubChatCreate,
    user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db_session)
):

    chat = db.query(ChatSession).filter(
        ChatSession.id == chat_id,
        ChatSession.user_id == user.id,
        ChatSession.room_name == room_name
    ).first()

    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    chat.title = chat_data.chat_name

    db.commit()

    return {"message": "Chat updated"}


@router.delete("/{room_name}/chats/{chat_id}")
async def delete_chat(
    room_name: str,
    chat_id: str,
    user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db_session)
):

    chat = db.query(ChatSession).filter(
        ChatSession.id == chat_id,
        ChatSession.user_id == user.id,
        ChatSession.room_name == room_name,
        ChatSession.session_type == "sub"
    ).first()

    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    db.delete(chat)
    db.commit()

    return {"message": "Chat deleted"}