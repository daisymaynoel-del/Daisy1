import json
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from database import get_db
from models import Post, PostMetrics, PostStatus, Platform
from schemas import (
    PostOut, PostCreate, PostUpdate, PostWithMetrics,
    GeneratePostRequest, ApprovalAction,
)
from services.content import generate_post_from_asset, get_next_posting_slot
from services.learning import update_pattern_library
from config import settings

router = APIRouter(prefix="/posts", tags=["posts"])


@router.post("/generate", response_model=PostOut, status_code=status.HTTP_201_CREATED)
async def generate_post(req: GeneratePostRequest, db: Session = Depends(get_db)):
    """Generate a post from an existing asset using AI."""
    try:
        post = await generate_post_from_asset(
            db=db,
            asset_id=req.asset_id,
            platform=req.platform.value,
            content_pillar=req.content_pillar.value if req.content_pillar else None,
            viral_benchmark_id=req.viral_benchmark_id,
            custom_notes=req.custom_notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _post_to_schema(post)


@router.post("/", response_model=PostOut, status_code=status.HTTP_201_CREATED)
def create_post(data: PostCreate, db: Session = Depends(get_db)):
    """Create a post manually (without AI generation)."""
    post = Post(
        platform=data.platform,
        content_type=data.content_type,
        asset_id=data.asset_id,
        caption=data.caption,
        hashtags=json.dumps(data.hashtags or []),
        audio_name=data.audio_name,
        hook_text=data.hook_text,
        content_pillar=data.content_pillar,
        scheduled_time=data.scheduled_time,
        patch_test_included=data.patch_test_included,
        status=PostStatus.pending_approval if settings.approval_required else PostStatus.approved,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return _post_to_schema(post)


@router.get("/", response_model=List[PostOut])
def list_posts(
    platform: Optional[str] = None,
    status: Optional[str] = None,
    pillar: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    query = db.query(Post)
    if platform:
        query = query.filter(Post.platform == platform)
    if status:
        query = query.filter(Post.status == status)
    if pillar:
        query = query.filter(Post.content_pillar == pillar)
    posts = query.order_by(Post.created_at.desc()).offset(skip).limit(limit).all()
    return [_post_to_schema(p) for p in posts]


@router.get("/pending-approval", response_model=List[PostOut])
def get_pending_approval(db: Session = Depends(get_db)):
    """Get all posts waiting for user approval."""
    posts = db.query(Post).filter(
        Post.status == PostStatus.pending_approval
    ).order_by(Post.created_at.asc()).all()
    return [_post_to_schema(p) for p in posts]


@router.get("/needs-review", response_model=List[PostOut])
def get_needs_review(db: Session = Depends(get_db)):
    """Get posts flagged for human review (predicted to underperform)."""
    posts = db.query(Post).filter(Post.needs_review == True).all()
    return [_post_to_schema(p) for p in posts]


@router.get("/{post_id}", response_model=PostWithMetrics)
def get_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    metrics_history = db.query(PostMetrics).filter(PostMetrics.post_id == post_id).order_by(PostMetrics.collected_at).all()
    latest = metrics_history[-1] if metrics_history else None

    schema = _post_to_schema(post)
    return PostWithMetrics(
        **schema.model_dump(),
        latest_metrics=_metrics_to_schema(latest) if latest else None,
        metrics_history=[_metrics_to_schema(m) for m in metrics_history],
    )


@router.patch("/{post_id}", response_model=PostOut)
def update_post(post_id: int, data: PostUpdate, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if post.status == PostStatus.published:
        raise HTTPException(status_code=400, detail="Cannot edit a published post")

    for field, value in data.model_dump(exclude_none=True).items():
        if field == "hashtags":
            value = json.dumps(value)
        setattr(post, field, value)

    db.commit()
    db.refresh(post)
    return _post_to_schema(post)


@router.post("/{post_id}/approve", response_model=PostOut)
def approve_post(
    post_id: int,
    action: ApprovalAction,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Approve or reject a post in the approval queue."""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if post.status not in [PostStatus.pending_approval, PostStatus.draft]:
        raise HTTPException(status_code=400, detail=f"Post is {post.status.value}, not pending approval")

    if action.action == "approve":
        post.status = PostStatus.scheduled
        post.approved_at = datetime.utcnow()
        if action.scheduled_time:
            post.scheduled_time = action.scheduled_time
        elif not post.scheduled_time:
            post.scheduled_time = get_next_posting_slot(db, post.platform.value)
    else:
        post.status = PostStatus.rejected
        post.rejection_reason = action.rejection_reason

    db.commit()
    db.refresh(post)

    # Update patterns after approval decisions
    background_tasks.add_task(update_pattern_library, db)
    return _post_to_schema(post)


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.status == PostStatus.published:
        raise HTTPException(status_code=400, detail="Cannot delete a published post")
    db.delete(post)
    db.commit()


def _post_to_schema(post: Post) -> PostOut:
    hashtags = json.loads(post.hashtags) if post.hashtags and isinstance(post.hashtags, str) else (post.hashtags or [])
    return PostOut(
        id=post.id,
        platform=post.platform,
        status=post.status,
        content_type=post.content_type,
        asset_id=post.asset_id,
        caption=post.caption,
        hashtags=hashtags,
        audio_name=post.audio_name,
        audio_id=post.audio_id,
        hook_text=post.hook_text,
        thumbnail_path=post.thumbnail_path,
        scheduled_time=post.scheduled_time,
        published_time=post.published_time,
        platform_post_id=post.platform_post_id,
        platform_url=post.platform_url,
        content_pillar=post.content_pillar,
        viral_benchmark_id=post.viral_benchmark_id,
        ai_confidence_score=post.ai_confidence_score,
        predicted_performance=post.predicted_performance,
        needs_review=post.needs_review or False,
        review_reason=post.review_reason,
        patch_test_included=post.patch_test_included or False,
        created_at=post.created_at,
        approved_at=post.approved_at,
        rejection_reason=post.rejection_reason,
    )


def _metrics_to_schema(m: PostMetrics):
    from schemas import PostMetricsOut
    return PostMetricsOut(
        id=m.id, post_id=m.post_id, collected_at=m.collected_at,
        interval=m.interval, views=m.views, likes=m.likes,
        comments=m.comments, shares=m.shares, saves=m.saves,
        completion_rate=m.completion_rate, follower_growth=m.follower_growth,
        reach=m.reach, impressions=m.impressions, engagement_rate=m.engagement_rate,
    )
