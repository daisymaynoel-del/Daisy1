"""
Trend research service.
In production, integrates with Instagram Hashtag Search API and TikTok Research API.
In demo mode, generates realistic synthetic trend data for EASTEND's niche.
"""
import logging
import json
import random
from datetime import date, timedelta
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from models import Trend, ViralBenchmark, Platform, TrendType
from config import settings

logger = logging.getLogger(__name__)

HAIR_HASHTAGS_INSTAGRAM = [
    "#HairTransformation", "#HairColour", "#HairGoals", "#SalonLife",
    "#LondonHair", "#EastLondon", "#HairEducation", "#HairTips",
    "#ColourCorrectionSpecialist", "#BalayageHair", "#HairHighlights",
    "#NaturalHair", "#HairCare", "#SalonVibes", "#HairInspo",
    "#BlondeHair", "#BrunettHair", "#HairStylist", "#HairdresserLife",
    "#ClientTransformation",
]

HAIR_TRENDING_SOUNDS = [
    "BIRDS OF A FEATHER — Billie Eilish",
    "APT. — ROSÉ & Bruno Mars",
    "Die With A Smile — Lady Gaga & Bruno Mars",
    "Espresso — Sabrina Carpenter",
    "Good Luck, Babe! — Chappell Roan",
    "original audio — trending tutorial sound",
    "MONTERO — Lil Nas X",
    "Levitating — Dua Lipa",
    "As It Was — Harry Styles",
    "Blinding Lights — The Weeknd",
    "Trending voiceover audio",
    "Aesthetic background music — trending",
    "POV audio — educational",
    "Transformation reveal sound",
]

TIKTOK_TRENDING_SOUNDS = [
    "APT. — ROSÉ & Bruno Mars",
    "BIRDS OF A FEATHER — Billie Eilish",
    "Stacy's Mom — Fountains of Wayne (TikTok remix)",
    "After Hours — The Weeknd",
    "Espresso — Sabrina Carpenter",
    "Moonlight Sonata — TikTok trend",
    "original sound — @hairtrends",
    "POV: you're at the best salon in East London",
    "Trending hair tutorial audio",
    "Satisfying transformation sound",
    "REMIX trending sound",
    "Before and after reveal audio",
]

VIRAL_BENCHMARK_TEMPLATES = [
    {
        "hook_text": "POV: you finally booked the appointment",
        "audio_name": "APT. — ROSÉ & Bruno Mars",
        "cta": "Book via link in bio",
        "views": 250000,
        "likes": 18000,
        "completion_rate": 0.78,
        "video_length_seconds": 15,
    },
    {
        "hook_text": "Before → After (you won't believe it)",
        "audio_name": "BIRDS OF A FEATHER — Billie Eilish",
        "cta": "DM to book",
        "views": 180000,
        "likes": 12000,
        "completion_rate": 0.82,
        "video_length_seconds": 12,
    },
    {
        "hook_text": "Stop washing your hair wrong 🛑",
        "audio_name": "Trending educational audio",
        "cta": "Save this post",
        "views": 320000,
        "likes": 25000,
        "completion_rate": 0.91,
        "video_length_seconds": 30,
    },
    {
        "hook_text": "This colour took 4 hours (worth it)",
        "audio_name": "Aesthetic background music",
        "cta": "Link in bio to book",
        "views": 95000,
        "likes": 8500,
        "completion_rate": 0.72,
        "video_length_seconds": 20,
    },
    {
        "hook_text": "Day in the life at our East London salon",
        "audio_name": "Die With A Smile — Lady Gaga & Bruno Mars",
        "cta": "Follow for more",
        "views": 45000,
        "likes": 3200,
        "completion_rate": 0.65,
        "video_length_seconds": 45,
    },
]


async def refresh_trends(db: Session) -> Dict[str, int]:
    """
    Daily trend refresh. In production, queries Instagram + TikTok APIs.
    Returns count of new trends added.
    """
    added = {"hashtags": 0, "sounds": 0, "benchmarks": 0}
    today = date.today()

    # Mark old trends as potentially saturated
    old_trends = db.query(Trend).filter(
        Trend.discovery_date < today - timedelta(days=14),
        Trend.is_active == True,
    ).all()
    for t in old_trends:
        if t.saturation_level == "low":
            t.saturation_level = "medium"
        elif t.saturation_level == "medium":
            t.saturation_level = "high"

    if settings.demo_mode:
        added = _seed_demo_trends(db, today)
    else:
        added = await _fetch_live_trends(db, today)

    db.commit()
    logger.info(f"Trend refresh complete: {added}")
    return added


