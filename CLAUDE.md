# HomeBase — Voice-First Family Command Center

## About This Project

Voice-first web app for household coordination between two parents with a newborn baby and a dog.
Users speak in Catalan, Spanish, or English. The app transcribes + classifies input via Claude API
(one call handles both), shows a confirmation card, then stores to the DB and optionally creates
a Google Calendar event.

## Tech Stack

- **Backend:** Python 3.11+, FastAPI
- **Frontend:** Plain HTML/JS served as static files from FastAPI
- **Database:** PostgreSQL with SQLAlchemy ORM + Alembic migrations
- **AI:** Anthropic Claude API (`claude-sonnet-4-5`) — classifies text (transcription done by browser Web Speech API)
- **Calendar:** Google Calendar API (Phase 2, shared family calendar, single OAuth token)

## Key Directories

- `app/api/routes/` — FastAPI route handlers
- `app/models/` — SQLAlchemy database models
- `app/services/` — Business logic (claude_voice, entry_router, calendar_sync, analytics)
- `app/db/` — Database connection and Alembic migrations
- `static/` — HTML/JS/CSS frontend
- `tests/` — pytest test files

## Voice Pipeline Flow

```
Browser (Web Speech API — Chrome/Edge only)
  → speech-to-text runs locally in browser
  → POST /api/voice/classify  { text, speaker_id, language_hint }
  → app/services/claude_voice.py sends TEXT to Claude API for classification
  → Claude returns JSON: language + category + type + extracted_data + suggested_action
  → Frontend shows confirmation card
  → User confirms → POST /api/voice/confirm
  → app/services/entry_router.py writes to correct table (baby_logs / dog_logs / household_tasks / calendar_events)
```

> **Note:** The MVP uses the browser's built-in Web Speech API for transcription (free, fast, ~1s).
> Claude only receives and classifies text — it does NOT receive raw audio bytes.
> Web Speech API requires Chrome or Edge. Safari/Firefox are not supported.

## Common Commands

```bash
docker compose up -d                          # Start PostgreSQL
uvicorn app.main:app --reload                 # Start API + frontend server
alembic upgrade head                          # Apply migrations
alembic revision --autogenerate -m "desc"     # Create new migration
pytest tests/ -v                              # Run tests
```

## Standards

- Type hints required on all functions
- pytest for testing
- PEP 8 with 100 character line limit
- All database changes via Alembic migrations
- Environment variables for all API keys (never hardcoded)

## Important Notes

- Voice supports 3 languages: Catalan (`ca`), Spanish (`es`), English (`en`)
- **Web Speech API** transcribes locally in browser; Claude only classifies text (no audio sent to API)
- ALL entries require user confirmation before being written to DB (`confirmed = True`)
- Calendar events go to ONE shared family Google Calendar (Phase 2)
- `night_shifts` table tracks "who's on tonight" — Phase 1 essential feature
- No `daily_notes` table: notes are `voice_entries` with `entry_type='note'`
- `cry_level` is NOT tracked — too granular; use the `notes` free-text field instead

## Data Model Summary

| Table | Purpose |
|---|---|
| `users` | Two parents (seed on first run) |
| `voice_entries` | Every voice input — raw transcription + Claude classification |
| `baby_logs` | Feeds, diapers, sleep times extracted from voice |
| `dog_logs` | Walks, feeding, vet visits |
| `household_tasks` | Tasks with assignment, due date, recurring support |
| `calendar_events` | Events created from voice → Google Calendar |
| `night_shifts` | On-duty tracker per night |

## Phase Status

- **Phase 1 (current):** Voice pipeline + daily feed + night shift tracker
- **Phase 2:** Google Calendar integration + recurring tasks
- **Phase 3:** Analytics dashboards + weekly AI summary
- **Phase 4:** NLP queries + PDF export + notifications
