"""
Chat service — conversational interface with the agent.
The owner can give instructions, ask questions, and update creative briefs
through natural dialogue. Claude maintains context and updates the system accordingly.
"""
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import anthropic
from config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the creative director and social media agent for EASTEND Salon, East London.
You are having a conversation with Daisy, the salon owner.

YOUR ROLE:
- Help Daisy create and plan social media content for Instagram and TikTok
- Take her instructions and translate them into precise content briefs
- Answer questions about performance, trends, and strategy
- Suggest ideas based on what's working for the brand

EASTEND BRAND:
- East London hair and beauty salon — authentic, welcoming, vibrant
- Voice: casual "we", wholesome humour, no swearing
- Content pillars: Transformation (35%), Education (35%), Process (20%), Lifestyle (10%)
- Target: Men and women 20-40, East London creative community
- Goal: Drive bookings — every post should feel like it could lead to someone booking
- LEGAL: Any colour service content MUST include patch test notice (48hr before colour)

WHEN DAISY GIVES CONTENT INSTRUCTIONS:
Extract and confirm these details in your response:
1. Hook (opening line or text overlay)
2. Video length (seconds)
3. Music/audio preference
4. Content pillar it fits
5. Any special instructions

WHEN UPDATING THE CREATIVE BRIEF:
If Daisy wants to change how future content is made, confirm what you've understood
and tell her the brief has been updated.

TONE: Warm, direct, like a skilled creative collaborator. Not corporate. Keep responses concise.
Always end with a clear next step or confirmation of what you'll do."""


def get_client() -> Optional[anthropic.Anthropic]:
    if not settings.anthropic_api_key:
        return None
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


async def chat_with_agent(
    user_message: str,
    history: List[Dict[str, str]],
    current_brief: Optional[Dict] = None,
    performance_context: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Send a message to the agent and get a response.
    Returns response text + any extracted brief updates.
    """
    client = get_client()
    if not client:
        return {
            "response": "AI is not configured yet. Please add your ANTHROPIC_API_KEY to the environment variables.",
            "brief_update": None,
        }

    # Build context for Claude
    context_parts = []
    if current_brief:
        context_parts.append(f"CURRENT CREATIVE BRIEF:\n{json.dumps(current_brief, indent=2)}")
    if performance_context:
        context_parts.append(f"RECENT PERFORMANCE:\n{json.dumps(performance_context, indent=2)}")

    system = SYSTEM_PROMPT
    if context_parts:
        system += "\n\nCONTEXT:\n" + "\n\n".join(context_parts)

    # Build message history
    messages = []
    for msg in history[-20:]:  # last 20 messages for context
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system,
            messages=messages,
        )
        response_text = response.content[0].text

        # Try to extract brief updates from the conversation
        brief_update = _extract_brief_update(user_message, response_text)

        return {
            "response": response_text,
            "brief_update": brief_update,
        }
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return {
            "response": f"Sorry, I hit an error: {str(e)}. Please try again.",
            "brief_update": None,
        }


async def generate_content_brief_from_instructions(
    instructions: str,
    asset_description: str,
    platform: str,
) -> Dict[str, Any]:
    """
    Given owner's specific instructions for a video, generate a full content brief.
    Used when uploading content with custom instructions.
    """
    client = get_client()
    if not client:
        return _fallback_brief(platform)

    prompt = f"""The EASTEND salon owner has given these instructions for a new video:

OWNER'S INSTRUCTIONS: {instructions}

ASSET: {asset_description}
PLATFORM: {platform}

Based on these instructions, create a complete content brief. Return JSON:
{{
  "hook": "exact opening hook text (first 3-5 words that stop the scroll)",
  "caption": "full caption in EASTEND voice with CTA",
  "hashtags": ["list", "of", "hashtags"],
  "audio_suggestion": "specific trending sound or music style they mentioned",
  "video_length_seconds": integer (from their instructions, or best guess),
  "content_pillar": "transformation|education|process|lifestyle",
  "patch_test_required": true or false,
  "text_overlays": ["any text that should appear on screen"],
  "cta": "call to action",
  "production_notes": "specific instructions for how to edit/create the video"
}}

Follow the owner's instructions precisely. Return ONLY valid JSON."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return json.loads(response.content[0].text.strip())
    except Exception as e:
        logger.error(f"Brief generation error: {e}")
        return _fallback_brief(platform)


def _extract_brief_update(user_message: str, response: str) -> Optional[Dict]:
    """Heuristically detect if the conversation updated the creative brief."""
    update_triggers = [
        "always", "from now on", "every video", "all videos", "make sure",
        "hook should", "music should", "use this", "length should", "seconds long",
        "i want", "change the", "update the"
    ]
    msg_lower = user_message.lower()
    if any(trigger in msg_lower for trigger in update_triggers):
        return {"detected": True, "raw_instruction": user_message}
    return None


def _fallback_brief(platform: str) -> Dict:
    return {
        "hook": "You need to see this transformation ✨",
        "caption": "Another day, another incredible transformation at EASTEND 💫\n\nBook in via the link in bio.\n\n#EastEndSalon #HairTransformation #LondonHair",
        "hashtags": ["#EastEndSalon", "#HairTransformation", "#LondonHair"],
        "audio_suggestion": "Trending viral sound",
        "video_length_seconds": 15,
        "content_pillar": "transformation",
        "patch_test_required": False,
        "text_overlays": [],
        "cta": "Book via link in bio",
        "production_notes": "Show the transformation process and reveal.",
    }
