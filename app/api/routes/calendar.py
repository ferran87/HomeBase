from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.calendar_event import CalendarEvent

router = APIRouter()

CATEGORY_EMOJI = {"baby": "🍼", "dog": "🐕", "household": "🏠"}


@router.get("/events")
async def get_calendar_events(
    year: int,
    month: int,
    db: Session = Depends(get_db),
) -> list[dict]:
    """Return all calendar events for the given year and month."""
    if not (1 <= month <= 12):
        raise HTTPException(status_code=400, detail="month must be 1–12")

    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)

    events = (
        db.query(CalendarEvent)
        .filter(CalendarEvent.event_date >= start, CalendarEvent.event_date < end)
        .order_by(CalendarEvent.event_date, CalendarEvent.event_time)
        .all()
    )
    return [
        {
            "id": str(e.id),
            "category": e.category,
            "emoji": CATEGORY_EMOJI.get(e.category, "📅"),
            "title": e.title,
            "event_date": e.event_date.isoformat(),
            "event_time": e.event_time.strftime("%H:%M") if e.event_time else None,
            "duration_min": e.duration_min,
            "notes": e.notes,
            "google_event_id": e.google_event_id,
        }
        for e in events
    ]
