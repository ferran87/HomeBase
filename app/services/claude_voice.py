"""
Voice pipeline: send audio to Claude API for transcription + classification in one call.

Claude receives the raw audio bytes and returns a structured JSON response containing:
  - transcription: verbatim text of what was said
  - language_detected: "ca" | "es" | "en"
  - category: "baby" | "dog" | "household"
  - type: "diary_entry" | "calendar_event" | "task" | "reminder" | "note"
  - extracted_data: dict of structured fields (times, dates, quantities, etc.)
  - suggested_action: what the app should do with this entry

Audio format: WebM/Opus blob from the browser's MediaRecorder API.
The Anthropic SDK receives it as base64-encoded bytes.
"""
import base64
import json
import uuid
from datetime import datetime

import anthropic
from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import User
from app.models.voice_entry import VoiceEntry

CLASSIFICATION_PROMPT = """\
You are a household assistant for a family with a newborn baby girl and a dog.
The input is a raw audio recording. Do two things:
1. Transcribe the audio exactly as spoken.
2. Classify and extract structured data.

Family context:
- Speaker: {speaker_name}
- Partner: {partner_name}
- Baby girl, newborn
- One dog
- Current date/time: {datetime}

Respond ONLY in JSON with this exact structure:
{{
  "transcription": "<verbatim transcription of the audio>",
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


async def process_audio(
    audio_bytes: bytes,
    speaker_id: uuid.UUID,
    db: Session,
) -> dict:
    """
    Send audio bytes to Claude API.
    Stores the result as an unconfirmed VoiceEntry and returns the full classification dict.
    """
    # Look up speaker and derive partner name
    speaker = db.get(User, speaker_id)
    if not speaker:
        raise ValueError(f"Speaker {speaker_id} not found")

    all_users = db.query(User).filter(User.id != speaker_id).all()
    partner_name = all_users[0].name if all_users else "Partner"

    # Call Claude API with audio input
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    audio_b64 = base64.standard_b64encode(audio_bytes).decode("utf-8")

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "audio/webm",
                            "data": audio_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": CLASSIFICATION_PROMPT.format(
                            speaker_name=speaker.name,
                            partner_name=partner_name,
                            datetime=datetime.now().strftime("%Y-%m-%d %H:%M"),
                        ),
                    },
                ],
            }
        ],
    )

    raw_text = response.content[0].text.strip()

    # Strip markdown code fences if Claude wraps the JSON
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    result = json.loads(raw_text)

    # Persist as unconfirmed voice entry
    entry = VoiceEntry(
        speaker_id=speaker_id,
        category=result["category"],
        entry_type=result["type"],
        raw_transcription=result["transcription"],
        language_detected=result.get("language_detected"),
        extracted_data=result,
        confirmed=False,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    result["voice_entry_id"] = str(entry.id)
    return result
