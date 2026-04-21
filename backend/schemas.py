from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime, date
from models import PostStatus, Platform, ContentPillar, AssetType, TrendType, PatternType


# ── ContentAsset ──────────────────────────────────────────────────────────────

class ContentAssetBase(BaseModel):
    filename: str
    asset_type: AssetType
    tags: Optional[List[str]] = []
    notes: Optional[str] = None


class ContentAssetCreate(ContentAssetBase):
    pass


class ContentAssetOut(ContentAssetBase):
    id: int
    original_filename: Optional[str]
    file_path: str
    thumbnail_path: Optional[str]
    duration_seconds: Optional[float]
    file_size_bytes: Optional[int]
    width: Optional[int]
    height: Optional[int]
    ai_analysis: Optional[Any]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Post ──────────────────────────────────────────────────────────────────────

class PostBase(BaseModel):
    platform: Platform
    content_type: str = "reel"
    caption: Optional[str] = None
    hashtags: Optional[List[str]] = []
    audio_name: Optional[str] = None
    audio_id: Optional[str] = None
    hook_text: Optional[str] = None
    content_pillar: Optional[ContentPillar] = None
    scheduled_time: Optional[datetime] = None
    patch_test_included: bool = False


class PostCreate(PostBase):
    asset_id: Optional[int] = None
    viral_benchmark_id: Optional[int] = None


class PostUpdate(BaseModel):
    caption: Optional[str] = None
    hashtags: Optional[List[str]] = None
    audio_name: Optional[str] = None
    hook_text: Optional[str] = None
    scheduled_time: Optional[datetime] = None
    content_pillar: Optional[ContentPillar] = None
    patch_test_included: Optional[bool] = None


class PostOut(PostBase):
    id: int
    status: PostStatus
    asset_id: Optional[int]
    thumbnail_path: Optional[str]
    published_time: Optional[datetime]
    platform_post_id: Optional[str]
    platform_url: Optional[str]
    viral_benchmark_id: Optional[int]
    ai_confidence_score: Optional[float]
    predicted_performance: Optional[float]
    needs_review: bool
    review_reason: Optional[str]
    created_at: datetime
    approved_at: Optional[datetime]
    rejection_reason: Optional[str]

    class Config:
        from_attributes = True


class PostWithMetrics(PostOut):
    latest_metrics: Optional["PostMetricsOut"] = None
    metrics_history: List["PostMetricsOut"] = []


# ── PostMetrics ───────────────────────────────────────────────────────────────

class PostMetricsOut(BaseModel):
    id: int
    post_id: int
    collected_at: datetime
    interval: str
    views: int
    likes: int
    comments: int
    shares: int
    saves: int
    completion_rate: float
    follower_growth: int
    reach: int
    impressions: int
    engagement_rate: float

    class Config:
        from_attributes = True


# ── ViralBenchmark ────────────────────────────────────────────────────────────

class ViralBenchmarkCreate(BaseModel):
    platform: Platform
    video_url: Optional[str] = None
    account: Optional[str] = None
    audio_name: Optional[str] = None
    hook_text: Optional[str] = None
    video_length_seconds: Optional[int] = None
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    completion_rate: Optional[float] = None
    cta: Optional[str] = None
    aspect_ratio: Optional[str] = "9:16"
    niche_tags: Optional[List[str]] = []
    notes: Optional[str] = None


class ViralBenchmarkOut(ViralBenchmarkCreate):
    id: int
    discovered_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


# ── Trend ─────────────────────────────────────────────────────────────────────

class TrendOut(BaseModel):
    id: int
    platform: Platform
    trend_type: TrendType
    trend_value: str
    discovery_date: date
    saturation_level: str
    relevance_score: float
    use_count: int
    growth_rate: float
    is_active: bool
    last_updated: datetime

    class Config:
        from_attributes = True


# ── Pattern ───────────────────────────────────────────────────────────────────

class PatternOut(BaseModel):
    id: int
    pattern_type: PatternType
    pattern_value: str
    performance_score: float
    sample_size: int
    avg_views: float
    avg_engagement_rate: float
    notes: Optional[str]
    last_updated: datetime

    class Config:
        from_attributes = True


# ── StrategyReport ────────────────────────────────────────────────────────────

class StrategyReportOut(BaseModel):
    id: int
    report_date: date
    week_start: Optional[date]
    week_end: Optional[date]
    total_posts: int
    avg_views: float
    avg_engagement_rate: float
    top_performing_post_id: Optional[int]
    worst_performing_post_id: Optional[int]
    report_content: Optional[str]
    wins: Optional[List[str]]
    losses: Optional[List[str]]
    next_week_direction: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Dashboard Stats ───────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_posts_published: int
    total_posts_pending: int
    avg_views_7d: float
    avg_engagement_rate_7d: float
    follower_growth_7d: int
    top_performing_post: Optional[PostOut]
    pending_approval_count: int
    active_trends_count: int
    instagram_posts_today: int
    tiktok_posts_today: int


class Suggestion(BaseModel):
    rank: int
    platform: Platform
    content_pillar: ContentPillar
    hook: str
    caption_preview: str
    suggested_audio: str
    reasoning: str
    predicted_views: int
    confidence: float


class ApprovalAction(BaseModel):
    action: str = Field(..., pattern="^(approve|reject)$")
    scheduled_time: Optional[datetime] = None
    rejection_reason: Optional[str] = None


class GeneratePostRequest(BaseModel):
    asset_id: int
    platform: Platform
    content_pillar: Optional[ContentPillar] = None
    viral_benchmark_id: Optional[int] = None
    custom_notes: Optional[str] = None
