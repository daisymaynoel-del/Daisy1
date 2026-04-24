from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # App
    app_env: str = "development"
    secret_key: str = "dev-secret-change-me"
    allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    # ── Make.com Webhooks ─────────────────────────────────────────────────────
    # Set these in Railway Variables after creating your Make.com scenarios
    make_instagram_webhook_url: str = ""   # Webhook URL from your Instagram scenario
    make_tiktok_webhook_url: str = ""      # Webhook URL from your TikTok scenario

    # ── Cloudinary (video storage) ────────────────────────────────────────────
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""

    # ── Public base URL (used to build video URLs for Make.com) ───────────────
    public_base_url: str = "https://daisy1.onrender.com"

    # ── Spotify (optional — trending audio for Reels/TikTok) ─────────────────
    spotify_client_id: str = ""
    spotify_client_secret: str = ""

    # ── Anthropic (Claude AI) ─────────────────────────────────────────────────
    anthropic_api_key: str = ""

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = "sqlite:///./eastend.db"

    # ── File Storage ──────────────────────────────────────────────────────────
    upload_dir: str = "uploads"
    thumbnail_dir: str = "thumbnails"
    max_upload_size_mb: int = 500

    # ── Scheduling ────────────────────────────────────────────────────────────
    post_times_instagram: str = "12:00,17:00,19:30"
    post_times_tiktok: str = "12:00,17:00,19:30"
    timezone: str = "Europe/London"

    # ── Agent Behaviour ───────────────────────────────────────────────────────
    approval_required: bool = True
    underperform_threshold: float = 0.5
    metrics_collection_intervals: str = "1h,6h,24h,72h,7d"

    # ── Demo Mode ─────────────────────────────────────────────────────────────
    demo_mode: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"

    @property
    def origins_list(self) -> List[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    @property
    def instagram_post_times(self) -> List[str]:
        return [t.strip() for t in self.post_times_instagram.split(",")]

    @property
    def tiktok_post_times(self) -> List[str]:
        return [t.strip() for t in self.post_times_tiktok.split(",")]

    @property
    def metric_intervals(self) -> List[str]:
        return [i.strip() for i in self.metrics_collection_intervals.split(",")]

    @property
    def instagram_live(self) -> bool:
        return bool(self.make_instagram_webhook_url) and not self.demo_mode

    @property
    def tiktok_live(self) -> bool:
        return bool(self.make_tiktok_webhook_url) and not self.demo_mode


settings = Settings()

# Ensure directories exist
for d in [settings.upload_dir, settings.thumbnail_dir, "reports", "data"]:
    os.makedirs(d, exist_ok=True)
