import os
import uuid
import json
import shutil
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from database import get_db
from models import ContentAsset
from schemas import ContentAssetOut
from services.content import process_uploaded_asset
from config import settings

router = APIRouter(prefix="/assets", tags=["assets"])

ALLOWED_VIDEO_TYPES = {"video/mp4", "video/quicktime", "video/mov", "video/mpeg", "video/webm"}
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic"}


@router.post("/upload", response_model=ContentAssetOut, status_code=status.HTTP_201_CREATED)
async def upload_asset(
    file: UploadFile = File(...),
    tags: str = Form(default="[]"),
    notes: Optional[str] = Form(default=None),
    db: Session = Depends(get_db),
):
    """Upload a video or image asset for content production."""
    content_type = file.content_type or ""

    if content_type in ALLOWED_VIDEO_TYPES or file.filename.lower().endswith((".mp4", ".mov", ".mpeg", ".webm")):
        asset_type = "video"
    elif content_type in ALLOWED_IMAGE_TYPES or file.filename.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".heic")):
        asset_type = "image"
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {content_type}. Allowed: MP4, MOV, JPEG, PNG, WEBP"
        )

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    os.makedirs(settings.upload_dir, exist_ok=True)

    safe_name = f"{uuid.uuid4().hex}_{os.path.basename(file.filename)}"
    dest_path = os.path.join(settings.upload_dir, safe_name)

    total_size = 0
    with open(dest_path, "wb") as out_file:
        while chunk := await file.read(1024 * 1024):
            total_size += len(chunk)
            if total_size > max_bytes:
                out_file.close()
                os.remove(dest_path)
                raise HTTPException(status_code=413, detail=f"File too large. Max: {settings.max_upload_size_mb}MB")
            out_file.write(chunk)

    try:
        parsed_tags = json.loads(tags) if tags else []
    except Exception:
        parsed_tags = []

    asset = await process_uploaded_asset(
        db=db,
        file_path=dest_path,
        original_filename=file.filename,
        asset_type=asset_type,
        tags=parsed_tags,
        notes=notes,
    )

    return _asset_to_schema(asset)


@router.get("/", response_model=List[ContentAssetOut])
def list_assets(
    skip: int = 0,
    limit: int = 50,
    asset_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(ContentAsset)
    if asset_type:
        query = query.filter(ContentAsset.asset_type == asset_type)
    assets = query.order_by(ContentAsset.created_at.desc()).offset(skip).limit(limit).all()
    return [_asset_to_schema(a) for a in assets]


@router.get("/{asset_id}", response_model=ContentAssetOut)
def get_asset(asset_id: int, db: Session = Depends(get_db)):
    asset = db.query(ContentAsset).filter(ContentAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return _asset_to_schema(asset)


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(asset_id: int, db: Session = Depends(get_db)):
    asset = db.query(ContentAsset).filter(ContentAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    if asset.file_path and os.path.exists(asset.file_path):
        os.remove(asset.file_path)
    if asset.thumbnail_path and os.path.exists(asset.thumbnail_path):
        os.remove(asset.thumbnail_path)
    db.delete(asset)
    db.commit()


@router.get("/{asset_id}/thumbnail")
def get_thumbnail(asset_id: int, db: Session = Depends(get_db)):
    asset = db.query(ContentAsset).filter(ContentAsset.id == asset_id).first()
    if not asset or not asset.thumbnail_path or not os.path.exists(asset.thumbnail_path):
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    return FileResponse(asset.thumbnail_path, media_type="image/jpeg")


def _asset_to_schema(asset: ContentAsset) -> ContentAssetOut:
    tags = json.loads(asset.tags) if asset.tags else []
    ai_analysis = json.loads(asset.ai_analysis) if asset.ai_analysis else None
    return ContentAssetOut(
        id=asset.id,
        filename=asset.filename,
        original_filename=asset.original_filename,
        file_path=asset.file_path,
        thumbnail_path=asset.thumbnail_path,
        asset_type=asset.asset_type,
        duration_seconds=asset.duration_seconds,
        file_size_bytes=asset.file_size_bytes,
        width=asset.width,
        height=asset.height,
        tags=tags,
        notes=asset.notes,
        ai_analysis=ai_analysis,
        created_at=asset.created_at,
    )
