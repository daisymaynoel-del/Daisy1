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

# Target clip lengths for auto-clipping. Tuned for short-form attention spans:
# slightly under platform max so we have headroom for hook/outro pacing.
PLATFORM_TARGET_CLIP = {
    "instagram": 60,
    "tiktok": 45,
}

# Minimum clip length we'll keep — anything shorter than this is dropped.
MIN_CLIP_DURATION = 8.0


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


# ────────────────────────────────────────────────────────────────────────────
# Full auto-clipping
# ────────────────────────────────────────────────────────────────────────────

def detect_silence_segments(
    input_path: str,
    noise_db: float = -30.0,
    min_silence_seconds: float = 0.6,
) -> List[Dict]:
    """
    Use ffmpeg's silencedetect filter to find pauses in the audio.
    Returns a list of {"start": float, "end": float} for each silence span.
    Empty list if ffmpeg is unavailable, the file has no audio, or detection fails.
    """
    cmd = [
        "ffmpeg", "-hide_banner", "-nostats", "-i", input_path,
        "-af", f"silencedetect=noise={noise_db}dB:d={min_silence_seconds}",
        "-f", "null", "-",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except Exception as e:
        logger.warning(f"silencedetect failed to run: {e}")
        return []

    # silencedetect writes to stderr
    silences: List[Dict] = []
    current_start: Optional[float] = None
    for line in (result.stderr or "").splitlines():
        if "silence_start:" in line:
            try:
                current_start = float(line.split("silence_start:")[1].strip().split()[0])
            except Exception:
                current_start = None
        elif "silence_end:" in line and current_start is not None:
            try:
                end_token = line.split("silence_end:")[1].strip().split()[0]
                end = float(end_token)
                silences.append({"start": current_start, "end": end})
            except Exception:
                pass
            current_start = None
    return silences


def _pick_smart_cut_points(
    total_duration: float,
    target_clip: float,
    silences: List[Dict],
) -> List[float]:
    """
    Pick clip START times near every `target_clip` mark, snapping to the
    midpoint of the nearest silence span (within ±25% of target_clip) when one exists.
    Falls back to even spacing when no silence is nearby.
    """
    if total_duration <= target_clip:
        return [0.0]

    # Ideal even spacing
    num_clips = max(1, int(total_duration // target_clip))
    starts = [i * target_clip for i in range(num_clips)]
    if not silences:
        return starts

    snap_window = target_clip * 0.25
    snapped: List[float] = []
    last_end = -1.0
    for s in starts:
        if s == 0.0:
            snapped.append(0.0)
            last_end = target_clip
            continue
        # Find silence span whose midpoint is closest to `s` and within snap_window
        best = None
        best_dist = snap_window
        for sil in silences:
            mid = (sil["start"] + sil["end"]) / 2
            if mid <= last_end + MIN_CLIP_DURATION:
                continue
            dist = abs(mid - s)
            if dist <= best_dist:
                best = mid
                best_dist = dist
        chosen = best if best is not None else s
        snapped.append(chosen)
        last_end = chosen + target_clip
    return snapped


def auto_clip_video(
    input_path: str,
    platform: str = "instagram",
    target_clip_seconds: Optional[float] = None,
    use_silence_detection: bool = True,
    max_clips: int = 12,
) -> List[Dict]:
    """
    Full auto-clipper.

    Reads the video, picks clip start points (silence-aware when possible),
    runs ffmpeg for each segment, and returns a list of
    {"path": str, "start": float, "duration": float, "index": int}.

    Returns an empty list on total failure (e.g. unreadable video).
    """
    info = get_video_info(input_path)
    total_duration = info["duration"]
    if total_duration <= 0:
        logger.error("auto_clip_video: cannot read duration")
        return []

    target = target_clip_seconds or PLATFORM_TARGET_CLIP.get(platform, 45)
    target = min(target, PLATFORM_MAX_DURATION.get(platform, 60))

    if total_duration < MIN_CLIP_DURATION:
        logger.info(f"auto_clip_video: video too short ({total_duration}s) — skipping")
        return []

    silences: List[Dict] = []
    if use_silence_detection:
        try:
            silences = detect_silence_segments(input_path)
            logger.info(f"auto_clip_video: found {len(silences)} silence spans")
        except Exception as e:
            logger.warning(f"silence detection failed, falling back to even cuts: {e}")

    starts = _pick_smart_cut_points(total_duration, target, silences)
    starts = starts[:max_clips]

    results: List[Dict] = []
    for i, start in enumerate(starts):
        remaining = total_duration - start
        if remaining < MIN_CLIP_DURATION:
            continue
        duration = min(target, remaining)
        output_path = os.path.join(
            settings.upload_dir,
            f"autoclip_{platform}_{i+1}_{uuid.uuid4().hex[:8]}.mp4",
        )
        if _run_ffmpeg(input_path, start, duration, output_path):
            results.append({
                "path": output_path,
                "start": start,
                "duration": duration,
                "index": i + 1,
            })
            logger.info(
                f"auto-clip {i+1}/{len(starts)} for {platform}: "
                f"start={start:.1f}s dur={duration:.1f}s -> {output_path}"
            )
        else:
            logger.warning(f"auto-clip {i+1} failed — skipping")

    return results
