"""
FFmpeg video processor — clips and crops uploaded videos for Instagram/TikTok.

For each platform we:
  • Clip to the target duration (from start or a specified offset)
  • Scale/crop to 9:16 vertical (1080×1920) — fills frame, centre-crops
  • Re-encode with H.264 + AAC for maximum compatibility
"""
import subprocess
import os
import uuid
import json
import logging
from typing import Optional
from config import settings

logger = logging.getLogger(__name__)

PLATFORM_MAX_DURATION = {
    "instagram": 90,   # Reels up to 90s
    "tiktok": 60,      # TikTok standard up to 60s
}


def get_video_info(file_path: str) -> dict:
    """Return duration, width, height of a video file via ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            file_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        data = json.loads(result.stdout)
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                return {
                    "duration": float(stream.get("duration", 0)),
                    "width": int(stream.get("width", 0)),
                    "height": int(stream.get("height", 0)),
                }
    except Exception as e:
        logger.warning(f"ffprobe failed: {e}")
    return {"duration": 0, "width": 0, "height": 0}


def process_for_platform(
    input_path: str,
    platform: str = "instagram",
    start_seconds: float = 0,
    duration_seconds: Optional[int] = None,
) -> str:
    """
    Clip and crop a video for the target platform.

    Returns the path to the processed file.
    Falls back to the original file if FFmpeg fails.
    """
    max_dur = PLATFORM_MAX_DURATION.get(platform, 60)
    target_dur = min(duration_seconds or max_dur, max_dur)

    output_name = f"proc_{uuid.uuid4().hex}.mp4"
    output_path = os.path.join(settings.upload_dir, output_name)

    # Scale up to fill 1080×1920, then centre-crop — no black bars
    vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start_seconds),
        "-i", input_path,
        "-t", str(target_dur),
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        output_path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0 and os.path.exists(output_path):
            size_mb = os.path.getsize(output_path) / 1_000_000
            logger.info(f"Video processed for {platform}: {output_path} ({size_mb:.1f} MB)")
            return output_path
        logger.error(f"FFmpeg failed (rc={result.returncode}): {result.stderr[-500:]}")
    except Exception as e:
        logger.error(f"Video processing error: {e}")

    # Fallback — return original so posting still works
    return input_path


def needs_processing(file_path: str, platform: str = "instagram") -> bool:
    """Return True if the video needs clipping or cropping."""
    info = get_video_info(file_path)
    max_dur = PLATFORM_MAX_DURATION.get(platform, 60)
    too_long = info["duration"] > max_dur
    not_vertical = info["width"] > 0 and info["width"] >= info["height"]
    return too_long or not_vertical
