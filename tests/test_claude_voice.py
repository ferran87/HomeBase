"""
Tests for claude_voice.py — mocks the Claude API so no real API calls are made.
Verifies that the service correctly parses Claude's JSON response and
stores an unconfirmed VoiceEntry in the DB.
"""
import json
import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.models.user import User
from app.models.voice_entry import VoiceEntry
from app.services.claude_voice import classify_text

BABY_RESPONSE = {
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


def _patch_claude(response_dict_or_client):
    """Context manager that patches both the Anthropic client and the API key check."""
    client = response_dict_or_client if isinstance(response_dict_or_client, MagicMock) else _mock_claude(response_dict_or_client)
    return patch.multiple(
        "app.services.claude_voice",
        anthropic=MagicMock(Anthropic=MagicMock(return_value=client)),
        settings=MagicMock(anthropic_api_key="test-key"),
    )


@pytest.mark.asyncio
async def test_baby_diary_entry_classified_correctly(db, two_users):
    parent1, _ = two_users

    with _patch_claude(BABY_RESPONSE):
        result = await classify_text(
            transcription="La nena s'ha despertat a les 2, ha menjat a les 2:30",
            speaker_id=parent1.id,
            language_hint="ca",
            db=db,
        )

    assert result["category"] == "baby"
    assert result["type"] == "diary_entry"
    assert result["language_detected"] == "ca"
    assert "voice_entry_id" in result

    entry = db.query(VoiceEntry).filter(VoiceEntry.id == uuid.UUID(result["voice_entry_id"])).first()
    assert entry is not None
    assert entry.confirmed is False
    assert entry.category == "baby"
    assert entry.raw_transcription == "La nena s'ha despertat a les 2, ha menjat a les 2:30"


@pytest.mark.asyncio
async def test_dog_calendar_event_classified_correctly(db, two_users):
    parent1, _ = two_users

    with _patch_claude(DOG_RESPONSE):
        result = await classify_text(
            transcription="Cita del veterinario el jueves a las 10",
            speaker_id=parent1.id,
            language_hint="es",
            db=db,
        )

    assert result["category"] == "dog"
    assert result["type"] == "calendar_event"
    assert result["language_detected"] == "es"


@pytest.mark.asyncio
async def test_household_task_classified_correctly(db, two_users):
    parent1, _ = two_users

    with _patch_claude(HOUSEHOLD_RESPONSE):
        result = await classify_text(
            transcription="Take the bins out tomorrow",
            speaker_id=parent1.id,
            language_hint="en",
            db=db,
        )

    assert result["category"] == "household"
    assert result["type"] == "task"
    assert result["language_detected"] == "en"


@pytest.mark.asyncio
async def test_markdown_fenced_json_is_stripped(db, two_users):
    """Claude sometimes wraps JSON in ```json ... ``` — verify it's handled."""
    parent1, _ = two_users

    mock_content = MagicMock()
    mock_content.text = f"```json\n{json.dumps(BABY_RESPONSE)}\n```"
    mock_response = MagicMock()
    mock_response.content = [mock_content]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    with _patch_claude(mock_client):
        result = await classify_text(
            transcription="La nena s'ha despertat a les 2",
            speaker_id=parent1.id,
            language_hint="ca",
            db=db,
        )

    assert result["category"] == "baby"
