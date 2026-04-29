"""
Auto-clipping orchestrator.

Given a long video ContentAsset, slice it into platform-ready clips
(silence-aware when possible), create a child ContentAsset + pending-approval
Post for each clip, and return a summary.

Used by:
  - routes/assets.py upload hook (auto-trigger on upload)
  - routes/assets.py POST /assets/{id}/auto-clip (manual re-trigger)
"""
import os
import json
import logging
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from models import (
    ContentAsset,
    Post,
    PostStatus,
    Platform,
    ContentPillar,
    AssetType,
)
from config import settings
from services.video_processor import (
    auto_clip_video,
    get_video_info,
    PLATFORM_TARGET_CLIP,
)
from services.ai_engine import generate_caption_and_hook

logger = logging.getLogger(__name__)


def _resolve_pillar(asset: ContentAsset) -> str:
    """Best-effort content pillar from AI analysis or a sane default."""
    if asset.ai_analysis:
        try:
            data = json.loads(asset.ai_analysis)
            pillar = data.get("suggested_pillar")
            if pillar:
                return pillar
        except Exception:
            pass
    return "transformation"


def auto_clip_asset(
    db: Session,
    asset: ContentAsset,
    platforms: Optional[List[str]] = None,
    use_silence_detection: Optional[bool] = None,
    max_per_platform: Optional[int] = None,
) -> Dict:
    """
    Run the full auto-clip pipeline for a single uploaded asset.

    Returns a summary dict:
      {
        "asset_id": int,
        "platforms": ["instagram","tiktok"],
        "clips_created": int,
        "post_ids": [int, ...],
        "skipped_reason": Optional[str],
      }
    """
    summary: Dict = {
        "asset_id": asset.id,
        "platforms": [],
        "clips_created": 0,
        "post_ids": [],
        "skipped_reason": None,
    }

    if asset.asset_type != AssetType.video:
        summary["skipped_reason"] = "not_a_video"
        return summary

    if not asset.file_path or not os.path.exists(asset.file_path):
        summary["skipped_reason"] = "missing_file"
        return summary

    info = get_video_info(asset.file_path)
    duration = info.get("duration", 0) or 0
    if duration < settings.auto_clip_min_duration_seconds:
        summary["skipped_reason"] = f"too_short ({duration:.1f}s)"
        return summary

    target_platforms = platforms or settings.auto_clip_platform_list or ["instagram", "tiktok"]
    target_platforms = [p for p in target_platforms if p in PLATFORM_TARGET_CLIP]
    if not target_platforms:
        summary["skipped_reason"] = "no_valid_platforms"
        return summary

    silence = (
        use_silence_detection
        if use_silence_detection is not None
        else settings.auto_clip_use_silence_detection
    )
    cap = max_per_platform or settings.auto_clip_max_per_platform

    pillar = _resolve_pillar(asset)
    summary["platforms"] = list(target_platforms)

    for platform in target_platforms:
        clips = auto_clip_video(
            input_path=asset.file_path,
            platform=platform,
            use_silence_detection=silence,
            max_clips=cap,
        )
        if not clips:
            logger.warning(
                f"auto_clip_asset: no clips produced for asset {asset.id} on {platform}"
            )
            continue

        for clip in clips:
            try:
                post_id = _create_clip_asset_and_post(
                    db=db,
                    parent_asset=asset,
                    clip=clip,
                    platform=platform,
                    pillar=pillar,
                    total_clips=len(clips),
                )
                summary["post_ids"].append(post_id)
                summary["clips_created"] += 1
            except Exception as e:
                logger.error(
                    f"auto_clip_asset: failed to create post for clip "
                    f"{clip.get('path')}: {e}"
                )

    db.commit()
    logger.info(
        f"auto_clip_asset: asset {asset.id} -> "
        f"{summary['clips_created']} clips across {summary['platforms']}"
    )
    return summary


def _create_clip_asset_and_post(
    db: Session,
    parent_asset: ContentAsset,
    clip: Dict,
    platform: str,
    pillar: str,
    total_clips: int,
) -> int:
    """Persist a clip as its own ContentAsset and create a pending-approval Post."""
    clip_path = clip["path"]
    idx = clip["index"]

    clip_asset = ContentAsset(
        filename=os.path.basename(clip_path),
        original_filename=f"Auto-clip {idx} of {parent_asset.original_filename or 'upload'}",
        file_path=clip_path,
        thumbnail_path=parent_asset.thumbnail_path,
        asset_type=AssetType.video,
        duration_seconds=clip["duration"],
        file_size_bytes=os.path.getsize(clip_path) if os.path.exists(clip_path) else None,
        tags=parent_asset.tags,
        notes=(
            f"Auto-clipped from asset #{parent_asset.id} "
            f"({parent_asset.original_filename}) \u2014 clip {idx}/{total_clips} "
            f"for {platform} (start={clip['start']:.1f}s, dur={clip['duration']:.1f}s)"
        ),
        ai_analysis=parent_asset.ai_analysis,
    )
    db.add(clip_asset)
    db.flush()  # get clip_asset.id

    asset_description = (
        f"Auto-clipped segment {idx}/{total_clips} from "
        f"{parent_asset.original_filename or 'uploaded video'} "
        f"({clip['duration']:.0f}s clip starting at {clip['start']:.0f}s)."
    )

    ai_content = generate_caption_and_hook(
        content_pillar=pillar,
        platform=platform,
        asset_description=asset_description,
        custom_notes=(
            f"This is auto-clip {idx} of {total_clips}. "
            f"Generate a unique hook and caption \u2014 don't repeat patterns "
            f"from sibling clips."
        ),
    )

    caption = ai_content.get("caption", "") or ""
    if ai_content.get("patch_test_required"):
        notice = "\n\n\u26a0\ufe0f Patch test required 48hrs before any colour service."
        if notice not in caption:
            caption += notice

    try:
        pillar_enum = ContentPillar(pillar)
    except ValueError:
        pillar_enum = ContentPillar.transformation

    post = Post(
        platform=Platform(platform),
        status=(
            PostStatus.pending_approval
            if settings.approval_required
            else PostStatus.approved
        ),
        content_type="reel" if platform == "instagram" else "tiktok_video",
        asset_id=clip_asset.id,
        caption=caption,
        hashtags=json.dumps(ai_content.get("hashtags", [])),
        audio_name=ai_content.get("audio_suggestion", "") or "",
        hook_text=ai_content.get("hook", "") or "",
        thumbnail_path=parent_asset.thumbnail_path,
        content_pillar=pillar_enum,
        ai_confidence_score=ai_content.get("confidence_score", 70),
    )
    db.add(post)
    db.flush()
    return post.id
