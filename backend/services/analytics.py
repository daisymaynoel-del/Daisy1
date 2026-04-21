"""
Analytics service — collects post metrics at scheduled intervals,
calculates rolling averages, and feeds data into the learning loop.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from models import Post, PostMetrics, PostStatus, Platform
from services.instagram import instagram_service
from services.tiktok import tiktok_service

logger = logging.getLogger(__name__)

INTERVALS = {
    "1h": timedelta(hours=1),
    "6h": timedelta(hours=6),
    "24h": timedelta(hours=24),
    "72h": timedelta(hours=72),
    "7d": timedelta(days=7),
}


async def collect_metrics_for_post(db: Session, post: Post, interval: str) -> Optional[PostMetrics]:
    """Fetch and store metrics for a post at a given interval."""
    if not post.platform_post_id:
        logger.warning(f"Post {post.id} has no platform ID — cannot collect metrics")
        return None

    # Check if we've already collected this interval
    existing = db.query(PostMetrics).filter(
        PostMetrics.post_id == post.id,
        PostMetrics.interval == interval,
    ).first()
    if existing:
        return existing

    try:
        if post.platform == Platform.instagram:
            raw = await instagram_service.get_post_insights(post.platform_post_id)
        else:
            raw = await tiktok_service.get_video_metrics(post.platform_post_id)
    except Exception as e:
        logger.error(f"Failed to collect metrics for post {post.id} at {interval}: {e}")
        return None

    m = PostMetrics(
        post_id=post.id,
        interval=interval,
        views=raw.get("views", 0),
        likes=raw.get("likes", 0),
        comments=raw.get("comments", 0),
        shares=raw.get("shares", 0),
        saves=raw.get("saves", 0),
        completion_rate=raw.get("completion_rate", 0.0),
        reach=raw.get("reach", 0),
        impressions=raw.get("impressions", 0),
        engagement_rate=raw.get("engagement_rate", 0.0),
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    logger.info(f"Metrics collected for post {post.id} at {interval}: {raw.get('views', 0)} views")
    return m


async def run_metrics_collection(db: Session):
    """Scheduled task — collect metrics for all published posts at the right intervals."""
    now = datetime.utcnow()
    published_posts = db.query(Post).filter(Post.status == PostStatus.published).all()

    for post in published_posts:
        if not post.published_time:
            continue
        age = now - post.published_time.replace(tzinfo=None)

        for interval, delta in INTERVALS.items():
            if age >= delta:
                await collect_metrics_for_post(db, post, interval)


def get_rolling_averages(db: Session, days: int = 30) -> Dict[str, float]:
    """Calculate rolling average performance metrics over the last N days."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    metrics = (
        db.query(PostMetrics)
        .join(Post)
        .filter(
            Post.published_time >= cutoff,
            PostMetrics.interval == "24h",
        )
        .all()
    )

    if not metrics:
        return {"avg_views": 500, "avg_likes": 50, "avg_engagement_rate": 4.0, "avg_saves": 25, "sample_size": 0}

    total_views = sum(m.views for m in metrics)
    total_likes = sum(m.likes for m in metrics)
    total_eng = sum(m.engagement_rate for m in metrics)
    total_saves = sum(m.saves for m in metrics)
    n = len(metrics)

    return {
        "avg_views": round(total_views / n, 0),
        "avg_likes": round(total_likes / n, 0),
        "avg_engagement_rate": round(total_eng / n, 2),
        "avg_saves": round(total_saves / n, 0),
        "sample_size": n,
    }


def get_per_platform_stats(db: Session, days: int = 7) -> Dict[str, Any]:
    """Break down performance by platform."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    result = {}

    for platform in [Platform.instagram, Platform.tiktok]:
        metrics = (
            db.query(PostMetrics)
            .join(Post)
            .filter(
                Post.platform == platform,
                Post.published_time >= cutoff,
                PostMetrics.interval == "24h",
            )
            .all()
        )
        if metrics:
            n = len(metrics)
            result[platform.value] = {
                "posts": n,
                "avg_views": round(sum(m.views for m in metrics) / n, 0),
                "avg_engagement_rate": round(sum(m.engagement_rate for m in metrics) / n, 2),
                "avg_saves": round(sum(m.saves for m in metrics) / n, 0),
            }
        else:
            result[platform.value] = {"posts": 0, "avg_views": 0, "avg_engagement_rate": 0, "avg_saves": 0}

    return result


def get_top_posts(db: Session, days: int = 30, limit: int = 5) -> List[Post]:
    """Return top performing posts by views over the last N days."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    top = (
        db.query(Post)
        .join(PostMetrics)
        .filter(
            Post.published_time >= cutoff,
            PostMetrics.interval == "24h",
        )
        .order_by(PostMetrics.views.desc())
        .limit(limit)
        .all()
    )
    return top


def get_follower_growth_estimate(db: Session, days: int = 7) -> int:
    """Estimate follower growth based on metrics data."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    metrics = (
        db.query(PostMetrics)
        .join(Post)
        .filter(Post.published_time >= cutoff, PostMetrics.interval == "24h")
        .all()
    )
    return sum(m.follower_growth for m in metrics)
