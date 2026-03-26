# HomeBase — Voice-First Family Command Center

A voice-first web app for household coordination between two parents with a newborn baby and a dog. Users speak in **Catalan, Spanish, or English** and the app auto-detects the language, identifies who is speaking (via tap-to-select toggle), classifies the input (baby / dog / household), extracts structured data, and takes the right action — creating a Google Calendar event, logging a diary entry, or adding a household task.

---

## Project Context

### Users
- **Primary users:** You and your wife
- **Household members:** Newborn baby girl, dog
- **Interaction mode:** Voice-first via mic button on web app
- **Languages:** Catalan, Spanish, English (auto-detected by Claude)
- **App language:** English

### Core Problem
Everything is coordinated verbally, which means things live in people's heads:
- No shared log of baby's night shifts, feeding, or health patterns
- Forgotten recurring tasks (bins, filters, vet appointments)
- Repeated "who's doing what?" conversations
- Dog care coordination gaps (walks, feeding, vet)

### Success Criteria
- Open the app and know exactly what needs to happen today/this week
- Stop having the same "who's on X" conversation
- Have a data trail of baby health patterns to show the pediatrician
- Both partners can input information hands-free via voice

---

## Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Frontend | FastAPI + HTML/JS + minimal CSS | Served as static files from FastAPI. No framework needed for Phase 1. Clean path to React later. |
| Backend | Python 3.11+ / FastAPI | API layer + serves static frontend |
| Database | PostgreSQL | SQLAlchemy ORM + Alembic migrations. Docker Compose for local dev. |
| AI (transcription + classification) | Claude API (`claude-sonnet-4-6`) | Audio input: one API call handles speech-to-text AND classification. No OpenAI/Whisper needed. |
| Calendar | Google Calendar API | One shared family calendar. Single OAuth2 token. Phase 2. |
| Hosting | Local (Phase 1) → Railway or Fly.io | Deploy when stable |

> **Note:** Streamlit was considered and dropped. Browser MediaRecorder API doesn't work reliably inside Streamlit. Plain HTML/JS served by FastAPI is simpler and gives full control over audio capture.

> **Note:** OpenAI Whisper was dropped. Claude's API accepts audio files directly, so transcription + classification happen in a single API call.

---

## Voice Pipeline Architecture

```
[User taps mic button]
  → Speaker toggle selected (tap your name before speaking)
  → Audio recorded via browser MediaRecorder API (WebM/Opus format)
  → POST /api/voice { audio_blob, speaker_id }
  → FastAPI sends audio to Claude API with classification prompt
  → Claude returns structured JSON:
      {
        "transcription": "La nena s'ha despertat a les 2...",
        "language_detected": "ca",
        "category": "baby | dog | household",
        "type": "diary_entry | calendar_event | task | reminder | note",
        "extracted_data": { ... },
        "suggested_action": "store_diary_entry | create_calendar_event | create_task | store_note"
      }
  → Frontend shows CONFIRMATION CARD (transcription + classified data)
  → User taps Confirm (or edits category/type manually)
  → Backend stores confirmed entry → routes to appropriate table → executes action
```

### Claude Classification Prompt (Draft)

```
You are a household assistant for a family with a newborn baby girl and a dog.
The input is a raw audio recording. Do two things:
1. Transcribe the audio exactly as spoken.
2. Classify and extract structured data.

Family context:
- Two parents: {speaker_name} and {partner_name}
- Baby girl, newborn
- One dog
- Current date/time: {datetime}

Respond ONLY in JSON:
{
  "transcription": "<verbatim transcription>",
  "language_detected": "ca | es | en",
  "category": "baby | dog | household",
  "type": "diary_entry | calendar_event | task | reminder | note",
  "extracted_data": { <structured fields relevant to category and type> },
  "suggested_action": "store_diary_entry | create_calendar_event | create_task | store_note"
}
```

### Example Voice Inputs and Expected Outputs

**Input (Catalan):** "La nena s'ha despertat a les 2, ha menjat a les 2:30, ha fet caca dues vegades i s'ha adormit a les 3"

```json
{
  "transcription": "La nena s'ha despertat a les 2, ha menjat a les 2:30, ha fet caca dues vegades i s'ha adormit a les 3",
  "language_detected": "ca",
  "category": "baby",
  "type": "diary_entry",
  "extracted_data": {
    "wake_time": "02:00",
    "feed_time": "02:30",
    "diaper_count": 2,
    "sleep_time": "03:00",
    "notes": "Woke at 2am, fed at 2:30, 2 diaper changes, back to sleep at 3am"
  },
  "suggested_action": "store_diary_entry"
}
```

**Input (Spanish):** "Cita del veterinario el jueves que viene a las 10 de la mañana"

