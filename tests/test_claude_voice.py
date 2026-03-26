"""
Tests for claude_voice.py — mocks the Claude API so no real API calls are made.
Verifies that the service correctly parses Claude's JSON response and
stores an unconfirmed VoiceEntry in the DB.
"""
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.user import User
from app.models.voice_entry import VoiceEntry
from app.services.claude_voice import process_audio

BABY_RESPONSE = {
    "transcription": "La nena s'ha despertat a les 2, ha menjat a les 2:30",
    "language_detected": "ca",
    "category": "baby",
    "type": "diary_entry",
    "extracted_data": {
        "wake_time": "02:00",
        "feed_time": "02:30",
        "feed_type": "breast",
        "diaper_count": 1,
        "diaper_type": "wet",
        "sleep_time": "03:00",
        "notes": "Woke at 2am, fed at 2:30",
    },
    "suggested_action": "store_diary_entry",
}

DOG_RESPONSE = {
    "transcription": "Cita del veterinario el jueves a las 10",
    "language_detected": "es",
    "category": "dog",
    "type": "calendar_event",
    "extracted_data": {
        "event_title": "Vet appointment",
        "date": "next Thursday",
        "time": "10:00",
    },
    "suggested_action": "create_calendar_event",
}

HOUSEHOLD_RESPONSE = {
    "transcription": "Take the bins out tomorrow",
    "language_detected": "en",
    "category": "household",
    "type": "task",
    "extracted_data": {
        "task": "Take bins out",
        "assigned_to": "speaker",
        "due_date": None,
    },
    "suggested_action": "create_task",
}


def _mock_claude(response_dict: dict):
    """Return a mock Anthropic client that yields a fixed JSON response."""
    mock_content = MagicMock()
    mock_content.text = json.dumps(response_dict)
    mock_response = MagicMock()
    mock_response.content = [mock_content]

    mock_messages = MagicMock()
    mock_messages.create.return_value = mock_response

    mock_client = MagicMock()
    mock_client.messages = mock_messages
    return mock_client


@pytest.mark.asyncio
async def test_baby_diary_entry_parsed_correctly(db, two_users):
    parent1, _ = two_users

    with patch("app.services.claude_voice.anthropic.Anthropic", return_value=_mock_claude(BABY_RESPONSE)):
        result = await process_audio(audio_bytes=b"fake_audio", speaker_id=parent1.id, db=db)

    assert result["category"] == "baby"
    assert result["type"] == "diary_entry"
    assert result["language_detected"] == "ca"
    assert "voice_entry_id" in result

    entry = db.query(VoiceEntry).filter(VoiceEntry.id == uuid.UUID(result["voice_entry_id"])).first()
    assert entry is not None
    assert entry.confirmed is False
    assert entry.category == "baby"


@pytest.mark.asyncio
async def test_dog_calendar_event_parsed_correctly(db, two_users):
    parent1, _ = two_users

    with patch("app.services.claude_voice.anthropic.Anthropic", return_value=_mock_claude(DOG_RESPONSE)):
        result = await process_audio(audio_bytes=b"fake_audio", speaker_id=parent1.id, db=db)

    assert result["category"] == "dog"
    assert result["type"] == "calendar_event"
    assert result["language_detected"] == "es"


@pytest.mark.asyncio
async def test_household_task_parsed_correctly(db, two_users):
    parent1, _ = two_users

    with patch("app.services.claude_voice.anthropic.Anthropic", return_value=_mock_claude(HOUSEHOLD_RESPONSE)):
        result = await process_audio(audio_bytes=b"fake_audio", speaker_id=parent1.id, db=db)

    assert result["category"] == "household"
    assert result["type"] == "task"
    assert result["language_detected"] == "en"


@pytest.mark.asyncio
async def test_markdown_fenced_json_is_stripped(db, two_users):
    """Claude sometimes wraps JSON in ```json ... ``` — verify it's handled."""
    parent1, _ = two_users
    fenced_response = dict(BABY_RESPONSE)

    mock_content = MagicMock()
    mock_content.text = f"```json\n{json.dumps(fenced_response)}\n```"
    mock_response = MagicMock()
    mock_response.content = [mock_content]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    with patch("app.services.claude_voice.anthropic.Anthropic", return_value=mock_client):
        result = await process_audio(audio_bytes=b"fake_audio", speaker_id=parent1.id, db=db)

    assert result["category"] == "baby"
