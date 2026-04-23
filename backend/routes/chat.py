import json
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from models import ChatMessage, CreativeBrief
from services.chat import chat_with_agent, generate_content_brief_from_instructions
from services.analytics import get_rolling_averages

router = APIRouter(prefix="/chat", tags=["chat"])


class MessageRequest(BaseModel):
    message: str


class BriefUpdate(BaseModel):
    platform: Optional[str] = "both"
    video_length_seconds: Optional[int] = 15
    hook_style: Optional[str] = None
    music_preference: Optional[str] = None
    tone: Optional[str] = "casual"
    special_instructions: Optional[str] = None
    content_pillar: Optional[str] = None
    cta: Optional[str] = "Book via link in bio"
    always_subtitle: Optional[bool] = True


class ContentBriefRequest(BaseModel):
    instructions: str
    asset_description: str
    platform: str = "instagram"


# ── Chat ─────────────────────────────────────────────────────────────────────

@router.post("/message")
async def send_message(req: MessageRequest, db: Session = Depends(get_db)):
    """Send a message to the agent and get a response."""
    # Load history
    history_rows = db.query(ChatMessage).order_by(ChatMessage.created_at).limit(40).all()
    history = [{"role": r.role, "content": r.content} for r in history_rows]

    # Load active brief for context
    brief = db.query(CreativeBrief).filter(CreativeBrief.is_active == True).order_by(CreativeBrief.id.desc()).first()
    brief_dict = _brief_to_dict(brief) if brief else None

    # Load recent performance
    rolling = get_rolling_averages(db, days=7)

    # Get AI response
    result = await chat_with_agent(
        user_message=req.message,
        history=history,
        current_brief=brief_dict,
        performance_context=rolling,
    )

    # Save messages
    db.add(ChatMessage(role="user", content=req.message))
    db.add(ChatMessage(role="assistant", content=result["response"]))

    # Auto-update brief if instructions detected
    if result.get("brief_update") and result["brief_update"].get("detected"):
        _apply_brief_from_instruction(db, req.message, brief)

    db.commit()

    return {
        "response": result["response"],
        "brief_updated": result.get("brief_update") is not None,
    }


@router.get("/history")
def get_history(limit: int = 50, db: Session = Depends(get_db)):
    messages = db.query(ChatMessage).order_by(ChatMessage.created_at).limit(limit).all()
    return [{"id": m.id, "role": m.role, "content": m.content, "created_at": m.created_at} for m in messages]


@router.delete("/history")
def clear_history(db: Session = Depends(get_db)):
    db.query(ChatMessage).delete()
    db.commit()
    return {"cleared": True}


# ── Creative Brief ────────────────────────────────────────────────────────────

@router.get("/brief")
def get_brief(db: Session = Depends(get_db)):
    brief = db.query(CreativeBrief).filter(CreativeBrief.is_active == True).order_by(CreativeBrief.id.desc()).first()
    if not brief:
        return {"brief": None}
    return {"brief": _brief_to_dict(brief)}


@router.post("/brief")
def update_brief(data: BriefUpdate, db: Session = Depends(get_db)):
    # Deactivate old briefs
    db.query(CreativeBrief).update({"is_active": False})
    brief = CreativeBrief(
        platform=data.platform,
        video_length_seconds=data.video_length_seconds,
        hook_style=data.hook_style,
        music_preference=data.music_preference,
        tone=data.tone,
        special_instructions=data.special_instructions,
        content_pillar=data.content_pillar,
        cta=data.cta,
        always_subtitle=data.always_subtitle,
        is_active=True,
    )
    db.add(brief)
    db.commit()
    db.refresh(brief)
    return {"brief": _brief_to_dict(brief)}


@router.post("/generate-brief")
async def generate_brief_from_instructions(req: ContentBriefRequest):
    """Generate a full content brief from owner's free-text instructions."""
    brief = await generate_content_brief_from_instructions(
        instructions=req.instructions,
        asset_description=req.asset_description,
        platform=req.platform,
    )
    return brief


def _brief_to_dict(brief: CreativeBrief) -> dict:
    return {
        "id": brief.id,
        "platform": brief.platform,
        "video_length_seconds": brief.video_length_seconds,
        "hook_style": brief.hook_style,
        "music_preference": brief.music_preference,
        "tone": brief.tone,
        "special_instructions": brief.special_instructions,
        "content_pillar": brief.content_pillar,
        "cta": brief.cta,
        "always_subtitle": brief.always_subtitle,
        "created_at": brief.created_at.isoformat() if brief.created_at else None,
    }


def _apply_brief_from_instruction(db: Session, instruction: str, existing_brief: Optional[CreativeBrief]):
    """Partially update the brief based on detected instruction keywords."""
    import re

    updates = {}
    il = instruction.lower()

    # Detect video length
    length_match = re.search(r'(\d+)\s*(?:second|sec)', il)
    if length_match:
        updates["video_length_seconds"] = int(length_match.group(1))

    # Detect music preferences
    if "no music" in il or "no audio" in il:
        updates["music_preference"] = "no music"
    elif "trending" in il and "music" in il:
        updates["music_preference"] = "trending music"

    if not updates:
        return

    if existing_brief:
        for k, v in updates.items():
            setattr(existing_brief, k, v)
        existing_brief.updated_at = datetime.utcnow()
    else:
        db.add(CreativeBrief(**updates, is_active=True))
