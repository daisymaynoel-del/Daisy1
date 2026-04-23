"""
Instagram posting via Make.com webhook.

Flow:
  Our agent  →  POST to Make.com webhook  →  Make.com scenario  →  Instagram

The Make.com scenario receives a JSON payload and uses the
Instagram module to publish the Reel.
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
            row = db.query(Setting).filter(Setting.key == "make_instagram_webhook_url").first()
            if row and row.value:
                return row.value
        finally:
            db.close()
    except Exception:
        pass
    return settings.make_instagram_webhook_url


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


class InstagramService:

    async def publish_reel(
        self,
        video_url: str,
        caption: str,
        cover_url: Optional[str] = None,
        audio_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send post data to the Make.com Instagram webhook.
        Make.com handles the actual upload and publishing.
        """
        webhook_url = _get_webhook_url()
        demo = _is_demo_mode()

        if demo or not webhook_url:
            logger.info("Instagram: demo mode — simulating publish")
            return self._demo_response()

        payload = {
            "platform": "instagram",
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
            permalink = data.get("permalink") or data.get("url") or ""
        except Exception:
            post_id = self._fake_id()
            permalink = ""

        logger.info(f"Instagram Reel published via Make.com: {post_id}")
        return {"post_id": post_id, "permalink": permalink}

    async def get_post_insights(self, post_id: str) -> Dict[str, Any]:
        """Return demo metrics — real metrics can be added via a Make.com fetch scenario."""
        return self._demo_insights()

    async def get_account_follower_count(self) -> int:
        return 0

    def _demo_response(self) -> Dict[str, Any]:
        return {
            "post_id": self._fake_id(),
            "permalink": f"https://instagram.com/p/{''.join(random.choices(string.ascii_letters, k=11))}",
            "demo": True,
        }

    def _demo_insights(self) -> Dict[str, Any]:
        base = random.randint(800, 15000)
        return {
            "views": base,
            "likes": int(base * random.uniform(0.05, 0.15)),
            "comments": int(base * random.uniform(0.01, 0.04)),
            "shares": int(base * random.uniform(0.01, 0.05)),
            "saves": int(base * random.uniform(0.02, 0.08)),
            "reach": int(base * 0.85),
            "impressions": base,
            "engagement_rate": round(random.uniform(3.5, 12.0), 2),
            "demo": True,
        }

    def _fake_id(self) -> str:
        return "".join(random.choices(string.digits, k=17))


instagram_service = InstagramService()