```json
{
  "category": "dog",
  "type": "calendar_event",
  "extracted_data": {
    "event_title": "Vet appointment",
    "date": "next Thursday",
    "time": "10:00"
  },
  "suggested_action": "create_calendar_event"
}
```

**Input (English):** "Take the bins out tomorrow, it's my turn"

```json
{
  "category": "household",
  "type": "task",
  "extracted_data": {
    "task": "Take bins out",
    "date": "tomorrow",
    "assigned_to": "speaker"
  },
  "suggested_action": "create_task"
}
```

---

## Data Model

### Tables

> **Removed:** `daily_notes` table. Notes are just voice entries with `type='note'`. Free-text lives in `raw_transcription`. No separate table needed.

#### `users`
| Column | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| name | VARCHAR | Display name |
| email | VARCHAR | For Google Calendar sync |
| created_at | TIMESTAMP | |

#### `voice_entries`
| Column | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| speaker_id | UUID | FK → users |
| category | ENUM | baby, dog, household |
| entry_type | ENUM | diary_entry, calendar_event, task, reminder, note |
| raw_transcription | TEXT | Original speech in original language |
| language_detected | VARCHAR | ca, es, en |
| extracted_data | JSONB | Full Claude output |
| confirmed | BOOLEAN | User confirmed this entry (default false until tapped) |
| created_at | TIMESTAMP | |

#### `baby_logs`
| Column | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| voice_entry_id | UUID | FK → voice_entries |
| log_date | DATE | Date of the entry |
| wake_time | TIME | Nullable |
| feed_time | TIME | Nullable |
| feed_type | VARCHAR | breast, bottle, solid |
| diaper_count | INT | Nullable |
| diaper_type | VARCHAR | wet, dirty, both |
| sleep_time | TIME | Nullable |
| medication | VARCHAR | Nullable |
| notes | TEXT | Free-text diary from the voice entry |
| logged_by | UUID | FK → users |
| created_at | TIMESTAMP | |

> **Removed:** `cry_level` — too granular to log consistently. Use `notes` for this.

#### `dog_logs`
| Column | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| voice_entry_id | UUID | FK → voice_entries |
| log_date | DATE | |
| activity_type | ENUM | walk, feed, vet, grooming, medication |
| duration_min | INT | Nullable (for walks) |
| notes | TEXT | |
| done_by | UUID | FK → users |
| created_at | TIMESTAMP | |

#### `household_tasks`
| Column | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| voice_entry_id | UUID | FK → voice_entries (nullable) |
| title | VARCHAR | |
| description | TEXT | Nullable |
| assigned_to | UUID | FK → users (nullable) |
| due_date | DATE | Nullable |
| is_recurring | BOOLEAN | Default false |
| recurrence | VARCHAR | daily, weekly, biweekly, monthly |
| status | ENUM | pending, done, overdue |
| created_at | TIMESTAMP | |
| completed_at | TIMESTAMP | Nullable |

#### `calendar_events`
| Column | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| voice_entry_id | UUID | FK → voice_entries |
| category | ENUM | baby, dog, household |
| title | VARCHAR | |
| event_date | DATE | |
| event_time | TIME | Nullable |
| duration_min | INT | Default 60 |
| google_event_id | VARCHAR | Returned from Google Calendar API |
| notes | TEXT | Nullable |
| created_at | TIMESTAMP | |

#### `night_shifts`
| Column | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| shift_date | DATE | The night in question |
| on_duty | UUID | FK → users |
| notes | TEXT | Nullable |
| created_at | TIMESTAMP | |

---

## Feature Breakdown by Module

### Baby Module

| Feature | Description | Phase |
|---|---|---|
| Voice diary entries | Speak a summary of the night shift; stored as text + extracted stats | 1 |
| Structured data extraction | Auto-extract feeds, diapers, sleep stretches from voice input | 1 |
| Night shift tracker | "Who's on tonight?" toggle + last 7 nights history | **1** |
| Medication & vitamin log | Log what was given and when via voice | 2 |
| Doctor appointments | Voice → auto-create Google Calendar event | 2 |
| Milestone tracker | Track upcoming milestones (vaccines, checkups) | 3 |
| Trends dashboard | Charts: sleep patterns, feed frequency, diaper count over time | 3 |
| Pediatrician export | Export baby health data as a PDF summary | 4 |

### Dog Module

| Feature | Description | Phase |
|---|---|---|
| Walk log | Voice: "I just walked the dog" → logged with who & when | 1 |
| Feeding log | Track meals via voice | 1 |
| Vet appointments | Voice → Google Calendar event | 2 |
| Grooming & flea reminders | Recurring task with auto-reminders | 3 |
| Walk stats | Who walked more this week? Visual balance tracker | 3 |