def _seed_demo_trends(db: Session, today: date) -> Dict[str, int]:
    added = {"hashtags": 0, "sounds": 0, "benchmarks": 0}

    # Add Instagram hashtags
    ig_hashtags = random.sample(HAIR_HASHTAGS_INSTAGRAM, min(8, len(HAIR_HASHTAGS_INSTAGRAM)))
    for tag in ig_hashtags:
        existing = db.query(Trend).filter(
            Trend.trend_value == tag,
            Trend.platform == Platform.instagram,
            Trend.discovery_date == today,
        ).first()
        if not existing:
            t = Trend(
                platform=Platform.instagram,
                trend_type=TrendType.hashtag,
                trend_value=tag,
                discovery_date=today,
                saturation_level=random.choice(["low", "low", "medium"]),
                relevance_score=random.uniform(0.6, 0.95),
                use_count=random.randint(50000, 2000000),
                growth_rate=random.uniform(0.05, 0.35),
            )
            db.add(t)
            added["hashtags"] += 1

    # Add trending sounds
    ig_sounds = random.sample(HAIR_TRENDING_SOUNDS, min(5, len(HAIR_TRENDING_SOUNDS)))
    for sound in ig_sounds:
        existing = db.query(Trend).filter(
            Trend.trend_value == sound,
            Trend.platform == Platform.instagram,
            Trend.discovery_date == today,
        ).first()
        if not existing:
            t = Trend(
                platform=Platform.instagram,
                trend_type=TrendType.sound,
                trend_value=sound,
                discovery_date=today,
                saturation_level=random.choice(["low", "medium"]),
                relevance_score=random.uniform(0.55, 0.90),
                use_count=random.randint(10000, 500000),
                growth_rate=random.uniform(0.1, 0.5),
            )
            db.add(t)
            added["sounds"] += 1

    # TikTok sounds
    tt_sounds = random.sample(TIKTOK_TRENDING_SOUNDS, min(5, len(TIKTOK_TRENDING_SOUNDS)))
    for sound in tt_sounds:
        existing = db.query(Trend).filter(
            Trend.trend_value == sound,
            Trend.platform == Platform.tiktok,
            Trend.discovery_date == today,
        ).first()
        if not existing:
            t = Trend(
                platform=Platform.tiktok,
                trend_type=TrendType.sound,
                trend_value=sound,
                discovery_date=today,
                saturation_level=random.choice(["low", "low", "medium"]),
                relevance_score=random.uniform(0.65, 0.95),
                use_count=random.randint(20000, 1000000),
                growth_rate=random.uniform(0.15, 0.60),
            )
            db.add(t)
            added["sounds"] += 1

    # Add viral benchmarks (only if we have fewer than 20)
    existing_benchmarks = db.query(ViralBenchmark).count()
    if existing_benchmarks < 20:
        for template in random.sample(VIRAL_BENCHMARK_TEMPLATES, min(3, len(VIRAL_BENCHMARK_TEMPLATES))):
            b = ViralBenchmark(
                platform=random.choice([Platform.instagram, Platform.tiktok]),
                account="@viral_hair_account",
                audio_name=template["audio_name"],
                hook_text=template["hook_text"],
                video_length_seconds=template["video_length_seconds"],
                views=template["views"] + random.randint(-10000, 10000),
                likes=template["likes"] + random.randint(-1000, 1000),
                completion_rate=template["completion_rate"],
                cta=template["cta"],
                aspect_ratio="9:16",
                niche_tags=json.dumps(["#HairTransformation", "#SalonLife", "#LondonHair"]),
            )
            db.add(b)
            added["benchmarks"] += 1

    return added


async def _fetch_live_trends(db: Session, today: date) -> Dict[str, int]:
    """Placeholder for live Instagram + TikTok API trend fetching."""
    logger.info("Live trend fetching not yet configured — using demo data")
    return _seed_demo_trends(db, today)


def get_trending_sounds_for_pillar(db: Session, platform: str, pillar: str) -> List[str]:
    """Return the top 5 trending-but-not-saturated sounds for a content pillar."""
    sounds = (
        db.query(Trend)
        .filter(
            Trend.platform == platform,
            Trend.trend_type == TrendType.sound,
            Trend.is_active == True,
            Trend.saturation_level.in_(["low", "medium"]),
        )
        .order_by(Trend.relevance_score.desc())
        .limit(5)
        .all()
    )
    if sounds:
        return [s.trend_value for s in sounds]

    # Fallback
    return TIKTOK_TRENDING_SOUNDS[:3] if platform == "tiktok" else HAIR_TRENDING_SOUNDS[:3]
