"""
Cloudinary storage — uploads processed videos and returns permanent public URLs
so Make.com can download them when posting to Instagram/TikTok.
"""
import logging
import os
import cloudinary
import cloudinary.uploader
from config import settings

logger = logging.getLogger(__name__)


def _configure():
    cloudinary.config(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        secure=True,
    )


def is_configured() -> bool:
    return bool(
        settings.cloudinary_cloud_name
        and settings.cloudinary_api_key
        and settings.cloudinary_api_secret
    )


def upload_video(file_path: str, folder: str = "eastend") -> str:
    """
    Upload a video file to Cloudinary.
    Returns the secure public URL Make.com will use to download it.
    Falls back to the Render public URL if Cloudinary is not configured.
    """
    if not is_configured():
        return _local_public_url(file_path)

    _configure()
    try:
        result = cloudinary.uploader.upload(
            file_path,
            resource_type="video",
            folder=folder,
            overwrite=True,
            use_filename=True,
        )
        url = result["secure_url"]
        logger.info(f"Uploaded to Cloudinary: {url}")
        return url
    except Exception as e:
        logger.error(f"Cloudinary upload failed, falling back to local URL: {e}")
        return _local_public_url(file_path)


def upload_image(file_path: str, folder: str = "eastend") -> str:
    """Upload a thumbnail/cover image to Cloudinary."""
    if not is_configured():
        return _local_public_url(file_path, subdir="thumbnails")

    _configure()
    try:
        result = cloudinary.uploader.upload(
            file_path,
            resource_type="image",
            folder=folder,
            overwrite=True,
        )
        return result["secure_url"]
    except Exception as e:
        logger.error(f"Cloudinary image upload failed: {e}")
        return _local_public_url(file_path, subdir="thumbnails")


def _local_public_url(file_path: str, subdir: str = "uploads") -> str:
    """Build a public URL using the app's base URL (Render domain)."""
    filename = os.path.basename(file_path) if file_path else ""
    base = settings.public_base_url.rstrip("/")
    return f"{base}/{subdir}/{filename}" if filename else ""
