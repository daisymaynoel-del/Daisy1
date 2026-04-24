"""
Real-time trend data from three live sources:

1. Google Trends (pytrends) — UK hair/beauty search trends, no API key needed
2. Spotify UK charts (spotipy) — trending audio, optional (needs free Spotify Dev account)
3. Claude AI — contextualises all live data into specific EASTEND content recommendations

Runs every 6 hours via the scheduler.
"""
import logging
import json
import asyncio
from datetime import date
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from models import Trend, Platform, TrendType
from config import settings

logger = logging.getLogger(__name__)

HAIR_KEYWORDS = [
    "hair transformation", "balayage hair", "hair colour",
    "blonde highlights", "hair trends", "colour correction hair",
]

TYPE_MAP = {
    "hashtag": TrendType.hashtag,
    "sound": TrendType.sound,
    "hook": TrendType.hook,
    "format": TrendType.format,
}


# ── Google Trends ─────────────────────────────────────────────────────────────

async def _fetch_google_trends() -> List[Dict]:
    """
    Pull UK hair/beauty rising search terms via pytrends.
    Free — no API key required.
    """
    try:
        from pytrends.request import TrendReq
    except ImportError:
        logger.warning("pytrends not installed — skipping Google Trends")
        return []

    try:
        pytrends = TrendReq(hl="en-GB", tz=0, timeout=(10, 25), retries=2, backoff_factor=0.5)
        pytrends.build_payload(HAIR_KEYWORDS[:5], timeframe="now 7-d", geo="GB")

        related = pytrends.related_queries()
        results = []

        for kw in HAIR_KEYWORDS[:5]:
            rising = related.get(kw, {}).get("rising")
            if rising is None or rising.empty:
                continue
            for _, row in rising.head(6).iterrows():
                query = str(row.get("query", "")).strip()
                value = int(row.get("value", 0))
                if not query:
                    continue
                hashtag = "#" + query.title().replace(" ", "")
                results.append({
                    "type": "hashtag",
                    "value": hashtag,
                    "platform": "both",
                    "growth_rate": min(value / 100, 5.0),
                    "relevance_score": min(0.5 + value / 2000, 0.95),
                    "use_count": value * 1000,
                    "saturation_level": "low" if value > 200 else "medium",
                })

        # Also check real-time UK trending
        try:
            trending = pytrends.trending_searches(pn="united_kingdom")
            if trending is not None and not trending.empty:
                beauty_terms = ["hair", "beauty", "salon", "colour", "skin", "nail", "style"]
                for term in trending[0].head(20).tolist():
                    if any(k in str(term).lower() for k in beauty_terms):
                        results.append({
                            "type": "hashtag",
                            "value": "#" + str(term).title().replace(" ", ""),
                            "platform": "both",
                            "growth_rate": 2.0,
                            "relevance_score": 0.82,
                            "use_count": 800000,
                            "saturation_level": "low",
                        })
        except Exception:
            pass

        logger.info(f"Google Trends: {len(results)} trends fetched")
        return results

    except Exception as e:
        logger.error(f"Google Trends error: {e}")
        return []


# ── Spotify ───────────────────────────────────────────────────────────────────

async def _fetch_spotify_charts() -> List[Dict]:
    """
    Pull UK Top 50 + Viral 50 from Spotify.
    Optional — only runs when spotify_client_id / spotify_client_secret are set.
    """
    if not (settings.spotify_client_id and settings.spotify_client_secret):
        return []

    try:
        import spotipy
        from spotipy.oauth2 import SpotifyClientCredentials
    except ImportError:
        logger.warning("spotipy not installed — skipping Spotify")
        return []

    try:
        sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=settings.spotify_client_id,
            client_secret=settings.spotify_client_secret,
        ))

        # Spotify official chart playlists (UK)
        playlists = [
            ("37i9dQZEVXbLnolsZ2PSNw", "UK Top 50"),
            ("37i9dQZEVXbIQnj7RRhdSX", "UK Viral 50"),
            ("37i9dQZF1DXcBWIGoYBM5M", "Hot Hits UK"),
        ]

        sounds = []
        for playlist_id, _ in playlists:
            try:
                items = sp.playlist_tracks(playlist_id, limit=25).get("items", [])
                for i, item in enumerate(items):
                    track = item.get("track")
                    if not track:
                        continue
                    name = track.get("name", "")
                    artists = ", ".join(a["name"] for a in track.get("artists", [])[:2])
                    popularity = track.get("popularity", 50)
                    sounds.append({
                        "type": "sound",
                        "value": f"{name} — {artists}",
                        "platform": "both",
                        "growth_rate": round(popularity / 20, 2),
                        "relevance_score": round(popularity / 100, 2),
                        "use_count": popularity * 12000,
                        "saturation_level": "low" if i < 8 else ("medium" if i < 18 else "high"),
                        "trend_id": track.get("id"),
                    })
            except Exception as e:
                logger.warning(f"Spotify playlist {playlist_id}: {e}")

        logger.info(f"Spotify: {len(sounds)} trending tracks fetched")
        return sounds

    except Exception as e:
        logger.error(f"Spotify error: {e}")
        return []


