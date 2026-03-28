"""
Routes a confirmed VoiceEntry to the appropriate domain table.

Called after the user taps "Confirm" on the confirmation card.
Reads the voice_entry.extracted_data (set by claude_voice.py) and writes
the structured record to baby_logs, dog_logs, household_tasks, or calendar_events.
"""
from datetime import date, time, datetime
import logging
import uuid

from dateutil import parser as dateutil_parser
from sqlalchemy.orm import Session

from app.models.voice_entry import VoiceEntry
from app.models.baby_log import BabyLog
from app.models.dog_log import DogLog
from app.models.household_task import HouseholdTask

logger = logging.getLogger(__name__)


def _parse_time(value: str | None) -> time | None:
    """Parse a time string from Claude's extracted_data.

    Handles formats like '02:00', '2:30 AM', '14:00', '0200', '2h30'.
    Falls back gracefully to None with a warning if unparseable.
    """
    if not value:
        return None
    try:
        # dateutil can parse "2:00 AM", "14:00", "02:00", etc.
        # We anchor to today to avoid date-part interference.
        anchor = datetime.combine(date.today(), time.min)
        parsed = dateutil_parser.parse(str(value), default=anchor)
        return parsed.time()
    except (ValueError, OverflowError):
        logger.warning("Could not parse time value: %r — storing as None", value)
        return None


def _parse_date(value: str | None) -> date | None:
    """Parse a date string from Claude's extracted_data.

    Handles ISO dates ('2025-04-01'), relative expressions ('tomorrow',
    'next Friday'), and locale formats ('28/3/2025').
    Uses today as the default anchor so relative terms resolve correctly.
    Falls back gracefully to None with a warning if unparseable.
    """
    if not value:
        return None
    # Pass-through if already a date object (defensive)
    if isinstance(value, date):
        return value
    try:
        anchor = datetime.combine(date.today(), time.min)
        parsed = dateutil_parser.parse(str(value), default=anchor)
        return parsed.date()
    except (ValueError, OverflowError):
        logger.warning("Could not parse date value: %r — storing as None", value)
        return None


async def route_confirmed_entry(entry: VoiceEntry, db: Session) -> str:
    """Write confirmed entry to the correct domain table. Returns table name."""
    raw = entry.extracted_data or {}
    data = raw.get("extracted_data", raw)

    if entry.category == "baby" and entry.entry_type == "diary_entry":
        log = BabyLog(
            voice_entry_id=entry.id,
            log_date=date.today(),
            wake_time=_parse_time(data.get("wake_time")),
            feed_time=_parse_time(data.get("feed_time")),
            feed_type=data.get("feed_type"),
            diaper_count=data.get("diaper_count"),
            diaper_type=data.get("diaper_type"),
            sleep_time=_parse_time(data.get("sleep_time")),
            medication=data.get("medication"),
            notes=data.get("notes") or entry.raw_transcription,
            logged_by=entry.speaker_id,
        )
        db.add(log)
        db.commit()
        return "baby_logs"

    elif entry.category == "dog":
        activity_type = data.get("activity_type")
        if not activity_type:
            logger.warning(
                "No activity_type in extracted_data for dog entry %s — defaulting to 'walk'",
                entry.id,
            )
            activity_type = "walk"
        log = DogLog(
            voice_entry_id=entry.id,
            log_date=date.today(),
            activity_type=activity_type,
            duration_min=data.get("duration_min"),
            notes=data.get("notes") or entry.raw_transcription,
            done_by=entry.speaker_id,
        )
        db.add(log)
        db.commit()
        return "dog_logs"

    elif entry.category == "household" and entry.entry_type == "task":
        task = HouseholdTask(
            voice_entry_id=entry.id,
            title=data.get("task", entry.raw_transcription[:255]),
            assigned_to=entry.speaker_id,  # default to speaker; can be edited in UI
            due_date=_parse_date(data.get("due_date")),
            status="pending",
        )
        db.add(task)
        db.commit()
        return "household_tasks"

    elif entry.entry_type == "calendar_event":
        # Phase 2: create Google Calendar event — stub for now
        # calendar_sync.create_event(entry, db)
        return "calendar_events (Phase 2 — not yet synced to Google)"

    # Notes and reminders: stored only in voice_entries (no separate table)
    return "voice_entries"