### Household Module

| Feature | Description | Phase |
|---|---|---|
| Task board | Voice: "take the bins out tomorrow" → task created and assigned | 1 |
| Daily notes | Free-text voice notes (stored as voice_entry with type='note') | 1 |
| Recurring tasks | Auto-schedule weekly/monthly tasks (bins, filters, bills) | 2 |
| Task rotation | Auto-alternate assignments between partners | 2 |
| Appointment management | Voice → Google Calendar event | 2 |
| Overdue alerts | Visual indicator for missed/overdue tasks | 3 |

### Voice & Intelligence Layer

| Feature | Description | Phase |
|---|---|---|
| Mic button + audio capture | Browser MediaRecorder API → WebM/Opus → backend | 1 |
| Speaker toggle | Tap your name before speaking | 1 |
| Claude transcription + classification | Single API call: audio in, structured JSON out | 1 |
| Confirmation card | Show classified result before saving; user confirms or edits | 1 |
| Google Calendar auto-create | Event created on shared family calendar | 2 |
| Weekly AI summary | Claude generates a weekly household report | 3 |
| Natural language queries | "How many times did the baby wake last week?" | 4 |
| Speaker voice recognition | Auto-detect who is speaking (ML-based, stretch goal) | 4 |

---

## Phased Build Plan

### Phase 1 — Foundation (Weekend, 1-2 days)

**Goal:** Voice pipeline working end-to-end with basic UI.

1. Docker Compose with PostgreSQL
2. FastAPI app skeleton with `/static` mount and health check route
3. Alembic migrations: users, voice_entries, baby_logs, dog_logs, household_tasks, night_shifts
4. Seed two user rows (you and partner names)
5. `POST /api/voice`: receive audio file → send to Claude API with prompt → return classified JSON
6. HTML/JS frontend:
   - Speaker toggle (tap name before speaking)
   - Mic button (hold to record via MediaRecorder)
   - Confirmation card (shows transcription + classified data + Confirm / Edit buttons)
7. `POST /api/voice/confirm`: route confirmed entry to correct table via `entry_router.py`
8. Daily feed view: chronological list of today's entries (all categories)
9. Night shift widget: "On duty tonight" toggle + last 7 nights history

**Acceptance criteria:**
- [ ] Press mic, speak in Catalan/Spanish/English → see transcription
- [ ] Claude correctly classifies baby vs dog vs household
- [ ] Confirmation card shows before anything is saved
- [ ] Baby diary entry: feeds, diapers, sleep extracted and stored in baby_logs
- [ ] Dog walk logged in dog_logs
- [ ] Household task created in household_tasks
- [ ] Daily feed shows all entries chronologically
- [ ] Night shift toggle works and shows history

---

### Phase 2 — Calendar & Core Features (Week 1)

**Goal:** Google Calendar integration and essential tracking features.

1. Google Calendar API setup (OAuth2, one shared family calendar)
2. Auto-create events when Claude returns `create_calendar_event`
3. Recurring task system (define frequency, auto-schedule next occurrence)
4. Task rotation logic (alternate between partners)
5. Medication/vitamin logging for baby
6. "Today" and "This week" dashboard views (tasks, appointments, recent logs)

**Acceptance criteria:**
- [ ] Say "doctor appointment Thursday at 10" → event appears in shared Google Calendar
- [ ] Recurring tasks auto-appear on the right days
- [ ] Dashboard shows today's tasks, appointments, and logs

---

### Phase 3 — Analytics & Intelligence (Week 2)

