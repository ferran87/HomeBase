import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.claude_voice import classify_text
from app.services.entry_router import route_confirmed_entry
from app.models.voice_entry import VoiceEntry

router = APIRouter()


class ClassifyRequest(BaseModel):
    text: str
    speaker_id: str
    language_hint: str = ""


@router.post("/classify")
async def classify_voice_text(
    payload: ClassifyRequest,
    db: Session = Depends(get_db),
) -> dict:
    """
    Receive transcribed text from the browser's Speech Recognition API,
    send to Claude for classification, and return the result for confirmation.
    """
    result = await classify_text(
        transcription=payload.text,
        speaker_id=uuid.UUID(payload.speaker_id),
        language_hint=payload.language_hint,
        db=db,
    )
    return result


@router.post("/confirm")
async def confirm_entry(
    voice_entry_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """
    User has reviewed and confirmed the classified result.
    Mark the voice_entry as confirmed and route to the appropriate table.
    """
    entry = db.get(VoiceEntry, uuid.UUID(voice_entry_id))
    if not entry:
        raise HTTPException(status_code=404, detail="Voice entry not found")

    entry.confirmed = True
    db.commit()

    routed = await route_confirmed_entry(entry=entry, db=db)
    return {"status": "saved", "routed_to": routed}


@router.delete("/discard")
async def discard_entry(
    voice_entry_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """Discard an unconfirmed voice entry (removes the orphan row)."""
    entry = db.get(VoiceEntry, uuid.UUID(voice_entry_id))
    if not entry:
        raise HTTPException(status_code=404, detail="Voice entry not found")
    if entry.confirmed:
        raise HTTPException(status_code=400, detail="Cannot discard a confirmed entry")
    db.delete(entry)
    db.commit()
    return {"status": "discarded", "voice_entry_id": voice_entry_id}


@router.get("/today")
async def get_today_feed(db: Session = Depends(get_db)) -> list[dict]:
    """Return all confirmed voice entries from today, ordered by time."""
    from datetime import datetime, timedelta, timezone

    # Use UTC-anchored boundaries so the feed is correct regardless of server timezone
    now_utc = datetime.now(timezone.utc)
    today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0).replace(tzinfo=None)
    tomorrow_start = today_start + timedelta(days=1)

    entries = (
        db.query(VoiceEntry)
        .filter(
            VoiceEntry.confirmed.is_(True),
            VoiceEntry.created_at >= today_start,
            VoiceEntry.created_at < tomorrow_start,
        )
        .order_by(VoiceEntry.created_at.asc())
        .all()
    )
    return [
        {
            "id": str(e.id),
            "category": e.category,
            "entry_type": e.entry_type,
            "transcription": e.raw_transcription,
            "language": e.language_detected,
            "extracted_data": e.extracted_data,
            "created_at": e.created_at.isoformat(),
        }
        for e in entries
    ]
