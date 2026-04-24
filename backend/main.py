import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from database import init_db
from services.scheduler import start_scheduler, stop_scheduler
from config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting EASTEND Social Media Agent")
    init_db()
    start_scheduler()

    # Fetch real-time trends on startup
    from database import SessionLocal
    from services.trends_realtime import fetch_and_store_realtime_trends
    db = SessionLocal()
    try:
        await fetch_and_store_realtime_trends(db)
    finally:
        db.close()

    yield

    stop_scheduler()
    logger.info("EASTEND Social Media Agent stopped")


app = FastAPI(
    title="EASTEND Social Media Growth Agent",
    description="Autonomous Instagram & TikTok growth agent for EASTEND Salon, East London",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving for uploads and thumbnails
os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs(settings.thumbnail_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")
app.mount("/thumbnails", StaticFiles(directory=settings.thumbnail_dir), name="thumbnails")

# Register all routes
from routes import assets, posts, metrics, trends, suggestions, reports, settings as settings_route, chat

app.include_router(assets.router, prefix="/api")
app.include_router(posts.router, prefix="/api")
app.include_router(metrics.router, prefix="/api")
app.include_router(trends.router, prefix="/api")
app.include_router(suggestions.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(settings_route.router, prefix="/api")
app.include_router(chat.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok", "demo_mode": settings.demo_mode}


# Serve built React frontend — must be mounted LAST so API routes take precedence
_frontend_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.exists(_frontend_dist):
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="frontend")
    logger.info(f"Serving frontend from {_frontend_dist}")
else:
    @app.get("/")
    def root():
        return {"service": "EASTEND Social Media Growth Agent", "status": "running", "docs": "/docs"}
