---
name: voice-pipeline
description: Use this skill when working on app/services/claude_voice.py, app/api/routes/voice.py, or anything touching the Claude audio transcription and classification flow. Triggers when the user mentions audio processing, the voice pipeline, Whisper replacement, Claude audio input, transcription, or classification prompt.
version: 1.0.0
---

# HomeBase Voice Pipeline

The voice pipeline is the core engine of HomeBase. It handles everything from receiving the audio blob to storing the classified result. There is NO Whisper — Claude handles both transcription and classification in a single API call.

## Flow

```
Browser (MediaRecorder → WebM/Opus blob)
  → POST /api/voice/  { audio: File, speaker_id: str }
  → app/api/routes/voice.py  →  app/services/claude_voice.py
  → Claude API (audio input + classification prompt)
  → Structured JSON response
  → VoiceEntry stored (confirmed=False)
  → Return result to frontend
  → Frontend shows confirmation card
  → User taps Confirm → POST /api/voice/confirm
  → app/services/entry_router.py  writes to baby_logs / dog_logs / household_tasks
```

## Claude API Audio Input Format

The Anthropic SDK accepts audio as a document block with base64-encoded bytes:

```python
import base64
import anthropic

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
                        "media_type": "audio/webm",   # browser MediaRecorder default
                        "data": audio_b64,
                    },
                },
                {
                    "type": "text",
                    "text": CLASSIFICATION_PROMPT,
                },
            ],
        }
    ],
)
```

Supported audio media types: `audio/webm`, `audio/mp4`, `audio/wav`, `audio/flac`, `audio/ogg`

## Classification Prompt Template

The prompt is in `app/services/claude_voice.py` as `CLASSIFICATION_PROMPT`. It:
1. Sets family context (speaker name, partner name, baby girl, dog, current datetime)
2. Instructs Claude to transcribe verbatim AND classify in one pass
3. Specifies the exact JSON schema to return

**Never change the JSON field names** — `entry_router.py` reads them directly.

## Expected JSON Response

```json
{
  "transcription": "<verbatim text>",
  "language_detected": "ca | es | en",
  "category": "baby | dog | household",
  "type": "diary_entry | calendar_event | task | reminder | note",
  "extracted_data": {
    "wake_time": "02:00",
    "feed_time": "02:30",
    "feed_type": "breast | bottle | solid",
    "diaper_count": 2,
    "diaper_type": "wet | dirty | both",
    "sleep_time": "03:00",
    "medication": null,
    "notes": "free text"
  },
  "suggested_action": "store_diary_entry | create_calendar_event | create_task | store_note"
}
```

Fields in `extracted_data` vary by category/type. `entry_router.py` handles each combination.

## Error Handling

Claude sometimes wraps JSON in markdown fences (` ```json ... ``` `). `claude_voice.py` strips these:

```python
if raw_text.startswith("```"):
    raw_text = raw_text.split("```")[1]
    if raw_text.startswith("json"):
        raw_text = raw_text[4:]
    raw_text = raw_text.strip()
result = json.loads(raw_text)
```

If `json.loads` fails, raise a `ValueError` — the route handler returns a 422 so the frontend can show an error.

## Two-Step Confirm Flow

- `POST /api/voice/` — processes audio, creates `VoiceEntry(confirmed=False)`, returns JSON
- `POST /api/voice/confirm?voice_entry_id=<uuid>` — sets `confirmed=True`, calls `entry_router`

This ensures **nothing is written to the domain tables until the user explicitly confirms**.

## Testing

Mock the Anthropic client in tests — see `tests/test_claude_voice.py`:

```python
with patch("app.services.claude_voice.anthropic.Anthropic", return_value=mock_client):
    result = await process_audio(audio_bytes=b"fake", speaker_id=user.id, db=db)
```
