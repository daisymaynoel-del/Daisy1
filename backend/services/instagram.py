"""
Instagram Graph API service.
Handles publishing Reels and collecting post insights.
"""
import logging
import json
from typing import Optional, Dict, Any
import httpx
from config import settings

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.facebook.com/v20.0"


class InstagramService:
    def __init__(self):
        self.access_token = settings.instagram_access_token
        self.account_id = settings.instagram_business_account_id
        self.demo_mode = settings.demo_mode

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}

    async def publish_reel(
        self,
        video_url: str,
        caption: str,
        cover_url: Optional[str] = None,
        audio_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Publish a Reel via Instagram Graph API (two-step: create container → publish).
        Returns {"post_id": str, "permalink": str} on success.
        """
        if self.demo_mode or not self.access_token:
            return self._demo_publish_response("instagram_reel")

        async with httpx.AsyncClient() as client:
            # Step 1: Create media container
            container_payload = {
                "media_type": "REELS",
                "video_url": video_url,
                "caption": caption,
                "access_token": self.access_token,
            }
            if cover_url:
                container_payload["cover_url"] = cover_url

            resp = await client.post(
                f"{GRAPH_BASE}/{self.account_id}/media",
                data=container_payload,
                timeout=60,
            )
            resp.raise_for_status()
            container_id = resp.json()["id"]
            logger.info(f"Instagram container created: {container_id}")

            # Step 2: Wait for processing then publish
            await self._wait_for_container(client, container_id)

            pub_resp = await client.post(
                f"{GRAPH_BASE}/{self.account_id}/media_publish",
                data={"creation_id": container_id, "access_token": self.access_token},
                timeout=30,
            )
            pub_resp.raise_for_status()
            post_id = pub_resp.json()["id"]

            # Get permalink
            permalink = await self._get_permalink(client, post_id)
            logger.info(f"Instagram Reel published: {post_id}")
            return {"post_id": post_id, "permalink": permalink}

    async def _wait_for_container(self, client: httpx.AsyncClient, container_id: str, max_wait: int = 120):
        """Poll container status until FINISHED."""
        import asyncio
        for _ in range(max_wait // 5):
            resp = await client.get(
                f"{GRAPH_BASE}/{container_id}",
                params={"fields": "status_code,status", "access_token": self.access_token},
            )
            data = resp.json()
            status = data.get("status_code", "")
            if status == "FINISHED":
                return
            if status == "ERROR":
                raise RuntimeError(f"Instagram container processing failed: {data.get('status')}")
            await asyncio.sleep(5)
        raise TimeoutError("Instagram container processing timed out")

    async def _get_permalink(self, client: httpx.AsyncClient, post_id: str) -> str:
        resp = await client.get(
            f"{GRAPH_BASE}/{post_id}",
            params={"fields": "permalink", "access_token": self.access_token},
        )
        return resp.json().get("permalink", f"https://instagram.com/p/{post_id}")

    async def get_post_insights(self, post_id: str) -> Dict[str, Any]:
        """Fetch engagement metrics for a published post."""
        if self.demo_mode or not self.access_token:
            return self._demo_insights()

        metrics = ["impressions", "reach", "likes", "comments", "shares", "saved", "plays", "total_interactions"]
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{GRAPH_BASE}/{post_id}/insights",
                params={
                    "metric": ",".join(metrics),
                    "access_token": self.access_token,
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json().get("data", [])
            result = {}
            for item in data:
                result[item["name"]] = item.get("values", [{}])[-1].get("value", 0)

            # Normalise field names
            return {
                "views": result.get("plays", result.get("impressions", 0)),
                "likes": result.get("likes", 0),
                "comments": result.get("comments", 0),
                "shares": result.get("shares", 0),
                "saves": result.get("saved", 0),
                "reach": result.get("reach", 0),
                "impressions": result.get("impressions", 0),
                "engagement_rate": self._calc_engagement(result),
            }

    async def get_account_follower_count(self) -> int:
        """Get current follower count."""
        if self.demo_mode or not self.access_token:
            return 1250

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{GRAPH_BASE}/{self.account_id}",
                params={"fields": "followers_count", "access_token": self.access_token},
            )
            return resp.json().get("followers_count", 0)

    def _calc_engagement(self, data: Dict) -> float:
        total = data.get("likes", 0) + data.get("comments", 0) + data.get("shares", 0) + data.get("saved", 0)
        reach = data.get("reach", 1)
        return round((total / max(reach, 1)) * 100, 2)

    def _demo_publish_response(self, platform: str) -> Dict[str, Any]:
        import random, string
        fake_id = "".join(random.choices(string.digits, k=17))
        return {
            "post_id": fake_id,
            "permalink": f"https://instagram.com/p/{''.join(random.choices(string.ascii_letters, k=11))}",
            "demo": True,
        }

    def _demo_insights(self) -> Dict[str, Any]:
        import random
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


instagram_service = InstagramService()
