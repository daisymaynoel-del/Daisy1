from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from schemas import PostMetricsOut, DashboardStats, PostOut
from services.analytics import (
    get_rolling_averages, get_per_platform_stats,
    get_top_posts, get_follower_growth_estimate,
)
from models import Post, PostMetrics, PostStatus
from routes.posts import _post_to_schema, _metrics_to_schema
from datetime import datetime, timedelta

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/dashboard", response_model=DashboardStats)
def dashboard_stats(db: Session = Depends(get_db)):
    """Aggregate stats for the dashboard overview."""
    rolling = get_rolling_averages(db, days=7)
    top_posts = get_top_posts(db, days=7, limit=1)
    follower_growth = get_follower_growth_estimate(db, days=7)

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    ig_today = db.query(Post).filter(
        Post.platform == "instagram",
        Post.published_time >= today_start,
        Post.status == PostStatus.published,
    ).count()

    tt_today = db.query(Post).filter(
        Post.platform == "tiktok",
        Post.published_time >= today_start,
        Post.status == PostStatus.published,
    ).count()

    pending_count = db.query(Post).filter(Post.status == PostStatus.pending_approval).count()
    total_published = db.query(Post).filter(Post.status == PostStatus.published).count()
    total_pending = db.query(Post).filter(Post.status.in_([PostStatus.pending_approval, PostStatus.scheduled])).count()

    from models import Trend
    active_trends = db.query(Trend).filter(Trend.is_active == True).count()

    top_post_schema = _post_to_schema(top_posts[0]) if top_posts else None

    return DashboardStats(
        total_posts_published=total_published,
        total_posts_pending=total_pending,
        avg_views_7d=rolling.get("avg_views", 0),
        avg_engagement_rate_7d=rolling.get("avg_engagement_rate", 0),
        follower_growth_7d=follower_growth,
        top_performing_post=top_post_schema,
        pending_approval_count=pending_count,
        active_trends_count=active_trends,
        instagram_posts_today=ig_today,
        tiktok_posts_today=tt_today,
    )


@router.get("/rolling-averages")
def rolling_averages(days: int = 30, db: Session = Depends(get_db)):
    return get_rolling_averages(db, days=days)


@router.get("/by-platform")
def by_platform(days: int = 7, db: Session = Depends(get_db)):
    return get_per_platform_stats(db, days=days)


@router.get("/post/{post_id}/history", response_model=List[PostMetricsOut])
def post_metrics_history(post_id: int, db: Session = Depends(get_db)):
    metrics = db.query(PostMetrics).filter(
        PostMetrics.post_id == post_id
    ).order_by(PostMetrics.collected_at).all()
    return [_metrics_to_schema(m) for m in metrics]


@router.get("/post/{post_id}/vs-average")
def post_vs_average(post_id: int, db: Session = Depends(get_db)):
    """Compare a specific post's 24h metrics against the rolling average."""
    post_metrics = db.query(PostMetrics).filter(
        PostMetrics.post_id == post_id,
        PostMetrics.interval == "24h",
    ).first()

    if not post_metrics:
        return {"error": "24h metrics not yet available for this post"}

    rolling = get_rolling_averages(db, days=30)

    return {
        "post": {
            "views": post_metrics.views,
            "likes": post_metrics.likes,
            "engagement_rate": post_metrics.engagement_rate,
            "saves": post_metrics.saves,
        },
        "rolling_average": {
            "views": rolling.get("avg_views", 0),
            "likes": rolling.get("avg_likes", 0),
            "engagement_rate": rolling.get("avg_engagement_rate", 0),
            "saves": rolling.get("avg_saves", 0),
        },
        "performance_ratio": round(post_metrics.views / max(rolling.get("avg_views", 1), 1), 2),
    }


@router.get("/top-posts")
def top_posts(days: int = 30, limit: int = 10, db: Session = Depends(get_db)):
    posts = get_top_posts(db, days=days, limit=limit)
    return [_post_to_schema(p) for p in posts]
