"""
TikTok Content Posting API service.
Handles video uploads and metrics collection.
"""
import logging
import json
from typing import Optional, Dict, Any
import httpx
from config import settings

logger = logging.getLogger(__name__)

TIKTOK_BASE = "https://open.tiktokapis.com/v2"


class TikTokService:
    def __init__(self):
        self.client_key = settings.tiktok_client_key
        self.client_secret = settings.tiktok_client_secret
        self.access_token = settings.tiktok_access_token
        self.open_id = settings.tiktok_open_id
        self.demo_mode = settings.demo_mode

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }

    async def publish_video(
        self,
        video_path: str,
        title: str,
        description: str = "",
        privacy_level: str = "PUBLIC_TO_EVERYONE",
        disable_duet: bool = False,
        disable_comment: bool = False,
        disable_stitch: bool = False,
    ) -> Dict[str, Any]:
        """
        Publish a video to TikTok via the Content Posting API.
        Uses the FILE_UPLOAD method.
        Returns {"post_id": str, "share_url": str} on success.
        """
        if self.demo_mode or not self.access_token:
            return self._demo_publish_response()

        async with httpx.AsyncClient() as client:
            # Step 1: Initialise upload
            init_payload = {
                "post_info": {
                    "title": title[:150],
                    "description": description[:2200] if description else "",
                    "privacy_level": privacy_level,
                    "disable_duet": disable_duet,
                    "disable_comment": disable_comment,
                    "disable_stitch": disable_stitch,
                    "video_cover_timestamp_ms": 1000,
                },
                "source_info": {
                    "source": "FILE_UPLOAD",
                    "video_size": self._get_file_size(video_path),
                    "chunk_size": 10_000_000,
                    "total_chunk_count": 1,
                },
            }

            init_resp = await client.post(
                f"{TIKTOK_BASE}/post/publish/video/init/",
                headers=self._headers(),
                json=init_payload,
                timeout=30,
            )
            init_resp.raise_for_status()
            init_data = init_resp.json().get("data", {})
            publish_id = init_data.get("publish_id")
            upload_url = init_data.get("upload_url")

            if not upload_url:
                raise RuntimeError(f"TikTok init failed: {init_resp.text}")

            # Step 2: Upload video chunks
            await self._upload_video(client, video_path, upload_url)

            # Step 3: Poll for status
            result = await self._poll_publish_status(client, publish_id)
            logger.info(f"TikTok video published: {publish_id}")
            return result

    async def _upload_video(self, client: httpx.AsyncClient, video_path: str, upload_url: str):
        file_size = self._get_file_size(video_path)
        with open(video_path, "rb") as f:
            video_data = f.read()

        resp = await client.put(
            upload_url,
            content=video_data,
            headers={
                "Content-Type": "video/mp4",
                "Content-Range": f"bytes 0-{file_size - 1}/{file_size}",
                "Content-Length": str(file_size),
            },
            timeout=300,
        )
        resp.raise_for_status()

    async def _poll_publish_status(self, client: httpx.AsyncClient, publish_id: str, max_wait: int = 120) -> Dict[str, Any]:
        import asyncio
        for _ in range(max_wait // 5):
            resp = await client.post(
                f"{TIKTOK_BASE}/post/publish/status/fetch/",
                headers=self._headers(),
                json={"publish_id": publish_id},
                timeout=30,
            )
            data = resp.json().get("data", {})
            status = data.get("status", "")
            if status == "PUBLISH_COMPLETE":
                return {
                    "post_id": publish_id,
                    "share_url": data.get("publicaly_available_post_id", [None])[0],
                }
            if status in ("FAILED", "SPAM"):
                raise RuntimeError(f"TikTok publish failed: {data}")
            await asyncio.sleep(5)
        raise TimeoutError("TikTok publish timed out")

    async def get_video_metrics(self, video_id: str) -> Dict[str, Any]:
        """Fetch metrics for a published TikTok video."""
        if self.demo_mode or not self.access_token:
            return self._demo_insights()

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{TIKTOK_BASE}/video/query/",
                headers=self._headers(),
                params={"fields": "id,title,cover_image_url,share_url,view_count,like_count,comment_count,share_count,play_count,reach,average_time_watched"},
                json={"filters": {"video_ids": [video_id]}},
                timeout=30,
            )
            resp.raise_for_status()
            videos = resp.json().get("data", {}).get("videos", [])
            if not videos:
                return self._demo_insights()
            v = videos[0]
            total_eng = v.get("like_count", 0) + v.get("comment_count", 0) + v.get("share_count", 0)
            views = v.get("view_count", 1)
            return {
                "views": views,
                "likes": v.get("like_count", 0),
                "comments": v.get("comment_count", 0),
                "shares": v.get("share_count", 0),
                "saves": 0,
                "reach": v.get("reach", views),
                "impressions": views,
                "engagement_rate": round((total_eng / max(views, 1)) * 100, 2),
                "avg_watch_time": v.get("average_time_watched", 0),
            }

    def _get_file_size(self, path: str) -> int:
        import os
        return os.path.getsize(path)

    def _demo_publish_response(self) -> Dict[str, Any]:
        import random, string
        return {
            "post_id": "tiktok_" + "".join(random.choices(string.digits, k=19)),
            "share_url": "https://www.tiktok.com/@eastend/video/" + "".join(random.choices(string.digits, k=19)),
            "demo": True,
        }

    def _demo_insights(self) -> Dict[str, Any]:
        import random
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


tiktok_service = TikTokService()
