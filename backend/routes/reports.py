import json
from typing import List, Optional
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from database import get_db
from models import StrategyReport
from schemas import StrategyReportOut
from services.reports import generate_weekly_strategy_report

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/", response_model=List[StrategyReportOut])
def list_reports(limit: int = 10, db: Session = Depends(get_db)):
    reports = db.query(StrategyReport).order_by(StrategyReport.report_date.desc()).limit(limit).all()
    return [_report_to_schema(r) for r in reports]


@router.get("/latest", response_model=StrategyReportOut)
def get_latest_report(db: Session = Depends(get_db)):
    report = db.query(StrategyReport).order_by(StrategyReport.report_date.desc()).first()
    if not report:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="No reports yet — the first report generates on Monday at 09:00")
    return _report_to_schema(report)


@router.get("/{report_id}", response_model=StrategyReportOut)
def get_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(StrategyReport).filter(StrategyReport.id == report_id).first()
    if not report:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Report not found")
    return _report_to_schema(report)


@router.post("/generate")
async def trigger_report_generation(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Manually trigger a strategy report generation."""
    background_tasks.add_task(generate_weekly_strategy_report, db)
    return {"message": "Report generation started in background"}


def _report_to_schema(r: StrategyReport) -> StrategyReportOut:
    wins = json.loads(r.wins) if r.wins else []
    losses = json.loads(r.losses) if r.losses else []
    return StrategyReportOut(
        id=r.id, report_date=r.report_date,
        week_start=r.week_start, week_end=r.week_end,
        total_posts=r.total_posts or 0,
        avg_views=r.avg_views or 0, avg_engagement_rate=r.avg_engagement_rate or 0,
        top_performing_post_id=r.top_performing_post_id,
        worst_performing_post_id=r.worst_performing_post_id,
        report_content=r.report_content, wins=wins, losses=losses,
        next_week_direction=r.next_week_direction, created_at=r.created_at,
    )
