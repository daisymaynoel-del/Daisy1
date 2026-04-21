import json
from typing import List, Optional
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from database import get_db
from models import Trend, ViralBenchmark, Platform, TrendType
from schemas import TrendOut, ViralBenchmarkCreate, ViralBenchmarkOut
from services.trends import refresh_trends
from datetime import date

router = APIRouter(prefix="/trends", tags=["trends"])


@router.get("/", response_model=List[TrendOut])
def list_trends(
    platform: Optional[str] = None,
    trend_type: Optional[str] = None,
    active_only: bool = True,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    query = db.query(Trend)
    if platform:
        query = query.filter(Trend.platform == platform)
    if trend_type:
        query = query.filter(Trend.trend_type == trend_type)
    if active_only:
        query = query.filter(Trend.is_active == True)
    trends = query.order_by(Trend.relevance_score.desc()).limit(limit).all()
    return [_trend_to_schema(t) for t in trends]


@router.get("/sounds", response_model=List[TrendOut])
def trending_sounds(platform: Optional[str] = None, db: Session = Depends(get_db)):
    """Get trending-but-not-saturated sounds (the sweet spot)."""
    query = db.query(Trend).filter(
        Trend.trend_type == TrendType.sound,
        Trend.is_active == True,
        Trend.saturation_level.in_(["low", "medium"]),
    )
    if platform:
        query = query.filter(Trend.platform == platform)
    sounds = query.order_by(Trend.growth_rate.desc()).limit(20).all()
    return [_trend_to_schema(t) for t in sounds]


@router.get("/hashtags", response_model=List[TrendOut])
def trending_hashtags(platform: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Trend).filter(
        Trend.trend_type == TrendType.hashtag,
        Trend.is_active == True,
    )
    if platform:
        query = query.filter(Trend.platform == platform)
    hashtags = query.order_by(Trend.relevance_score.desc()).limit(30).all()
    return [_trend_to_schema(t) for t in hashtags]


@router.post("/refresh")
async def trigger_trend_refresh(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Manually trigger a trend research refresh."""
    background_tasks.add_task(refresh_trends, db)
    return {"message": "Trend refresh started in background"}


@router.get("/viral-benchmarks", response_model=List[ViralBenchmarkOut])
def list_viral_benchmarks(
    platform: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    query = db.query(ViralBenchmark).filter(ViralBenchmark.is_active == True)
    if platform:
        query = query.filter(ViralBenchmark.platform == platform)
    benchmarks = query.order_by(ViralBenchmark.views.desc()).limit(limit).all()
    return [_benchmark_to_schema(b) for b in benchmarks]


@router.post("/viral-benchmarks", response_model=ViralBenchmarkOut, status_code=201)
def add_viral_benchmark(data: ViralBenchmarkCreate, db: Session = Depends(get_db)):
    """Manually add a viral video to track as a benchmark."""
    benchmark = ViralBenchmark(
        platform=data.platform,
        video_url=data.video_url,
        account=data.account,
        audio_name=data.audio_name,
        hook_text=data.hook_text,
        video_length_seconds=data.video_length_seconds,
        views=data.views,
        likes=data.likes,
        comments=data.comments,
        shares=data.shares,
        completion_rate=data.completion_rate,
        cta=data.cta,
        aspect_ratio=data.aspect_ratio,
        niche_tags=json.dumps(data.niche_tags or []),
        notes=data.notes,
    )
    db.add(benchmark)
    db.commit()
    db.refresh(benchmark)
    return _benchmark_to_schema(benchmark)


def _trend_to_schema(t: Trend) -> TrendOut:
    return TrendOut(
        id=t.id, platform=t.platform, trend_type=t.trend_type,
        trend_value=t.trend_value, discovery_date=t.discovery_date,
        saturation_level=t.saturation_level or "low",
        relevance_score=t.relevance_score or 0,
        use_count=t.use_count or 0, growth_rate=t.growth_rate or 0,
        is_active=t.is_active, last_updated=t.last_updated,
    )


def _benchmark_to_schema(b: ViralBenchmark) -> ViralBenchmarkOut:
    niche_tags = json.loads(b.niche_tags) if b.niche_tags else []
    return ViralBenchmarkOut(
        id=b.id, platform=b.platform, video_url=b.video_url,
        account=b.account, audio_name=b.audio_name, hook_text=b.hook_text,
        video_length_seconds=b.video_length_seconds, views=b.views or 0,
        likes=b.likes or 0, comments=b.comments or 0, shares=b.shares or 0,
        completion_rate=b.completion_rate, cta=b.cta,
        aspect_ratio=b.aspect_ratio or "9:16", niche_tags=niche_tags,
        notes=b.notes, discovered_at=b.discovered_at, is_active=b.is_active,
    )
