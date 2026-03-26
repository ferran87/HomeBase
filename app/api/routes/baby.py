from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.baby_log import BabyLog

router = APIRouter()


@router.get("/logs")
async def get_baby_logs(
    log_date: date | None = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    """Return baby logs, optionally filtered by date."""
    query = db.query(BabyLog)
    if log_date:
        query = query.filter(BabyLog.log_date == log_date)
    logs = query.order_by(BabyLog.created_at.desc()).all()
    return [
        {
            "id": str(log.id),
            "log_date": log.log_date.isoformat(),
            "wake_time": log.wake_time.isoformat() if log.wake_time else None,
            "feed_time": log.feed_time.isoformat() if log.feed_time else None,
            "feed_type": log.feed_type,
            "diaper_count": log.diaper_count,
            "diaper_type": log.diaper_type,
            "sleep_time": log.sleep_time.isoformat() if log.sleep_time else None,
            "medication": log.medication,
            "notes": log.notes,
            "logged_by": str(log.logged_by),
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]
