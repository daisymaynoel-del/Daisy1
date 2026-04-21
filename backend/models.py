from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text,
    DateTime, Date, ForeignKey, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum


class PostStatus(str, enum.Enum):
    draft = "draft"
    pending_approval = "pending_approval"
    approved = "approved"
    scheduled = "scheduled"
    publishing = "publishing"
    published = "published"
    failed = "failed"
    rejected = "rejected"


class Platform(str, enum.Enum):
    instagram = "instagram"
    tiktok = "tiktok"


class ContentPillar(str, enum.Enum):
    transformation = "transformation"
    education = "education"
    process = "process"
    lifestyle = "lifestyle"


class AssetType(str, enum.Enum):
    video = "video"
    image = "image"


class TrendType(str, enum.Enum):
    sound = "sound"
    hashtag = "hashtag"
    format = "format"
    hook = "hook"


class PatternType(str, enum.Enum):
    hook = "hook"
    audio = "audio"
    caption_style = "caption_style"
    posting_time = "posting_time"
    hashtag_set = "hashtag_set"
    visual_style = "visual_style"
    length = "length"
    content_pillar = "content_pillar"


class ContentAsset(Base):
    __tablename__ = "content_assets"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    original_filename = Column(String)
    file_path = Column(String, nullable=False)
    thumbnail_path = Column(String)
    asset_type = Column(SAEnum(AssetType), nullable=False)
    duration_seconds = Column(Float)
    file_size_bytes = Column(Integer)
    width = Column(Integer)
    height = Column(Integer)
    tags = Column(Text)          # JSON array
    notes = Column(Text)
    ai_analysis = Column(Text)   # JSON: brand alignment score, suggested pillar, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    posts = relationship("Post", back_populates="asset")


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(SAEnum(Platform), nullable=False)
    status = Column(SAEnum(PostStatus), default=PostStatus.draft, nullable=False)
    content_type = Column(String, nullable=False)  # reel, story, carousel, tiktok_video
    asset_id = Column(Integer, ForeignKey("content_assets.id"))
    caption = Column(Text)
    hashtags = Column(Text)        # JSON array
    audio_name = Column(String)
    audio_id = Column(String)
    hook_text = Column(Text)
    thumbnail_path = Column(String)
    scheduled_time = Column(DateTime(timezone=True))
    published_time = Column(DateTime(timezone=True))
    platform_post_id = Column(String)   # ID from platform after publish
    platform_url = Column(String)
    content_pillar = Column(SAEnum(ContentPillar))
    viral_benchmark_id = Column(Integer, ForeignKey("viral_benchmarks.id"))
    ai_confidence_score = Column(Float)  # 0-100
    predicted_performance = Column(Float)  # estimated views
    needs_review = Column(Boolean, default=False)
    review_reason = Column(Text)
    patch_test_included = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    approved_at = Column(DateTime(timezone=True))
    rejection_reason = Column(Text)

    asset = relationship("ContentAsset", back_populates="posts")
    metrics = relationship("PostMetrics", back_populates="post", cascade="all, delete-orphan")
    viral_benchmark = relationship("ViralBenchmark")


class PostMetrics(Base):
    __tablename__ = "post_metrics"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    collected_at = Column(DateTime(timezone=True), server_default=func.now())
    interval = Column(String, nullable=False)  # 1h, 6h, 24h, 72h, 7d
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    saves = Column(Integer, default=0)
    completion_rate = Column(Float, default=0.0)
    follower_growth = Column(Integer, default=0)
    reach = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    engagement_rate = Column(Float, default=0.0)

    post = relationship("Post", back_populates="metrics")


class ViralBenchmark(Base):
    __tablename__ = "viral_benchmarks"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(SAEnum(Platform), nullable=False)
    video_url = Column(String)
    account = Column(String)
    discovered_at = Column(DateTime(timezone=True), server_default=func.now())
    audio_name = Column(String)
    audio_id = Column(String)
    hook_text = Column(Text)
    video_length_seconds = Column(Integer)
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    completion_rate = Column(Float)
    text_overlays = Column(Text)   # JSON
    cta = Column(String)
    aspect_ratio = Column(String)
    niche_tags = Column(Text)      # JSON
    notes = Column(Text)
    is_active = Column(Boolean, default=True)


class Trend(Base):
    __tablename__ = "trends"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(SAEnum(Platform), nullable=False)
    trend_type = Column(SAEnum(TrendType), nullable=False)
    trend_value = Column(String, nullable=False)
    trend_id = Column(String)
    discovery_date = Column(Date, nullable=False)
    saturation_level = Column(String, default="low")  # low, medium, high
    relevance_score = Column(Float, default=0.0)
    use_count = Column(Integer, default=0)
    growth_rate = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    last_updated = Column(DateTime(timezone=True), server_default=func.now())


class Pattern(Base):
    __tablename__ = "patterns"

    id = Column(Integer, primary_key=True, index=True)
    pattern_type = Column(SAEnum(PatternType), nullable=False)
    pattern_value = Column(String, nullable=False)
    performance_score = Column(Float, default=50.0)  # 0-100
    sample_size = Column(Integer, default=0)
    avg_views = Column(Float, default=0.0)
    avg_engagement_rate = Column(Float, default=0.0)
    last_updated = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(Text)


class StrategyReport(Base):
    __tablename__ = "strategy_reports"

    id = Column(Integer, primary_key=True, index=True)
    report_date = Column(Date, nullable=False)
    week_start = Column(Date)
    week_end = Column(Date)
    total_posts = Column(Integer, default=0)
    avg_views = Column(Float, default=0.0)
    avg_engagement_rate = Column(Float, default=0.0)
    top_performing_post_id = Column(Integer, ForeignKey("posts.id"))
    worst_performing_post_id = Column(Integer, ForeignKey("posts.id"))
    report_content = Column(Text)   # Full markdown report
    wins = Column(Text)             # JSON array
    losses = Column(Text)           # JSON array
    next_week_direction = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