# ── Claude AI analysis ────────────────────────────────────────────────────────

async def _generate_ai_trends(google_data: List[Dict], spotify_data: List[Dict]) -> List[Dict]:
    """
    Ask Claude to generate specific EASTEND trend recommendations,
    grounded in the live Google + Spotify data.
    """
    if not settings.anthropic_api_key:
        return []

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        today_str = date.today().strftime("%B %Y")

        google_summary = json.dumps([t["value"] for t in google_data[:12]]) if google_data else "[]"
        spotify_summary = json.dumps([t["value"] for t in spotify_data[:12]]) if spotify_data else "[]"

        prompt = f"""You are a social media trend analyst for EASTEND Salon, East London.
Date: {today_str}

LIVE UK GOOGLE TRENDS right now (hair/beauty searches):
{google_summary}

LIVE SPOTIFY UK CHARTS right now:
{spotify_summary}

EASTEND makes content about: hair transformations, colour services (balayage, highlights, colour correction), haircuts, education, East London salon lifestyle.
Audience: East London creatives, 20–40. Platforms: Instagram Reels + TikTok.

Using this LIVE data as your context, generate exactly 18 specific trend recommendations for EASTEND right now.
Include: 7 hashtags, 6 audio/sounds (use the Spotify tracks above where relevant), 5 hook formats.

Return ONLY a valid JSON array:
[
  {{"type":"hashtag","value":"#ExactHashtag","platform":"instagram","relevance_score":0.88,"growth_rate":0.4,"saturation_level":"low","why":"one-line reason"}},
  {{"type":"sound","value":"Track Name — Artist","platform":"both","relevance_score":0.92,"growth_rate":0.6,"saturation_level":"low","why":"why this audio works for hair content"}},
  {{"type":"hook","value":"Exact hook text that stops the scroll","platform":"both","relevance_score":0.85,"growth_rate":0.3,"saturation_level":"low","why":"psychological hook reason"}}
]

Be specific. Use real Spotify tracks from the list above. Reference actual current hashtag communities."""

        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()
        start, end = text.find("["), text.rfind("]") + 1
        if start >= 0 and end > start:
            data = json.loads(text[start:end])
            logger.info(f"Claude AI: {len(data)} trend insights generated")
            return data

    except Exception as e:
        logger.error(f"AI trend analysis error: {e}")

    return []


# ── Main entry point ─────────────────────────────────────────────────────────

async def fetch_and_store_realtime_trends(db: Session) -> Dict[str, int]:
    """
    Pull from all sources, deduplicate, and upsert into the Trend table.
    Called by the scheduler every 6 hours.
    """
    today = date.today()
    counts = {"google": 0, "spotify": 0, "ai": 0, "stored": 0}

    google_data, spotify_data = await asyncio.gather(
        _fetch_google_trends(),
        _fetch_spotify_charts(),
    )
    ai_data = await _generate_ai_trends(google_data, spotify_data)

    counts["google"] = len(google_data)
    counts["spotify"] = len(spotify_data)
    counts["ai"] = len(ai_data)

    all_raw = google_data + spotify_data + ai_data

    for t in all_raw:
        value = str(t.get("value", "")).strip()
        if not value:
            continue

        trend_type = TYPE_MAP.get(t.get("type", "hashtag"), TrendType.hashtag)
        platforms = (
            [Platform.instagram, Platform.tiktok]
            if t.get("platform", "both") == "both"
            else [Platform(t["platform"])]
        )

        for platform in platforms:
            existing = (
                db.query(Trend)
                .filter(
                    Trend.trend_value == value,
                    Trend.platform == platform,
                    Trend.discovery_date == today,
                )
                .first()
            )
            if existing:
                existing.relevance_score = float(t.get("relevance_score", existing.relevance_score))
                existing.growth_rate = float(t.get("growth_rate", existing.growth_rate))
                existing.use_count = int(t.get("use_count", existing.use_count))
            else:
                db.add(Trend(
                    platform=platform,
                    trend_type=trend_type,
                    trend_value=value,
                    trend_id=t.get("trend_id"),
                    discovery_date=today,
                    saturation_level=t.get("saturation_level", "low"),
                    relevance_score=float(t.get("relevance_score", 0.7)),
                    use_count=int(t.get("use_count", 50000)),
                    growth_rate=float(t.get("growth_rate", 0.2)),
                    is_active=True,
                ))
                counts["stored"] += 1

    db.commit()
    logger.info(f"Real-time trends stored: {counts}")
    return counts
