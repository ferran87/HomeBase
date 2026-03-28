from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.voice_entry import VoiceEntry

router = APIRouter()

CATEGORY_EMOJI = {"baby": "🍼", "dog": "🐕", "household": "🏠"}


@router.get("/")
async def get_notes(
    category: str | None = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    """Return all confirmed notes, newest first. Optionally filter by category."""
    query = (
        db.query(VoiceEntry)
        .filter(VoiceEntry.confirmed.is_(True), VoiceEntry.entry_type == "note")
    )
    if category:
        query = query.filter(VoiceEntry.category == category)

    notes = query.order_by(VoiceEntry.created_at.desc()).all()
    return [
        {
            "id": str(n.id),
            "category": n.category,
            "emoji": CATEGORY_EMOJI.get(n.category, "📝"),
            "transcription": n.raw_transcription,
            "summary": n.summary,
            "language": n.language_detected,
            "created_at": n.created_at.isoformat(),
        }
        for n in notes
    ]
