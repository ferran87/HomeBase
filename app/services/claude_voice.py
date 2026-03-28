"""
Voice pipeline: send transcribed text to Claude API for classification.

The browser's Web Speech API handles transcription (supports Catalan, Spanish, English).
Claude receives the text and returns structured JSON containing:
  - category: "baby" | "dog" | "household"
  - type: "diary_entry" | "calendar_event" | "task" | "reminder" | "note"
  - extracted_data: dict of structured fields (times, dates, quantities, etc.)
  - suggested_action: what the app should do with this entry
"""
import json
import uuid
from datetime import datetime, timezone

import anthropic
from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import User
from app.models.voice_entry import VoiceEntry

CLASSIFICATION_PROMPT = """\
You are a household assistant for a family with a newborn baby girl and a dog.
The user has spoken the following text (transcribed by speech recognition).
Classify it and extract structured data.

Family context:
- Speaker: {speaker_name}
- Partner: {partner_name}
- Baby girl, newborn
- One dog
- Current date/time: {datetime}

The text may be in Catalan, Spanish, or English. Detect the language.

Respond ONLY in JSON with this exact structure:
{{
  "language_detected": "ca | es | en",
  "category": "baby | dog | household",
  "type": "diary_entry | calendar_event | task | reminder | note",
  "extracted_data": {{
    "<relevant fields based on category and type>"
  }},
  "suggested_action": "store_diary_entry | create_calendar_event | create_task | store_note"
}}

For baby diary entries, extract: wake_time, feed_time, feed_type, diaper_count, diaper_type, sleep_time, medication, notes
For dog logs, extract: activity_type, duration_min, notes
For household tasks, extract: task, assigned_to (speaker | partner | both), due_date
For calendar events, extract: event_title, date, time, duration_min
"""


async def classify_text(
    transcription: str,
    speaker_id: uuid.UUID,
    language_hint: str,
    db: Session,
) -> dict:
    """
    Send transcribed text to Claude API for classification.
    Stores the result as an unconfirmed VoiceEntry and returns the classification dict.
    """
    speaker = db.get(User, speaker_id)
    if not speaker:
        raise ValueError(f"Speaker {speaker_id} not found")

    all_users = db.query(User).filter(User.id != speaker_id).all()
    partner_name = all_users[0].name if all_users else "Partner"

    api_key = settings.anthropic_api_key
    if not api_key or api_key.startswith("your_"):
        raise ValueError(
            "Anthropic API key not configured. "
            "Set ANTHROPIC_API_KEY in your .env file."
        )

    client = anthropic.Anthropic(api_key=api_key)

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": CLASSIFICATION_PROMPT.format(
                    speaker_name=speaker.name,
                    partner_name=partner_name,
                    datetime=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
                ) + f"\n\nTranscribed text: \"{transcription}\"",
            }
        ],
    )

    raw_text = response.content[0].text.strip()

    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    result = json.loads(raw_text)

    lang = result.get("language_detected", language_hint or "en")

    entry = VoiceEntry(
        speaker_id=speaker_id,
        category=result["category"],
        entry_type=result["type"],
        raw_transcription=transcription,
        language_detected=lang,
        extracted_data=result,
        confirmed=False,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    result["voice_entry_id"] = str(entry.id)
    result["transcription"] = transcription
    return result
