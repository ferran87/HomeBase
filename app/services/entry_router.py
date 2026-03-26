"""
Routes a confirmed VoiceEntry to the appropriate domain table.

Called after the user taps "Confirm" on the confirmation card.
Reads the voice_entry.extracted_data (set by claude_voice.py) and writes
the structured record to baby_logs, dog_logs, household_tasks, or calendar_events.
"""
from datetime import date, time
import uuid

from sqlalchemy.orm import Session

from app.models.voice_entry import VoiceEntry
from app.models.baby_log import BabyLog
from app.models.dog_log import DogLog
from app.models.household_task import HouseholdTask


def _parse_time(value: str | None) -> time | None:
    if not value:
        return None
    try:
        parts = value.split(":")
        return time(int(parts[0]), int(parts[1]))
    except (ValueError, IndexError):
        return None


def _parse_date(value: str | None) -> date | None:
    """Naive ISO date parse — Claude should return YYYY-MM-DD when possible."""
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


async def route_confirmed_entry(entry: VoiceEntry, db: Session) -> str:
    """Write confirmed entry to the correct domain table. Returns table name."""
    data = entry.extracted_data or {}

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
        log = DogLog(
            voice_entry_id=entry.id,
            log_date=date.today(),
            activity_type=data.get("activity_type", "walk"),
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
