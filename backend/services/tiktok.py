"""
TikTok posting via Make.com webhook.

Flow:
  Our agent  →  POST to Make.com webhook  →  Make.com scenario  →  TikTok

The Make.com scenario receives a JSON payload and uses the
TikTok module to publish the video.
"""
import logging
import random
import string
from typing import Optional, Dict, Any
import httpx
from config import settings

logger = logging.getLogger(__name__)


def _get_webhook_url() -> str:
    """Read webhook URL from DB first, fall back to env/config."""
    try:
        from database import SessionLocal
        from models import Setting
        db = SessionLocal()
        try:
            row = db.query(Setting).filter(Setting.key == "make_tiktok_webhook_url").first()
            if row and row.value:
                return row.value
        finally:
            db.close()
    except Exception:
        pass
    return settings.make_tiktok_webhook_url


def _is_demo_mode() -> bool:
    try:
        from database import SessionLocal
        from models import Setting
        db = SessionLocal()
        try:
            row = db.query(Setting).filter(Setting.key == "demo_mode").first()
            if row:
                return row.value.lower() == "true"
        finally:
            db.close()
    except Exception:
        pass
    return settings.demo_mode


class TikTokService:

    async def publish_video(
        self,
        video_url: str,
        caption: str,
        cover_url: Optional[str] = None,
        audio_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send post data to the Make.com TikTok webhook.
        Make.com handles the actual upload and publishing.
        """
        webhook_url = _get_webhook_url()
        demo = _is_demo_mode()

        if demo or not webhook_url:
            logger.info("TikTok: demo mode — simulating publish")
            return self._demo_response()

        payload = {
            "platform": "tiktok",
            "video_url": video_url,
            "caption": caption,
            "audio_name": audio_name or "",
        }
        if cover_url:
            payload["cover_url"] = cover_url

        async with httpx.AsyncClient() as client:
            resp = await client.post(webhook_url, json=payload, timeout=60)
            resp.raise_for_status()

        try:
            data = resp.json()
            post_id = data.get("post_id") or data.get("id") or self._fake_id()
            share_url = data.get("share_url") or data.get("url") or ""
        except Exception:
            post_id = self._fake_id()
            share_url = ""

        logger.info(f"TikTok video published via Make.com: {post_id}")
        return {"post_id": post_id, "share_url": share_url}

    async def get_video_metrics(self, video_id: str) -> Dict[str, Any]:
        """Return demo metrics — real metrics can be added via a Make.com fetch scenario."""
        return self._demo_insights()

    def _demo_response(self) -> Dict[str, Any]:
        fake_id = "".join(random.choices(string.digits, k=19))
        return {
            "post_id": "tiktok_" + fake_id,
            "share_url": f"https://www.tiktok.com/@eastend/video/{fake_id}",
            "demo": True,
        }

    def _demo_insights(self) -> Dict[str, Any]:
        base = random.randint(1000, 50000)
        return {
            "views": base,
            "likes": int(base * random.uniform(0.05, 0.20)),
            "comments": int(base * random.uniform(0.01, 0.05)),
            "shares": int(base * random.uniform(0.02, 0.08)),
            "saves": int(base * random.uniform(0.01, 0.05)),
            "reach": int(base * 0.9),
            "impressions": base,
            "engagement_rate": round(random.uniform(4.0, 18.0), 2),
            "avg_watch_time": round(random.uniform(3.0, 15.0), 1),
            "demo": True,
        }

    def _fake_id(self) -> str:
        return "tiktok_" + "".join(random.choices(string.digits, k=19))


tiktok_service = TikTokService()
