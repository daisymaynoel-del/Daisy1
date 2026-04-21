"""
AI Engine — uses Claude to generate content, analyse brand alignment,
suggest posts, and write strategy reports.
"""
import json
import logging
from typing import Optional, List, Dict, Any
import anthropic
from config import settings

logger = logging.getLogger(__name__)

BRAND_CONTEXT = """
You are the content strategist for EASTEND, a hair and beauty salon in East London.

BRAND PROFILE:
- Name: EASTEND Salon, East London
- Personality: Authentic, welcoming, vibrant
- Voice: "We" (first-person plural), casual, no swearing, wholesome humour
- Target audience: Men and women, 20-40, East London creative community
- Mission: Create community, grow demand, fully booked most days
- USP: We educate clients — they leave knowing how to maintain their look at home

CONTENT PILLARS (use this ratio):
1. Transformation (35%) — before/after reveals, dramatic results — BEST for viral reach and sales
2. Education (35%) — how-to maintenance, product demos, hair tips — BEST for saves and follows
3. Process (20%) — behind-the-scenes, technique shots, day in the life
4. Lifestyle (10%) — East London culture, team moments, community

TONE RULES:
- Casual but professional. No swearing.
- Wholesome humour — warm, never mean
- Always sounds human, never scripted or corporate
- CTA on every post: link in bio to book, or DM us

LEGAL REQUIREMENT:
- Any post featuring colour services MUST include patch test notice:
  "⚠️ Patch test required 48hrs before any colour service. DM us to arrange."

PLATFORM NUANCES:
- Instagram: slightly longer captions OK, emojis encouraged, mix of broad + niche hashtags
- TikTok: shorter captions, conversational, trending hooks, 3-5 hashtags max

WHAT NOT TO DO:
- Never reference competitor salons by name
- Never post political content
- Never make it look like a magazine — we're a real, bookable salon
- Never sound exclusionary — we're accessible and welcoming
"""


