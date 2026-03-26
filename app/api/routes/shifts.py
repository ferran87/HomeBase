import uuid
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.night_shift import NightShift

router = APIRouter()


class ShiftIn(BaseModel):
    on_duty: str  # user UUID
    shift_date: date | None = None
    notes: str | None = None


@router.post("/")
async def set_on_duty(payload: ShiftIn, db: Session = Depends(get_db)) -> dict:
    """Set who is on duty for a given night (defaults to tonight)."""
    shift = NightShift(
        shift_date=payload.shift_date or date.today(),
        on_duty=uuid.UUID(payload.on_duty),
        notes=payload.notes,
    )
    db.add(shift)
    db.commit()
    db.refresh(shift)
    return {
        "id": str(shift.id),
        "shift_date": shift.shift_date.isoformat(),
        "on_duty": str(shift.on_duty),
    }


@router.get("/history")
async def get_shift_history(limit: int = 7, db: Session = Depends(get_db)) -> list[dict]:
    """Return the last N nights of shift history."""
    shifts = (
        db.query(NightShift)
        .order_by(NightShift.shift_date.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "shift_date": s.shift_date.isoformat(),
            "on_duty": str(s.on_duty),
            "notes": s.notes,
        }
        for s in shifts
    ]
