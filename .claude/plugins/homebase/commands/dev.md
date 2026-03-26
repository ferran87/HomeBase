---
description: Start the HomeBase development environment (PostgreSQL + FastAPI server)
allowed-tools: [Bash]
---

# /dev — Start HomeBase Dev Environment

Run these commands to start HomeBase locally:

```bash
# 1. Start PostgreSQL (detached)
docker compose up -d

# 2. Apply any pending migrations
alembic upgrade head

# 3. Start the FastAPI server (serves backend + frontend)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Then open http://localhost:8000 in your browser.

## Useful extras

```bash
# Check PostgreSQL logs
docker compose logs db

# Stop PostgreSQL
docker compose down

# Run tests (separate terminal)
pytest tests/ -v
```

Check the server is healthy: `curl http://localhost:8000/health`
