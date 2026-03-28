"""
Endpoint-level tests for the voice pipeline routes.

Uses a mocked Claude API so no real API calls are made.
Tests cover: classify, confirm, discard, and today feed.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ─── Fixtures from conftest.py: client, db, two_users ────────────────────────


MOCK_CLAUDE_RESPONSE = {
    "language_detected": "en",
    "category": "household",
    "type": "task",
    "extracted_data": {
        "task": "Take bins out",
        "due_date": None,
        "notes": "Take bins out tomorrow",
    },
    "suggested_action": "create_task",
}


def _mock_classify(monkeypatch, response: dict | None = None) -> None:
    """Patch classify_text so no real Anthropic call is made."""
    payload = response or MOCK_CLAUDE_RESPONSE

    async def fake_classify(transcription, speaker_id, language_hint, db):
        from app.models.voice_entry import VoiceEntry
        import uuid as _uuid
        from datetime import datetime, timezone

        entry = VoiceEntry(
            id=_uuid.uuid4(),
            speaker_id=speaker_id,
            category=payload["category"],
            entry_type=payload["type"],
            raw_transcription=transcription,
            language_detected=payload["language_detected"],
            extracted_data=payload,
            confirmed=False,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return {**payload, "transcription": transcription, "voice_entry_id": str(entry.id)}

    monkeypatch.setattr("app.api.routes.voice.classify_text", fake_classify)


# ─── Tests ────────────────────────────────────────────────────────────────────


def test_classify_returns_classification(client, two_users, monkeypatch):
    """POST /api/voice/classify returns category, type and voice_entry_id."""
    _mock_classify(monkeypatch)
    parent1, _ = two_users

    resp = client.post(
        "/api/voice/classify",
        json={"text": "Take the bins out tomorrow", "speaker_id": str(parent1.id), "language_hint": "en"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["category"] == "household"
    assert body["type"] == "task"
    assert "voice_entry_id" in body


def test_classify_creates_unconfirmed_entry(client, db, two_users, monkeypatch):
    """After classify, the voice_entry row exists but confirmed=False."""
    from app.models.voice_entry import VoiceEntry

    _mock_classify(monkeypatch)
    parent1, _ = two_users

    resp = client.post(
        "/api/voice/classify",
        json={"text": "Walk the dog", "speaker_id": str(parent1.id), "language_hint": "en"},
    )
    entry_id = resp.json()["voice_entry_id"]
    entry = db.get(VoiceEntry, uuid.UUID(entry_id))
    assert entry is not None
    assert entry.confirmed is False


def test_confirm_marks_entry_and_routes(client, db, two_users, monkeypatch):
    """POST /api/voice/confirm marks confirmed=True and routes to correct table."""
    from app.models.voice_entry import VoiceEntry
    from app.models.household_task import HouseholdTask

    _mock_classify(monkeypatch)
    parent1, _ = two_users

    classify_resp = client.post(
        "/api/voice/classify",
        json={"text": "Take the bins out tomorrow", "speaker_id": str(parent1.id), "language_hint": "en"},
    )
    entry_id = classify_resp.json()["voice_entry_id"]

    confirm_resp = client.post(f"/api/voice/confirm?voice_entry_id={entry_id}")
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["status"] == "saved"
    assert confirm_resp.json()["routed_to"] == "household_tasks"

    entry = db.get(VoiceEntry, uuid.UUID(entry_id))
    assert entry.confirmed is True

    task = db.query(HouseholdTask).filter_by(voice_entry_id=uuid.UUID(entry_id)).first()
    assert task is not None
    assert task.title == "Take bins out"


def test_discard_removes_unconfirmed_entry(client, db, two_users, monkeypatch):
    """DELETE /api/voice/discard removes the unconfirmed voice_entry row."""
    from app.models.voice_entry import VoiceEntry

    _mock_classify(monkeypatch)
    parent1, _ = two_users

    classify_resp = client.post(
        "/api/voice/classify",
        json={"text": "Some random note", "speaker_id": str(parent1.id), "language_hint": "en"},
    )
    entry_id = classify_resp.json()["voice_entry_id"]

    discard_resp = client.delete(f"/api/voice/discard?voice_entry_id={entry_id}")
    assert discard_resp.status_code == 200
    assert discard_resp.json()["status"] == "discarded"

    entry = db.get(VoiceEntry, uuid.UUID(entry_id))
    assert entry is None


def test_discard_refuses_confirmed_entry(client, two_users, monkeypatch):
    """DELETE /api/voice/discard returns 400 if entry is already confirmed."""
    _mock_classify(monkeypatch)
    parent1, _ = two_users

    classify_resp = client.post(
        "/api/voice/classify",
        json={"text": "Take bins out", "speaker_id": str(parent1.id), "language_hint": "en"},
    )
    entry_id = classify_resp.json()["voice_entry_id"]
    client.post(f"/api/voice/confirm?voice_entry_id={entry_id}")

    discard_resp = client.delete(f"/api/voice/discard?voice_entry_id={entry_id}")
    assert discard_resp.status_code == 400


def test_today_feed_returns_confirmed_entries(client, db, two_users, monkeypatch):
    """GET /api/voice/today returns confirmed entries only."""
    _mock_classify(monkeypatch)
    parent1, _ = two_users

    # Classify + confirm one entry
    classify_resp = client.post(
        "/api/voice/classify",
        json={"text": "Walked the dog", "speaker_id": str(parent1.id), "language_hint": "en"},
    )
    entry_id = classify_resp.json()["voice_entry_id"]
    client.post(f"/api/voice/confirm?voice_entry_id={entry_id}")

    # Classify but do NOT confirm a second entry
    client.post(
        "/api/voice/classify",
        json={"text": "Unconfirmed thought", "speaker_id": str(parent1.id), "language_hint": "en"},
    )

    feed_resp = client.get("/api/voice/today")
    assert feed_resp.status_code == 200
    feed = feed_resp.json()
    assert len(feed) == 1
    assert feed[0]["transcription"] == "Walked the dog"


def test_confirm_unknown_entry_returns_404(client):
    """POST /api/voice/confirm with a random UUID returns 404."""
    resp = client.post(f"/api/voice/confirm?voice_entry_id={uuid.uuid4()}")
    assert resp.status_code == 404