def _get_client() -> Optional[anthropic.Anthropic]:
    if not settings.anthropic_api_key:
        logger.warning("ANTHROPIC_API_KEY not set — AI features disabled")
        return None
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def generate_caption_and_hook(
    content_pillar: str,
    platform: str,
    asset_description: str,
    trending_audio: Optional[str] = None,
    viral_benchmark_notes: Optional[str] = None,
    custom_notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a caption, hook, and hashtag set for a post."""
    client = _get_client()
    if not client:
        return _fallback_caption(content_pillar, platform)

    prompt = f"""{BRAND_CONTEXT}

TASK: Write a complete social media post for EASTEND Salon.

POST DETAILS:
- Platform: {platform}
- Content pillar: {content_pillar}
- Asset description: {asset_description}
- Trending audio (if applicable): {trending_audio or "not specified"}
- Viral benchmark notes: {viral_benchmark_notes or "none"}
- Additional notes: {custom_notes or "none"}

Return a JSON object with exactly these fields:
{{
  "hook": "The first 3-5 words that appear as text overlay or opening line — must stop the scroll",
  "caption": "Full caption including hook, body, and CTA. Natural, warm, East London voice.",
  "hashtags": ["list", "of", "10-15", "hashtags", "for", "{platform}"],
  "audio_suggestion": "Name of a trending sound that would fit this content (or 'original audio')",
  "patch_test_required": true or false (true if content shows colour services),
  "predicted_performance": "low|medium|high",
  "confidence_score": 0-100,
  "pillar_fit_reason": "One sentence explaining why this content fits the pillar"
}}

Return ONLY valid JSON. No markdown, no explanation."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        return json.loads(raw)
    except Exception as e:
        logger.error(f"AI caption generation failed: {e}")
        return _fallback_caption(content_pillar, platform)


def generate_post_suggestions(
    recent_performance: List[Dict],
    top_patterns: List[Dict],
    active_trends: List[Dict],
    available_assets: List[Dict],
) -> List[Dict[str, Any]]:
    """Generate 5 next-post suggestions based on what's working."""
    client = _get_client()
    if not client:
        return _fallback_suggestions()

    prompt = f"""{BRAND_CONTEXT}

TASK: Suggest the next 5 posts for EASTEND Salon based on current data.

RECENT PERFORMANCE DATA (last 7 days):
{json.dumps(recent_performance, indent=2)}

TOP PERFORMING PATTERNS (what's working):
{json.dumps(top_patterns, indent=2)}

ACTIVE TRENDS (sounds, hashtags, formats):
{json.dumps(active_trends, indent=2)}

AVAILABLE CONTENT ASSETS:
{json.dumps(available_assets, indent=2)}

Return a JSON array of 5 suggestion objects:
[
  {{
    "rank": 1,
    "platform": "instagram" or "tiktok",
    "content_pillar": "transformation|education|process|lifestyle",
    "hook": "Compelling 3-5 word hook",
    "caption_preview": "First 100 chars of suggested caption",
    "suggested_audio": "Specific trending audio name",
    "reasoning": "2-3 sentences: why this post, why now, what makes it likely to perform",
    "predicted_views": estimated integer,
    "confidence": 0.0-1.0,
    "asset_id": asset id to use or null
  }}
]

Prioritise: transformation + education pillars (they drive growth and sales for this brand).
Return ONLY valid JSON array."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        return json.loads(raw)
    except Exception as e:
        logger.error(f"AI suggestions failed: {e}")
        return _fallback_suggestions()


def generate_weekly_report(
    week_data: Dict[str, Any],
    patterns: List[Dict],
    top_posts: List[Dict],
    worst_posts: List[Dict],
) -> Dict[str, Any]:
    """Generate a written weekly strategy report."""
    client = _get_client()
    if not client:
        return {"report": "AI unavailable — please configure ANTHROPIC_API_KEY.", "wins": [], "losses": [], "direction": ""}

    prompt = f"""{BRAND_CONTEXT}

TASK: Write a weekly strategy report for EASTEND Salon.

WEEK DATA:
{json.dumps(week_data, indent=2)}

TOP PERFORMING PATTERNS THIS WEEK:
{json.dumps(patterns, indent=2)}

TOP 3 POSTS:
{json.dumps(top_posts, indent=2)}

WORST 3 POSTS:
{json.dumps(worst_posts, indent=2)}

Write a professional but readable report. Return JSON:
{{
  "report_markdown": "Full markdown report with sections: ## This Week's Results, ## What Worked, ## What Didn't, ## Next Week's Strategy",
  "wins": ["win 1", "win 2", "win 3"],
  "losses": ["loss 1", "loss 2"],
  "next_week_direction": "2-3 sentence direction for next week",
  "revenue_insight": "Any observations linking content performance to potential booking impact"
}}

Tone: Direct, honest, actionable. Focus on what drives bookings.
Return ONLY valid JSON."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        return json.loads(raw)
    except Exception as e:
        logger.error(f"AI weekly report failed: {e}")
        return {"report_markdown": f"Report generation failed: {e}", "wins": [], "losses": [], "next_week_direction": "", "revenue_insight": ""}


def analyse_asset(asset_description: str, asset_type: str) -> Dict[str, Any]:
    """Analyse an uploaded asset for brand fit and suggest content pillar."""
    client = _get_client()
    if not client:
        return {"brand_alignment": 75, "suggested_pillar": "transformation", "notes": "AI unavailable"}

    prompt = f"""{BRAND_CONTEXT}

TASK: Analyse this content asset for EASTEND Salon brand fit.

Asset type: {asset_type}
Description: {asset_description}

Return JSON:
{{
  "brand_alignment_score": 0-100,
  "suggested_pillar": "transformation|education|process|lifestyle",
  "colour_service_detected": true or false,
  "strengths": ["what's strong about this asset"],
  "suggestions": ["how to maximise it"],
  "hook_ideas": ["3 hook options for this asset"]
}}

Return ONLY valid JSON."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        return json.loads(raw)
    except Exception as e:
        logger.error(f"AI asset analysis failed: {e}")
        return {"brand_alignment_score": 70, "suggested_pillar": "transformation", "colour_service_detected": False, "strengths": [], "suggestions": [], "hook_ideas": []}


def predict_performance(post_data: Dict[str, Any], historical_avg: Dict[str, float]) -> Dict[str, Any]:
    """Predict whether a post will under/over-perform vs rolling average."""
    client = _get_client()
    if not client:
        return {"predicted_views": int(historical_avg.get("avg_views", 1000)), "performance_vs_average": 1.0, "flag_for_review": False, "reason": ""}

    prompt = f"""{BRAND_CONTEXT}

TASK: Predict performance of this upcoming post vs. EASTEND's rolling average.

POST DATA:
{json.dumps(post_data, indent=2)}

EASTEND ROLLING AVERAGES (last 30 days):
{json.dumps(historical_avg, indent=2)}

Return JSON:
{{
  "predicted_views": integer,
  "performance_multiplier": float (e.g. 1.5 = 50% above average, 0.4 = 60% below),
  "flag_for_review": true if multiplier < 0.5,
  "confidence": 0.0-1.0,
  "key_factors": ["main reasons for prediction"]
}}

Return ONLY valid JSON."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        return json.loads(raw)
    except Exception as e:
        logger.error(f"AI performance prediction failed: {e}")
        return {"predicted_views": int(historical_avg.get("avg_views", 500)), "performance_multiplier": 1.0, "flag_for_review": False, "confidence": 0.5, "key_factors": []}


# ── Fallbacks (when AI is unavailable) ───────────────────────────────────────

def _fallback_caption(pillar: str, platform: str) -> Dict[str, Any]:
    captions = {
        "transformation": {
            "hook": "Before → After ✨",
            "caption": "Another transformation complete at EASTEND 💫\n\nYour hair, your way — that's what we're about. Come through and let us show you what's possible.\n\nBook in via the link in bio.\n\n#EastEndSalon #HairTransformation #LondonHair",
            "hashtags": ["#EastEndSalon", "#HairTransformation", "#LondonHair", "#EastLondon", "#HairColour", "#SalonLife"],
            "audio_suggestion": "Trending viral sound",
            "patch_test_required": True,
            "predicted_performance": "high",
            "confidence_score": 70,
            "pillar_fit_reason": "Transformation content drives the most reach and booking conversions.",
        },
        "education": {
            "hook": "You're doing this wrong 👀",
            "caption": "Real talk — most people are damaging their hair without knowing it. Here's what we teach every client at EASTEND:\n\n✅ Do this instead\n\nSave this post and thank us later. Questions? Drop them below 👇\n\n#HairEducation #HairTips #EastEndSalon",
            "hashtags": ["#HairEducation", "#HairTips", "#EastEndSalon", "#HairCare", "#LondonHair"],
            "audio_suggestion": "Trending educational sound",
            "patch_test_required": False,
            "predicted_performance": "medium",
            "confidence_score": 65,
            "pillar_fit_reason": "Education content drives saves and follows.",
        },
    }
    return captions.get(pillar, captions["transformation"])


def _fallback_suggestions() -> List[Dict[str, Any]]:
    return [
        {
            "rank": 1,
            "platform": "instagram",
            "content_pillar": "transformation",
            "hook": "Before → After ✨",
            "caption_preview": "Another transformation complete at EASTEND...",
            "suggested_audio": "Trending viral sound",
            "reasoning": "Transformation content consistently drives the most reach and directly leads to bookings. Post during peak hours (17:00-19:00) for maximum impact.",
            "predicted_views": 5000,
            "confidence": 0.75,
            "asset_id": None,
        },
        {
            "rank": 2,
            "platform": "tiktok",
            "content_pillar": "education",
            "hook": "Stop doing this to your hair",
            "caption_preview": "Here's what we teach every client at EASTEND...",
            "suggested_audio": "Trending educational audio",
            "reasoning": "Education content on TikTok drives high save rates and follower growth. Hair tips with clear value get reshared.",
            "predicted_views": 8000,
            "confidence": 0.70,
            "asset_id": None,
        },
    ]
