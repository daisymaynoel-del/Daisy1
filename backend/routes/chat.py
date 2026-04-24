import json
import re
import os
import shutil
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from models import ChatMessage, CreativeBrief, ContentAsset, Post, PostStatus, Platform, ContentPillar
from services.chat import chat_with_agent, generate_content_brief_from_instructions
from services.analytics import get_rolling_averages
from config import settings

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
    # Check for clip intent first
    clip_intent = _detect_clip_intent(req.message)
    if clip_intent:
        return await _handle_clip_request(req.message, clip_intent, db)

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
    updates = {}
    il = instruction.lower()

    length_match = re.search(r'(\d+)\s*(?:second|sec)', il)
    if length_match:
        updates["video_length_seconds"] = int(length_match.group(1))

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


# ── Clip intent detection ─────────────────────────────────────────────────────

def _detect_clip_intent(message: str) -> Optional[dict]:
    """
    Detect if the user wants to split a video into multiple clips.
    Returns {"num_clips": int, "platform": str, "instructions": str} or None.
    """
    msg = message.lower()
    clip_keywords = ["clip", "split", "cut into", "divide into", "make", "create"]
    has_clip_keyword = any(k in msg for k in clip_keywords)
    if not has_clip_keyword:
        return None

    num_match = re.search(
        r'(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s*'
        r'(?:different\s+)?(?:clips?|videos?|posts?|reels?)',
        msg
    )
    if not num_match:
        return None

    word_to_num = {"one":1,"two":2,"three":3,"four":4,"five":5,
                   "six":6,"seven":7,"eight":8,"nine":9,"ten":10}
    raw = num_match.group(1)
    num_clips = word_to_num.get(raw, None) or int(raw)
    num_clips = max(1, min(num_clips, 10))  # cap at 10

    platform = "tiktok" if "tiktok" in msg else "instagram"
    return {"num_clips": num_clips, "platform": platform, "instructions": message}


async def _handle_clip_request(message: str, intent: dict, db: Session) -> dict:
    """
    Split the most recent video asset into multiple clips and create posts for each.
    """
    from services.video_processor import create_multiple_clips, get_video_info
    from services.ai_engine import generate_caption_and_hook

    num_clips = intent["num_clips"]
    platform = intent["platform"]

    # Save user message
    db.add(ChatMessage(role="user", content=message))
    db.commit()

    # Find the most recent video asset
    asset = (
        db.query(ContentAsset)
        .filter(ContentAsset.asset_type == "video")
        .order_by(ContentAsset.created_at.desc())
        .first()
    )

    if not asset:
        reply = "I couldn't find any uploaded video to clip. Please upload a video first via the Upload page, then ask me to clip it."
        db.add(ChatMessage(role="assistant", content=reply))
        db.commit()
        return {"response": reply, "brief_updated": False, "clips_created": 0}

    info = get_video_info(asset.file_path)
    duration_mins = round(info["duration"] / 60, 1)

    reply_thinking = (
        f"On it! I'm splitting your {duration_mins}-minute video into {num_clips} clips "
        f"for {platform.capitalize()} — cropping to 9:16 and generating a caption for each. "
        f"This takes a minute..."
    )
    db.add(ChatMessage(role="assistant", content=reply_thinking))
    db.commit()

    # Create the clips with FFmpeg
    clip_paths = create_multiple_clips(
        input_path=asset.file_path,
        num_clips=num_clips,
        platform=platform,
    )

    if not clip_paths:
        reply = "FFmpeg couldn't process the video — it may be corrupted or in an unsupported format. Try re-uploading it."
        db.add(ChatMessage(role="assistant", content=reply))
        db.commit()
        return {"response": reply, "brief_updated": False, "clips_created": 0}

    # Create a ContentAsset + Post for each clip
    post_ids = []
    for i, clip_path in enumerate(clip_paths):
        clip_asset = ContentAsset(
            filename=os.path.basename(clip_path),
            original_filename=f"Clip {i+1} of {asset.original_filename}",
            file_path=clip_path,
            thumbnail_path=asset.thumbnail_path,
            asset_type="video",
            duration_seconds=info["duration"] / num_clips,
            file_size_bytes=os.path.getsize(clip_path),
            tags=asset.tags,
            notes=f"Auto-clipped from {asset.original_filename} — clip {i+1}/{num_clips}",
            ai_analysis=asset.ai_analysis,
        )
        db.add(clip_asset)
        db.flush()

        ai_content = generate_caption_and_hook(
            content_pillar="transformation",
            platform=platform,
            asset_description=f"Clip {i+1} of {num_clips} from {asset.original_filename}",
            custom_notes=f"This is clip {i+1} of {num_clips}. {intent['instructions']}",
        )

        caption = ai_content.get("caption", "")
        if ai_content.get("patch_test_required"):
            caption += "\n\n⚠️ Patch test required 48hrs before any colour service."

        post = Post(
            platform=Platform(platform),
            status=PostStatus.pending_approval,
            content_type="reel" if platform == "instagram" else "tiktok_video",
            asset_id=clip_asset.id,
            caption=caption,
            hashtags=json.dumps(ai_content.get("hashtags", [])),
            audio_name=ai_content.get("audio_suggestion", ""),
            hook_text=ai_content.get("hook", ""),
            thumbnail_path=asset.thumbnail_path,
            content_pillar=ContentPillar.transformation,
            ai_confidence_score=ai_content.get("confidence_score", 70),
        )
        db.add(post)
        db.flush()
        post_ids.append(post.id)

    db.commit()

    reply = (
        f"Done! I've created {len(clip_paths)} clips from your video and generated a unique caption for each one. "
        f"Head to the **Approval Queue** to review them — approve the ones you like and they'll be scheduled to post automatically."
    )
    db.add(ChatMessage(role="assistant", content=reply))
    db.commit()

    return {
        "response": reply,
        "brief_updated": False,
        "clips_created": len(clip_paths),
        "post_ids": post_ids,
    }
