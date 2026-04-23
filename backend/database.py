from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from models import (  # noqa: F401
        ContentAsset, Post, PostMetrics, ViralBenchmark,
        Trend, Pattern, StrategyReport, Setting,
        ChatMessage, CreativeBrief,
    )
    Base.metadata.create_all(bind=engine)
    _seed_default_settings()


def _seed_default_settings():
    db = SessionLocal()
    try:
        from models import Setting
        defaults = {
            "approval_required": "true",
            "demo_mode": "true",
            "brand_name": "EASTEND",
            "brand_location": "East London",
            "patch_test_notice": "⚠️ Patch test required 48hrs before any colour service. DM us to arrange.",
            "instagram_hashtags_default": '["#EastEndSalon", "#EastLondonHair", "#LondonHair", "#HairTransformation", "#HairEducation", "#SalonLife", "#HairColour", "#EastLondon", "#LondonSalon", "#HairGoals"]',
            "tiktok_hashtags_default": '["#HairTransformation", "#SalonLife", "#HairTok", "#LondonHair", "#HairColour", "#HairTips", "#EastLondon", "#SalonTok"]',
            "content_pillars": '["transformation", "education", "process", "lifestyle"]',
            "posting_times_note": "12:00, 17:00, 19:30 GMT/BST",
        }
        for key, value in defaults.items():
            existing = db.query(Setting).filter(Setting.key == key).first()
            if not existing:
                db.add(Setting(key=key, value=value))
        db.commit()
    finally:
        db.close()
