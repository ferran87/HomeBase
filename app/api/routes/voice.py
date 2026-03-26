import uuid
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.claude_voice import process_audio
from app.services.entry_router import route_confirmed_entry
from app.models.voice_entry import VoiceEntry

router = APIRouter()


@router.post("/")
async def receive_voice(
    audio: UploadFile = File(...),
    speaker_id: str = Form(...),
    db: Session = Depends(get_db),
) -> dict:
    """
    Step 1: Receive audio from the browser, send to Claude API for
    transcription + classification. Returns the classified result for
    the user to review in the confirmation card. Does NOT write to DB yet.
    """
    audio_bytes = await audio.read()
    result = await process_audio(
        audio_bytes=audio_bytes,
        speaker_id=uuid.UUID(speaker_id),
        db=db,
    )
    return result


@router.post("/confirm")
async def confirm_entry(
    voice_entry_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """
    Step 2: User has reviewed and confirmed the classified result.
    Mark the voice_entry as confirmed and route to the appropriate table.
    """
    entry = db.get(VoiceEntry, uuid.UUID(voice_entry_id))
    if not entry:
        raise HTTPException(status_code=404, detail="Voice entry not found")

    entry.confirmed = True
    db.commit()

    routed = await route_confirmed_entry(entry=entry, db=db)
    return {"status": "saved", "routed_to": routed}


@router.get("/today")
async def get_today_feed(db: Session = Depends(get_db)) -> list[dict]:
    """Return all confirmed voice entries from today, ordered by time."""
    from datetime import date
    from sqlalchemy import cast, Date

    entries = (
        db.query(VoiceEntry)
        .filter(
            VoiceEntry.confirmed.is_(True),
            cast(VoiceEntry.created_at, Date) == date.today(),
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
