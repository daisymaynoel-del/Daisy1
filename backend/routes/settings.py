from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from models import Setting
from config import settings as app_settings
from datetime import datetime
import httpx

router = APIRouter(prefix="/settings", tags=["settings"])


# ── helpers ──────────────────────────────────────────────────────────────────

def _get_setting(db: Session, key: str, fallback: str = "") -> str:
    row = db.query(Setting).filter(Setting.key == key).first()
    return row.value if row else fallback


def _set_setting(db: Session, key: str, value: str):
    row = db.query(Setting).filter(Setting.key == key).first()
    if row:
        row.value = value
        row.updated_at = datetime.utcnow()
    else:
        db.add(Setting(key=key, value=value))


# ── existing routes ───────────────────────────────────────────────────────────

@router.get("/")
def get_settings(db: Session = Depends(get_db)):
    settings_rows = db.query(Setting).all()
    return {s.key: s.value for s in settings_rows}


@router.patch("/")
def update_settings(updates: Dict[str, Any], db: Session = Depends(get_db)):
    for key, value in updates.items():
        _set_setting(db, key, str(value))
    db.commit()
    return {"updated": list(updates.keys())}


@router.get("/brand-bible")
def get_brand_bible():
    import os
    bible_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "brand_bible.md")
    if os.path.exists(bible_path):
        with open(bible_path, "r") as f:
            return {"content": f.read()}
    return {"content": "Brand bible not found"}


# ── integrations ──────────────────────────────────────────────────────────────

class IntegrationsUpdate(BaseModel):
    instagram_webhook_url: Optional[str] = None
    tiktok_webhook_url: Optional[str] = None
    demo_mode: Optional[bool] = None


@router.get("/integrations")
def get_integrations(db: Session = Depends(get_db)):
    """Return current Make.com integration status."""
    ig_url = _get_setting(db, "make_instagram_webhook_url") or app_settings.make_instagram_webhook_url
    tt_url = _get_setting(db, "make_tiktok_webhook_url") or app_settings.make_tiktok_webhook_url
    demo_str = _get_setting(db, "demo_mode")
    demo = (demo_str.lower() == "true") if demo_str else app_settings.demo_mode

    return {
        "demo_mode": demo,
        "instagram": {
            "connected": bool(ig_url) and not demo,
            "webhook_url": ig_url,
            "webhook_url_masked": _mask_url(ig_url),
        },
        "tiktok": {
            "connected": bool(tt_url) and not demo,
            "webhook_url": tt_url,
            "webhook_url_masked": _mask_url(tt_url),
        },
    }


@router.patch("/integrations")
def update_integrations(body: IntegrationsUpdate, db: Session = Depends(get_db)):
    """Save Make.com webhook URLs and demo mode to the database."""
    if body.instagram_webhook_url is not None:
        _set_setting(db, "make_instagram_webhook_url", body.instagram_webhook_url)
    if body.tiktok_webhook_url is not None:
        _set_setting(db, "make_tiktok_webhook_url", body.tiktok_webhook_url)
    if body.demo_mode is not None:
        _set_setting(db, "demo_mode", str(body.demo_mode).lower())
    db.commit()
    return {"ok": True}


@router.post("/integrations/test")
async def test_integration(body: Dict[str, str], db: Session = Depends(get_db)):
    """Send a test ping to a Make.com webhook URL."""
    url = body.get("url", "").strip()
    if not url:
        return {"ok": False, "error": "No URL provided"}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json={"test": True, "source": "eastend_agent"}, timeout=10)
        return {"ok": True, "status_code": resp.status_code}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _mask_url(url: str) -> str:
    if not url:
        return ""
    if len(url) <= 20:
        return "••••••••"
    return url[:20] + "••••••••" + url[-6:]
