from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # App
    app_env: str = "development"
    secret_key: str = "dev-secret-change-me"
    allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    # Instagram
    instagram_app_id: str = ""
    instagram_app_secret: str = ""
    instagram_access_token: str = ""
    instagram_business_account_id: str = ""
    facebook_page_id: str = ""

    # TikTok
    tiktok_client_key: str = ""
    tiktok_client_secret: str = ""
    tiktok_access_token: str = ""
    tiktok_open_id: str = ""

    # Anthropic
    anthropic_api_key: str = ""

    # Database
    database_url: str = "sqlite:///./eastend.db"

    # File storage
    upload_dir: str = "uploads"
    thumbnail_dir: str = "thumbnails"
    max_upload_size_mb: int = 500

    # Scheduling
    post_times_instagram: str = "12:00,17:00,19:30"
    post_times_tiktok: str = "12:00,17:00,19:30"
    timezone: str = "Europe/London"

    # Agent behaviour
    approval_required: bool = True
    underperform_threshold: float = 0.5
    metrics_collection_intervals: str = "1h,6h,24h,72h,7d"

    # Demo mode
    demo_mode: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = False

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


settings = Settings()

# Ensure directories exist
for d in [settings.upload_dir, settings.thumbnail_dir, "reports", "data"]:
    os.makedirs(d, exist_ok=True)
