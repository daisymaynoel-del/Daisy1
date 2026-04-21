"""
Scheduler service — manages automated posting, metrics collection,
trend refreshes, and weekly reports.
"""
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Post, PostStatus, Platform
from config import settings

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone=settings.timezone)


def start_scheduler():
    # Publish due posts — check every 5 minutes
    scheduler.add_job(
        _publish_due_posts,
        trigger=IntervalTrigger(minutes=5),
        id="publish_due_posts",
        replace_existing=True,
    )

    # Collect metrics — check every 30 minutes
    scheduler.add_job(
        _collect_metrics,
        trigger=IntervalTrigger(minutes=30),
        id="collect_metrics",
        replace_existing=True,
    )

    # Refresh trends — daily at 06:00
    scheduler.add_job(
        _refresh_trends,
        trigger=CronTrigger(hour=6, minute=0, timezone=settings.timezone),
        id="refresh_trends",
        replace_existing=True,
    )

    # Update pattern library — daily at 08:00
    scheduler.add_job(
        _update_patterns,
        trigger=CronTrigger(hour=8, minute=0, timezone=settings.timezone),
        id="update_patterns",
        replace_existing=True,
    )

    # Weekly strategy report — every Monday at 09:00
    scheduler.add_job(
        _generate_weekly_report,
        trigger=CronTrigger(day_of_week="mon", hour=9, minute=0, timezone=settings.timezone),
        id="weekly_report",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")


async def _publish_due_posts():
    """Publish all posts that are scheduled and due."""
    db: Session = SessionLocal()
    try:
        now = datetime.utcnow()
        due_posts = db.query(Post).filter(
            Post.status == PostStatus.scheduled,
            Post.scheduled_time <= now,
        ).all()

        for post in due_posts:
            await _publish_post(db, post)
    finally:
        db.close()


async def _publish_post(db: Session, post: Post):
    """Publish a single post to its platform."""
    import json
    from services.instagram import instagram_service
    from services.tiktok import tiktok_service
    from services.content import _build_public_asset_url

    post.status = PostStatus.publishing
    db.commit()

    try:
        caption = post.caption or ""
        if post.hashtags:
            tags = json.loads(post.hashtags) if isinstance(post.hashtags, str) else post.hashtags
            caption += "\n\n" + " ".join(tags)

        asset = post.asset
        if not asset:
            raise ValueError(f"Post {post.id} has no asset")

        asset_url = _build_public_asset_url(asset.file_path)

        if post.platform == Platform.instagram:
            result = await instagram_service.publish_reel(
                video_url=asset_url,
                caption=caption,
                cover_url=_build_public_asset_url(asset.thumbnail_path) if asset.thumbnail_path else None,
            )
            post.platform_post_id = result.get("post_id")
            post.platform_url = result.get("permalink")
        else:
            result = await tiktok_service.publish_video(
                video_path=asset.file_path,
                title=post.hook_text or caption[:100],
                description=caption,
            )
            post.platform_post_id = result.get("post_id")
            post.platform_url = result.get("share_url")

        post.status = PostStatus.published
        post.published_time = datetime.utcnow()
        db.commit()
        logger.info(f"Post {post.id} published to {post.platform.value}: {post.platform_post_id}")

    except Exception as e:
        post.status = PostStatus.failed
        post.review_reason = str(e)
        db.commit()
        logger.error(f"Failed to publish post {post.id}: {e}")


async def _collect_metrics():
    db: Session = SessionLocal()
    try:
        from services.analytics import run_metrics_collection
        await run_metrics_collection(db)
    finally:
        db.close()


async def _refresh_trends():
    db: Session = SessionLocal()
    try:
        from services.trends import refresh_trends
        result = await refresh_trends(db)
        logger.info(f"Daily trend refresh: {result}")
    finally:
        db.close()


async def _update_patterns():
    db: Session = SessionLocal()
    try:
        from services.learning import update_pattern_library
        update_pattern_library(db)
    finally:
        db.close()


async def _generate_weekly_report():
    db: Session = SessionLocal()
    try:
        from services.reports import generate_weekly_strategy_report
        report = await generate_weekly_strategy_report(db)
        logger.info(f"Weekly report generated: ID {report.id}")
    finally:
        db.close()


def _build_public_asset_url(file_path: str) -> str:
    """Convert local file path to a publicly accessible URL for API calls."""
    if not file_path:
        return ""
    filename = file_path.replace("\\", "/").split("/")[-1]
    return f"http://localhost:8000/uploads/{filename}"
