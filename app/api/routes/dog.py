from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.dog_log import DogLog

router = APIRouter()


@router.get("/logs")
async def get_dog_logs(
    log_date: date | None = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    """Return dog logs, optionally filtered by date."""
    query = db.query(DogLog)
    if log_date:
        query = query.filter(DogLog.log_date == log_date)
    logs = query.order_by(DogLog.created_at.desc()).all()
    return [
        {
            "id": str(log.id),
            "log_date": log.log_date.isoformat(),
            "activity_type": log.activity_type,
            "duration_min": log.duration_min,
            "notes": log.notes,
            "done_by": str(log.done_by),
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]
