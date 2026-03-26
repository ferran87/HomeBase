# HomeBase

Voice-first family command center for two parents with a newborn baby and a dog.

Speak in Catalan, Spanish, or English — HomeBase transcribes, classifies, and acts: logging baby night shifts, dog walks, and household tasks, or creating Google Calendar events.

## Quick Start

```bash
# 1. Copy env template and fill in your API keys
cp .env.example .env

# 2. Start PostgreSQL
docker compose up -d

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run database migrations
alembic upgrade head

# 5. Start the server (also serves the frontend)
uvicorn app.main:app --reload
```

Open http://localhost:8000 in your browser.

## Tech Stack

- **Backend:** Python 3.11+, FastAPI
- **Frontend:** Plain HTML/JS (served by FastAPI)
- **Database:** PostgreSQL + SQLAlchemy + Alembic
- **AI:** Anthropic Claude API — handles audio transcription AND classification in one call
- **Calendar:** Google Calendar API (Phase 2)

## Project Structure

```
app/
  api/routes/     — FastAPI route handlers
  models/         — SQLAlchemy database models
  services/       — Business logic (claude_voice, entry_router, analytics)
  db/             — Database connection + Alembic migrations
static/           — HTML/JS/CSS frontend
tests/            — pytest test suite
```

## Development

```bash
pytest tests/ -v              # Run tests
alembic revision --autogenerate -m "description"   # New migration
alembic upgrade head          # Apply migrations
```

See `homebase_plan.md` for the full project plan, data model, and phased build roadmap.
