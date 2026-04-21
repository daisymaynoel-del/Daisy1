"""
Content management service — handles asset processing, thumbnail generation,
and post assembly from assets + AI-generated content.
"""
import os
import json
import logging
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy.orm import Session
from models import ContentAsset, Post, PostStatus, Platform, ContentPillar, AssetType
from services.ai_engine import generate_caption_and_hook, analyse_asset
from services.trends import get_trending_sounds_for_pillar
from config import settings

logger = logging.getLogger(__name__)


async def process_uploaded_asset(
    db: Session,
    file_path: str,
    original_filename: str,
    asset_type: str,
    tags: List[str] = None,
    notes: str = None,
) -> ContentAsset:
    """Process an uploaded file: generate thumbnail, analyse with AI, store in DB."""
    file_size = os.path.getsize(file_path)
    duration = None
    width, height = None, None

    if asset_type == "video":
        duration, width, height = _get_video_metadata(file_path)
    elif asset_type == "image":
        width, height = _get_image_dimensions(file_path)

    thumbnail_path = _generate_thumbnail(file_path, asset_type)

    # AI analysis
    description = f"{asset_type} file: {original_filename}, duration: {duration}s, dimensions: {width}x{height}"
    ai_analysis = analyse_asset(description, asset_type)

    asset = ContentAsset(
        filename=os.path.basename(file_path),
        original_filename=original_filename,
        file_path=file_path,
        thumbnail_path=thumbnail_path,
        asset_type=AssetType(asset_type),
        duration_seconds=duration,
        file_size_bytes=file_size,
        width=width,
        height=height,
        tags=json.dumps(tags or []),
        notes=notes,
        ai_analysis=json.dumps(ai_analysis),
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    logger.info(f"Asset processed: {asset.id} — {original_filename}")
    return asset


async def generate_post_from_asset(
    db: Session,
    asset_id: int,
    platform: str,
    content_pillar: Optional[str] = None,
    viral_benchmark_id: Optional[int] = None,
    custom_notes: Optional[str] = None,
) -> Post:
    """Use AI to generate a complete post from an asset."""
    asset = db.query(ContentAsset).filter(ContentAsset.id == asset_id).first()
    if not asset:
        raise ValueError(f"Asset {asset_id} not found")

    # Determine pillar from AI analysis if not specified
    if not content_pillar and asset.ai_analysis:
        analysis = json.loads(asset.ai_analysis)
        content_pillar = analysis.get("suggested_pillar", "transformation")

    # Get trending sounds for this pillar/platform
    trending_sounds = get_trending_sounds_for_pillar(db, platform, content_pillar or "transformation")
    trending_audio = trending_sounds[0] if trending_sounds else None

    # Get viral benchmark notes
    benchmark_notes = None
    if viral_benchmark_id:
        from models import ViralBenchmark
        benchmark = db.query(ViralBenchmark).filter(ViralBenchmark.id == viral_benchmark_id).first()
        if benchmark:
            benchmark_notes = f"Hook: {benchmark.hook_text}, Audio: {benchmark.audio_name}, Length: {benchmark.video_length_seconds}s"

    asset_description = f"Hair salon {asset.asset_type.value}, tags: {asset.tags}"

    ai_content = generate_caption_and_hook(
        content_pillar=content_pillar or "transformation",
        platform=platform,
        asset_description=asset_description,
        trending_audio=trending_audio,
        viral_benchmark_notes=benchmark_notes,
        custom_notes=custom_notes,
    )

    # Determine if patch test notice needed
    patch_test = ai_content.get("patch_test_required", False)
    caption = ai_content.get("caption", "")
    if patch_test:
        patch_notice = "\n\n⚠️ Patch test required 48hrs before any colour service. DM us to arrange."
        if patch_notice not in caption:
            caption += patch_notice

    # Map predicted performance to numeric score
    perf_map = {"low": 0.4, "medium": 1.0, "high": 1.8}
    perf_str = ai_content.get("predicted_performance", "medium")
    perf_multiplier = perf_map.get(perf_str, 1.0)

    from services.analytics import get_rolling_averages
    rolling = get_rolling_averages(db)
    predicted_views = int(rolling.get("avg_views", 1000) * perf_multiplier)

    post = Post(
        platform=Platform(platform),
        status=PostStatus.pending_approval if settings.approval_required else PostStatus.approved,
        content_type="reel" if platform == "instagram" else "tiktok_video",
        asset_id=asset_id,
        caption=caption,
        hashtags=json.dumps(ai_content.get("hashtags", [])),
        audio_name=ai_content.get("audio_suggestion") or trending_audio,
        hook_text=ai_content.get("hook", ""),
        thumbnail_path=asset.thumbnail_path,
        content_pillar=ContentPillar(content_pillar) if content_pillar else ContentPillar.transformation,
        viral_benchmark_id=viral_benchmark_id,
        ai_confidence_score=ai_content.get("confidence_score", 70),
        predicted_performance=predicted_views,
        needs_review=perf_multiplier < settings.underperform_threshold + 0.5,
        review_reason="Predicted to underperform vs. rolling average" if perf_multiplier < settings.underperform_threshold + 0.5 else None,
        patch_test_included=patch_test,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    logger.info(f"Post generated: {post.id} for platform {platform}, pillar {content_pillar}")
    return post


def get_next_posting_slot(db: Session, platform: str) -> datetime:
    """Return the next available posting time for a platform."""
    from pytz import timezone
    from datetime import date
    from config import settings as cfg

    tz = timezone(cfg.timezone)
    now = datetime.now(tz)

    post_times = cfg.instagram_post_times if platform == "instagram" else cfg.tiktok_post_times

    for time_str in post_times:
        hour, minute = map(int, time_str.split(":"))
        candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate > now:
            # Check no post is already scheduled at this time for this platform
            existing = db.query(Post).filter(
                Post.platform == platform,
                Post.scheduled_time == candidate.astimezone(tz=None).replace(tzinfo=None),
                Post.status.in_([PostStatus.scheduled, PostStatus.approved]),
            ).first()
            if not existing:
                return candidate.replace(tzinfo=None)

    # Default to tomorrow noon
    tomorrow = (now + timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
    return tomorrow.replace(tzinfo=None)


def _get_video_metadata(file_path: str):
    """Extract video duration and dimensions. Returns (duration, width, height)."""
    try:
        import subprocess, json
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", file_path],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "video":
                    duration = float(stream.get("duration", 0))
                    width = stream.get("width")
                    height = stream.get("height")
                    return duration, width, height
    except Exception:
        pass
    return None, None, None


def _get_image_dimensions(file_path: str):
    """Get image dimensions."""
    try:
        from PIL import Image
        with Image.open(file_path) as img:
            return img.size
    except Exception:
        return None, None


def _generate_thumbnail(file_path: str, asset_type: str) -> Optional[str]:
    """Generate a thumbnail for video or copy image for preview."""
    try:
        thumbnail_dir = settings.thumbnail_dir
        os.makedirs(thumbnail_dir, exist_ok=True)
        thumb_name = f"thumb_{uuid.uuid4().hex}.jpg"
        thumb_path = os.path.join(thumbnail_dir, thumb_name)

        if asset_type == "video":
            import subprocess
            result = subprocess.run(
                ["ffmpeg", "-i", file_path, "-ss", "00:00:01", "-vframes", "1", "-q:v", "2", thumb_path],
                capture_output=True, timeout=30
            )
            if result.returncode == 0:
                return thumb_path
        elif asset_type == "image":
            from PIL import Image
            with Image.open(file_path) as img:
                img.thumbnail((400, 400))
                img.save(thumb_path, "JPEG")
            return thumb_path
    except Exception as e:
        logger.warning(f"Thumbnail generation failed: {e}")
    return None
