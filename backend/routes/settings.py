from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import Setting
from datetime import datetime

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/")
def get_settings(db: Session = Depends(get_db)):
    settings_rows = db.query(Setting).all()
    return {s.key: s.value for s in settings_rows}


@router.patch("/")
def update_settings(updates: Dict[str, Any], db: Session = Depends(get_db)):
    """Update one or more settings keys."""
    for key, value in updates.items():
        existing = db.query(Setting).filter(Setting.key == key).first()
        if existing:
            existing.value = str(value)
            existing.updated_at = datetime.utcnow()
        else:
            db.add(Setting(key=key, value=str(value)))
    db.commit()
    return {"updated": list(updates.keys())}


@router.get("/brand-bible")
def get_brand_bible():
    """Return the brand bible markdown content."""
    import os
    bible_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "brand_bible.md")
    if os.path.exists(bible_path):
        with open(bible_path, "r") as f:
            return {"content": f.read()}
    return {"content": "Brand bible not found"}