1. Baby sleep/feed trends dashboard (charts, last 30 days)
2. Dog walk balance tracker (who walked more this week)
3. Overdue task indicators
4. Weekly AI summary (Claude generates a report from the week's data)
5. Baby milestone tracker (configurable: next vaccines, checkups)
6. Grooming/flea treatment reminders for dog
7. UI polish: color-coded categories, cleaner layout

---

### Phase 4 — Advanced (Week 3+)

1. Natural language queries ("how many times did the baby wake up last week?")
2. Pediatrician PDF export (baby health data summary)
3. Email or Telegram notifications for upcoming tasks
4. Mobile-responsive design (or begin React migration)
5. Speaker voice recognition (stretch goal)
6. Data backup and export

---

## Project Structure

```
homebase/
├── CLAUDE.md                     # Claude Code project memory
├── homebase_plan.md              # This file
├── requirements.txt              # Python dependencies
├── .env                          # ANTHROPIC_API_KEY, GOOGLE_CALENDAR_ID, DB_URL
├── docker-compose.yml            # PostgreSQL only
│
├── app/
│   ├── main.py                   # FastAPI entry point + mounts /static
│   ├── config.py                 # Settings from env vars
│   │
│   ├── api/
│   │   └── routes/
│   │       ├── voice.py          # POST /api/voice + POST /api/voice/confirm
│   │       ├── baby.py           # Baby logs CRUD + stats
│   │       ├── dog.py            # Dog logs CRUD
│   │       ├── household.py      # Tasks CRUD
│   │       ├── shifts.py         # Night shift tracker
│   │       └── calendar.py       # Phase 2: Google Calendar sync
│   │
│   ├── models/                   # SQLAlchemy models (one file per table)
│   │   ├── user.py
│   │   ├── voice_entry.py
│   │   ├── baby_log.py
│   │   ├── dog_log.py
│   │   ├── household_task.py
│   │   ├── calendar_event.py
│   │   └── night_shift.py
│   │
│   ├── services/
│   │   ├── claude_voice.py       # Send audio to Claude API, parse JSON response
│   │   ├── entry_router.py       # Route confirmed voice entry to correct table
│   │   ├── calendar_sync.py      # Phase 2: Google Calendar integration
│   │   └── analytics.py          # Phase 3: trends and summaries
│   │
│   └── db/
│       ├── database.py           # SQLAlchemy engine + session factory
│       └── migrations/           # Alembic migration files
│
├── static/
│   ├── index.html                # Single-page app shell
│   ├── app.js                    # MediaRecorder, API calls, confirmation card UI
│   └── style.css                 # Minimal styling
│
└── tests/
    ├── test_claude_voice.py      # Mock audio → assert JSON structure
    └── test_entry_router.py      # Assert entries routed to correct tables
```

---

## API Keys & Services Required

| Service | Purpose | When |
|---|---|---|
| Anthropic API | Audio transcription + classification | Phase 1 |
| Google Calendar API | Event creation on shared family calendar | Phase 2 |

---

## CLAUDE.md (Copy to project root)

```markdown
# HomeBase — Voice-First Family Command Center

## About This Project
Voice-first web app for household coordination between two parents with a newborn baby and a dog.
Users speak in Catalan, Spanish, or English. The app transcribes + classifies input via Claude API
(one call handles both), shows a confirmation card, then stores to DB and optionally creates
a Google Calendar event.

## Tech Stack
- Backend: Python 3.11+, FastAPI
- Frontend: Plain HTML/JS served as static files from FastAPI
- Database: PostgreSQL with SQLAlchemy ORM + Alembic migrations
- AI: Anthropic Claude API (claude-sonnet-4-6) — handles audio transcription AND classification
- Calendar: Google Calendar API (Phase 2, shared family calendar)

## Key Directories
- app/api/routes/ — FastAPI route handlers
- app/models/ — SQLAlchemy database models
- app/services/ — Business logic (claude_voice, entry_router, calendar_sync, analytics)
- app/db/ — Database connection and Alembic migrations
- static/ — HTML/JS/CSS frontend

## Voice Pipeline Flow
Audio (WebM/Opus) → POST /api/voice → Claude API (audio input: transcription + classification)
→ confirmation card shown to user → POST /api/voice/confirm → entry_router.py writes to
correct table (baby_logs / dog_logs / household_tasks / calendar_events)

## Standards
- Type hints required on all functions
- pytest for testing
- PEP 8 with 100 character line limit
- All database changes via Alembic migrations
- Environment variables for all API keys (never hardcoded)

## Common Commands
- docker compose up -d                  # Start PostgreSQL
- uvicorn app.main:app --reload         # Start API server (also serves frontend)
- alembic upgrade head                  # Run migrations
- pytest tests/ -v                      # Run tests

## Important Notes
- Voice supports 3 languages: Catalan (ca), Spanish (es), English (en)
- Claude API receives raw audio and returns transcription + classification in ONE call
- ALL entries require user confirmation before being written to DB
- Calendar events go to ONE shared family Google Calendar (Phase 2)
- night_shifts table tracks "who's on tonight" — Phase 1 essential
- No daily_notes table: notes are voice_entries with type='note'
```

---

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Claude audio accuracy for Catalan | Test early with real recordings; prompt includes language context |
| Claude misclassification | Confirmation card before every save — user always reviews result |
| Google Calendar OAuth complexity | Single shared calendar = one token; much simpler than per-account OAuth |
| MediaRecorder browser compatibility | WebM/Opus works on Chrome/Firefox/Edge; test early on target devices |
| Phase 1 scope creep | Voice pipeline + confirmation + daily feed + night shift ONLY. Nothing else. |
| Wife adoption | One big mic button, one tap to confirm, speaker toggle is the only extra step |
| Audio privacy (baby data) | All processing via Anthropic API (not stored by Anthropic per policy). Self-host DB. |
