"""
Learning loop — correlates post performance with variables (hook type, audio,
length, posting time, hashtag set, visual style) and updates the pattern library.
"""
import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from models import Post, PostMetrics, Pattern, PatternType, PostStatus
from services.analytics import get_rolling_averages

logger = logging.getLogger(__name__)


def update_pattern_library(db: Session):
    """
    Run after every batch of new metrics arrive.
    Correlates performance against variables and updates patterns.
    """
    rolling = get_rolling_averages(db, days=30)
    avg_views = rolling.get("avg_views", 1)

    # Gather all 24h metrics with their posts
    metrics_with_posts = (
        db.query(PostMetrics, Post)
        .join(Post)
        .filter(
            PostMetrics.interval == "24h",
            Post.status == PostStatus.published,
        )
        .all()
    )

    if len(metrics_with_posts) < 3:
        logger.info("Not enough data to update patterns yet (need at least 3 published posts)")
        return

    # Build correlation data
    correlations: Dict[str, Dict[str, List[float]]] = {
        "audio": {},
        "content_pillar": {},
        "posting_hour": {},
        "hook_type": {},
        "caption_length": {},
    }

    for metrics, post in metrics_with_posts:
        score = metrics.views / max(avg_views, 1) * 50  # score relative to average, base 50

        # Audio
        if post.audio_name:
            correlations["audio"].setdefault(post.audio_name, []).append(score)

        # Content pillar
        if post.content_pillar:
            correlations["content_pillar"].setdefault(post.content_pillar.value, []).append(score)

        # Posting hour
        if post.published_time:
            hour = post.published_time.hour
            bucket = _hour_bucket(hour)
            correlations["posting_hour"].setdefault(bucket, []).append(score)

        # Hook type (first 3 words)
        if post.hook_text:
            hook_type = _classify_hook(post.hook_text)
            correlations["hook_type"].setdefault(hook_type, []).append(score)

        # Caption length
        if post.caption:
            length_bucket = _caption_length_bucket(len(post.caption))
            correlations["caption_length"].setdefault(length_bucket, []).append(score)

    # Update Pattern table
    type_map = {
        "audio": PatternType.audio,
        "content_pillar": PatternType.content_pillar,
        "posting_hour": PatternType.posting_time,
        "hook_type": PatternType.hook,
        "caption_length": PatternType.caption_style,
    }

    for correlation_key, values_dict in correlations.items():
        pattern_type = type_map[correlation_key]
        for value, scores in values_dict.items():
            if not scores:
                continue
            avg_score = sum(scores) / len(scores)
            _upsert_pattern(db, pattern_type, value, avg_score, len(scores))

    db.commit()
    logger.info("Pattern library updated")


def _upsert_pattern(db: Session, pattern_type: PatternType, value: str, score: float, sample_size: int):
    existing = db.query(Pattern).filter(
        Pattern.pattern_type == pattern_type,
        Pattern.pattern_value == value,
    ).first()

    if existing:
        # Weighted moving average
        total = existing.sample_size + sample_size
        existing.performance_score = (existing.performance_score * existing.sample_size + score * sample_size) / total
        existing.sample_size = total
        existing.last_updated = datetime.utcnow()
    else:
        db.add(Pattern(
            pattern_type=pattern_type,
            pattern_value=value,
            performance_score=score,
            sample_size=sample_size,
        ))


def get_best_patterns(db: Session, limit: int = 10) -> List[Pattern]:
    return (
        db.query(Pattern)
        .filter(Pattern.sample_size >= 2)
        .order_by(Pattern.performance_score.desc())
        .limit(limit)
        .all()
    )


def get_optimal_posting_time(db: Session, platform: str) -> str:
    """Return the best posting time based on pattern data, defaulting to 17:00."""
    pattern = (
        db.query(Pattern)
        .filter(Pattern.pattern_type == PatternType.posting_time)
        .order_by(Pattern.performance_score.desc())
        .first()
    )
    if pattern:
        return pattern.pattern_value
    return "17:00"


def _hour_bucket(hour: int) -> str:
    if 11 <= hour <= 13:
        return "12:00 (lunch)"
    elif 16 <= hour <= 18:
        return "16:00-18:00 (after work)"
    elif 18 <= hour <= 20:
        return "18:00-20:00 (evening)"
    elif 7 <= hour <= 9:
        return "07:00-09:00 (morning)"
    else:
        return "other"


def _classify_hook(hook_text: str) -> str:
    hook_lower = hook_text.lower()
    if any(w in hook_lower for w in ["before", "after", "→", "transformation"]):
        return "before_after"
    elif any(w in hook_lower for w in ["stop", "wrong", "mistake", "don't"]):
        return "negative_hook"
    elif any(w in hook_lower for w in ["pov", "you're", "imagine"]):
        return "pov_hook"
    elif any(w in hook_lower for w in ["how to", "tutorial", "tip", "secret"]):
        return "education_hook"
    elif any(w in hook_lower for w in ["day in", "behind", "what it's"]):
        return "bts_hook"
    else:
        return "statement_hook"


def _caption_length_bucket(length: int) -> str:
    if length < 100:
        return "short (<100)"
    elif length < 250:
        return "medium (100-250)"
    else:
        return "long (250+)"
