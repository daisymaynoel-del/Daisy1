import json
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from schemas import Suggestion
from models import ContentAsset, Pattern, Trend, Platform, ContentPillar
from services.ai_engine import generate_post_suggestions
from services.analytics import get_rolling_averages
from services.learning import get_best_patterns

router = APIRouter(prefix="/suggestions", tags=["suggestions"])


@router.get("/next-posts", response_model=List[Suggestion])
async def next_post_suggestions(db: Session = Depends(get_db)):
    """Return 5 AI-recommended next posts based on what's working."""
    rolling = get_rolling_averages(db, days=30)
    patterns = get_best_patterns(db, limit=10)
    active_trends = db.query(Trend).filter(
        Trend.is_active == True,
        Trend.saturation_level.in_(["low", "medium"]),
    ).order_by(Trend.relevance_score.desc()).limit(20).all()

    assets = db.query(ContentAsset).order_by(ContentAsset.created_at.desc()).limit(10).all()

    recent_perf = [
        {
            "avg_views": rolling.get("avg_views", 0),
            "avg_engagement_rate": rolling.get("avg_engagement_rate", 0),
            "sample_size": rolling.get("sample_size", 0),
        }
    ]
    patterns_data = [
        {"type": p.pattern_type.value, "value": p.pattern_value, "score": p.performance_score}
        for p in patterns
    ]
    trends_data = [
        {"platform": t.platform.value, "type": t.trend_type.value, "value": t.trend_value, "score": t.relevance_score}
        for t in active_trends
    ]
    assets_data = [
        {"id": a.id, "type": a.asset_type.value, "tags": json.loads(a.tags) if a.tags else []}
        for a in assets
    ]

    raw_suggestions = generate_post_suggestions(recent_perf, patterns_data, trends_data, assets_data)

    result = []
    for s in raw_suggestions:
        try:
            result.append(Suggestion(
                rank=s.get("rank", len(result) + 1),
                platform=Platform(s.get("platform", "instagram")),
                content_pillar=ContentPillar(s.get("content_pillar", "transformation")),
                hook=s.get("hook", ""),
                caption_preview=s.get("caption_preview", ""),
                suggested_audio=s.get("suggested_audio", ""),
                reasoning=s.get("reasoning", ""),
                predicted_views=s.get("predicted_views", 1000),
                confidence=s.get("confidence", 0.5),
            ))
        except Exception:
            continue
    return result
