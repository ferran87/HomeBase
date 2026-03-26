"""
Tests for entry_router.py — verifies that confirmed VoiceEntry records
are routed to the correct domain tables.
"""
import uuid
from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from app.models.voice_entry import VoiceEntry
from app.models.baby_log import BabyLog
from app.models.dog_log import DogLog
from app.models.household_task import HouseholdTask
from app.services.entry_router import route_confirmed_entry


def _make_entry(db: Session, speaker_id: uuid.UUID, category: str, entry_type: str, extracted: dict) -> VoiceEntry:
    entry = VoiceEntry(
        speaker_id=speaker_id,
        category=category,
        entry_type=entry_type,
        raw_transcription="test transcription",
        language_detected="en",
        extracted_data=extracted,
        confirmed=True,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@pytest.mark.asyncio
async def test_baby_diary_entry_routes_to_baby_logs(db, two_users):
    parent1, _ = two_users
    entry = _make_entry(db, parent1.id, "baby", "diary_entry", {
        "wake_time": "02:00",
        "feed_time": "02:30",
        "feed_type": "breast",
        "diaper_count": 2,
        "diaper_type": "dirty",
        "sleep_time": "03:00",
        "notes": "Good night overall",
    })

    result = await route_confirmed_entry(entry=entry, db=db)

    assert result == "baby_logs"
    log = db.query(BabyLog).filter(BabyLog.voice_entry_id == entry.id).first()
    assert log is not None
    assert log.feed_type == "breast"
    assert log.diaper_count == 2


@pytest.mark.asyncio
async def test_dog_walk_routes_to_dog_logs(db, two_users):
    parent1, _ = two_users
    entry = _make_entry(db, parent1.id, "dog", "diary_entry", {
        "activity_type": "walk",
        "duration_min": 30,
        "notes": "Morning walk in the park",
    })

    result = await route_confirmed_entry(entry=entry, db=db)

    assert result == "dog_logs"
    log = db.query(DogLog).filter(DogLog.voice_entry_id == entry.id).first()
    assert log is not None
    assert log.activity_type == "walk"
    assert log.duration_min == 30


@pytest.mark.asyncio
async def test_household_task_routes_to_household_tasks(db, two_users):
    parent1, _ = two_users
    entry = _make_entry(db, parent1.id, "household", "task", {
        "task": "Take bins out",
        "due_date": None,
    })

    result = await route_confirmed_entry(entry=entry, db=db)

    assert result == "household_tasks"
    task = db.query(HouseholdTask).filter(HouseholdTask.voice_entry_id == entry.id).first()
    assert task is not None
    assert task.title == "Take bins out"
    assert task.status == "pending"


@pytest.mark.asyncio
async def test_note_stays_in_voice_entries(db, two_users):
    parent1, _ = two_users
    entry = _make_entry(db, parent1.id, "household", "note", {
        "notes": "Remember to call the pediatrician",
    })

    result = await route_confirmed_entry(entry=entry, db=db)

    assert result == "voice_entries"
    # No record in other tables
    assert db.query(BabyLog).count() == 0
    assert db.query(DogLog).count() == 0
    assert db.query(HouseholdTask).count() == 0
