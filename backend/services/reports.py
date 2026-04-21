"""
Strategy report generation service.
Produces weekly markdown reports using AI analysis of performance data.
"""
import json
import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from models import StrategyReport, Post, PostMetrics, Pattern, PostStatus
from services.analytics import get_rolling_averages, get_top_posts
from services.learning import get_best_patterns
from services.ai_engine import generate_weekly_report

logger = logging.getLogger(__name__)


async def generate_weekly_strategy_report(db: Session) -> StrategyReport:
    """Generate and store a weekly strategy report."""
    today = date.today()
    week_start = today - timedelta(days=7)
    week_end = today

    # Gather data
    rolling = get_rolling_averages(db, days=7)
    top_posts = get_top_posts(db, days=7, limit=3)
    patterns = get_best_patterns(db, limit=10)

    # Posts this week
    published_this_week = db.query(Post).filter(
        Post.published_time >= datetime.combine(week_start, datetime.min.time()),
        Post.status == PostStatus.published,
    ).all()

    # Worst performing posts
    worst_posts = (
        db.query(Post)
        .join(PostMetrics)
        .filter(
            Post.published_time >= datetime.combine(week_start, datetime.min.time()),
            PostMetrics.interval == "24h",
        )
        .order_by(PostMetrics.views.asc())
        .limit(3)
        .all()
    )

    # Serialise for AI
    week_data = {
        "week": f"{week_start} to {week_end}",
        "total_posts": len(published_this_week),
        "avg_views": rolling.get("avg_views", 0),
        "avg_engagement_rate": rolling.get("avg_engagement_rate", 0),
        "platform_breakdown": _platform_breakdown(published_this_week),
        "pillar_breakdown": _pillar_breakdown(published_this_week),
    }

    top_posts_data = [_serialise_post_for_report(p, db) for p in top_posts]
    worst_posts_data = [_serialise_post_for_report(p, db) for p in worst_posts]
    patterns_data = [{"type": p.pattern_type.value, "value": p.pattern_value, "score": p.performance_score} for p in patterns]

    ai_report = generate_weekly_report(week_data, patterns_data, top_posts_data, worst_posts_data)

    # Store report
    report = StrategyReport(
        report_date=today,
        week_start=week_start,
        week_end=week_end,
        total_posts=len(published_this_week),
        avg_views=rolling.get("avg_views", 0),
        avg_engagement_rate=rolling.get("avg_engagement_rate", 0),
        top_performing_post_id=top_posts[0].id if top_posts else None,
        worst_performing_post_id=worst_posts[0].id if worst_posts else None,
        report_content=ai_report.get("report_markdown", ""),
        wins=json.dumps(ai_report.get("wins", [])),
        losses=json.dumps(ai_report.get("losses", [])),
        next_week_direction=ai_report.get("next_week_direction", ""),
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    logger.info(f"Weekly strategy report created: {report.id}")
    return report


def _platform_breakdown(posts: List[Post]) -> Dict:
    result = {"instagram": 0, "tiktok": 0}
    for p in posts:
        result[p.platform.value] = result.get(p.platform.value, 0) + 1
    return result


def _pillar_breakdown(posts: List[Post]) -> Dict:
    result = {}
    for p in posts:
        pillar = p.content_pillar.value if p.content_pillar else "unknown"
        result[pillar] = result.get(pillar, 0) + 1
    return result


def _serialise_post_for_report(post: Post, db: Session) -> Dict[str, Any]:
    metrics = (
        db.query(PostMetrics)
        .filter(PostMetrics.post_id == post.id, PostMetrics.interval == "24h")
        .first()
    )
    return {
        "id": post.id,
        "platform": post.platform.value,
        "pillar": post.content_pillar.value if post.content_pillar else None,
        "hook": post.hook_text,
        "audio": post.audio_name,
        "views": metrics.views if metrics else 0,
        "engagement_rate": metrics.engagement_rate if metrics else 0,
        "saves": metrics.saves if metrics else 0,
    }
