"""
FFmpeg video processor — clips and crops uploaded videos for Instagram/TikTok.
"""
import subprocess
import os
import uuid
import json
import logging
from typing import Optional, List, Dict
from config import settings

logger = logging.getLogger(__name__)

PLATFORM_MAX_DURATION = {
    "instagram": 90,
    "tiktok": 60,
}


def get_video_info(file_path: str) -> dict:
    """Return duration, width, height of a video file via ffprobe."""
    try:
        cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", file_path]
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


def _run_ffmpeg(input_path: str, start: float, duration: float, output_path: str) -> bool:
    """Run FFmpeg to clip + crop one segment. Returns True on success."""
    vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start),
        "-i", input_path,
        "-t", str(duration),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        output_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0 and os.path.exists(output_path):
            return True
        logger.error(f"FFmpeg error: {result.stderr[-400:]}")
    except Exception as e:
        logger.error(f"FFmpeg exception: {e}")
    return False


def process_for_platform(
    input_path: str,
    platform: str = "instagram",
    start_seconds: float = 0,
    duration_seconds: Optional[int] = None,
) -> str:
    """Clip and crop a single video. Falls back to original on failure."""
    max_dur = PLATFORM_MAX_DURATION.get(platform, 60)
    target_dur = min(duration_seconds or max_dur, max_dur)
    output_path = os.path.join(settings.upload_dir, f"proc_{uuid.uuid4().hex}.mp4")
    if _run_ffmpeg(input_path, start_seconds, target_dur, output_path):
        logger.info(f"Processed for {platform}: {output_path}")
        return output_path
    return input_path


def create_multiple_clips(
    input_path: str,
    num_clips: int,
    platform: str = "instagram",
    clip_duration: Optional[int] = None,
    segments: Optional[List[Dict]] = None,
) -> List[str]:
    """
    Create multiple platform-ready clips from one video.

    segments: optional list of {"start": float, "duration": float}.
    If omitted, the video is divided evenly into num_clips segments.

    Returns list of output file paths for successfully created clips.
    """
    info = get_video_info(input_path)
    total_duration = info["duration"]
    if total_duration == 0:
        logger.error("Cannot read video duration — aborting clip creation")
        return []

    max_dur = PLATFORM_MAX_DURATION.get(platform, 60)
    clip_dur = min(clip_duration or max_dur, max_dur)

    if segments:
        clip_segments = [
            (float(s["start"]), min(float(s.get("duration", clip_dur)), max_dur))
            for s in segments
        ]
    else:
        segment_len = total_duration / num_clips
        actual_dur = min(segment_len, max_dur)
        clip_segments = [(i * segment_len, actual_dur) for i in range(num_clips)]

    output_paths = []
    for i, (start, duration) in enumerate(clip_segments):
        output_path = os.path.join(settings.upload_dir, f"clip{i+1}_{uuid.uuid4().hex[:8]}.mp4")
        if _run_ffmpeg(input_path, start, duration, output_path):
            output_paths.append(output_path)
            logger.info(f"Clip {i+1}/{num_clips}: {output_path}")
        else:
            logger.warning(f"Clip {i+1}/{num_clips} failed — skipping")

    return output_paths


def needs_processing(file_path: str, platform: str = "instagram") -> bool:
    """Return True if the video needs clipping or cropping."""
    info = get_video_info(file_path)
    max_dur = PLATFORM_MAX_DURATION.get(platform, 60)
    return info["duration"] > max_dur or (info["width"] > 0 and info["width"] >= info["height"])
