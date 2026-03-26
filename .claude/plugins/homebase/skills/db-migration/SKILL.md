---
name: db-migration
description: Use this skill when adding new database tables or columns, modifying the schema, running alembic commands, or working with SQLAlchemy models in the app/models/ directory. Triggers on mentions of alembic, migration, schema change, new table, or adding a column.
version: 1.0.0
---

# HomeBase Database Migrations

HomeBase uses **Alembic** for schema migrations with **SQLAlchemy 2.0** mapped columns.

## Standard Workflow

```bash
# 1. Edit or create the model in app/models/
# 2. Generate the migration
alembic revision --autogenerate -m "add_medication_to_baby_logs"

# 3. Review the generated file in app/db/migrations/versions/
# 4. Apply
alembic upgrade head

# Roll back one step if needed
alembic downgrade -1
```

## Naming Conventions

| Change | Name format |
|---|---|
| New table | `create_<table>_table` |
| Add column | `add_<column>_to_<table>` |
| Add index | `add_index_on_<table>_<column>` |
| Rename | `rename_<old>_to_<new>_in_<table>` |

**Never delete a migration file.** Always create a new one.

## Model Pattern (SQLAlchemy 2.0)

All models inherit from `app.models.base.Base`. Use `Mapped` + `mapped_column`:

```python
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class MyModel(Base):
    __tablename__ = "my_table"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

## PostgreSQL ENUMs

Define ENUMs with `native_enum=True` so they're real Postgres types:

```python
from sqlalchemy import Enum as SAEnum

MY_STATUS = SAEnum("pending", "done", "overdue", name="my_status_enum", native_enum=True)

class MyModel(Base):
    status: Mapped[str] = mapped_column(MY_STATUS, default="pending", nullable=False)
```

Alembic autogenerate handles ENUM creation. If you rename an ENUM, you must write the `upgrade()` and `downgrade()` manually.

## Autogenerate Requirements

`app/db/migrations/env.py` imports all models via:
```python
from app.models import *  # noqa: F401, F403
```

**Any new model file must be added to `app/models/__init__.py`** or autogenerate won't detect it.

## JSONB Columns

For flexible structured data (like `voice_entries.extracted_data`):

```python
from sqlalchemy.dialects.postgresql import JSONB

extracted_data: Mapped[dict] = mapped_column(JSONB, nullable=True)
```

## Checking Migration State

```bash
alembic current          # show current revision applied to DB
alembic history          # list all migrations
alembic show <rev_id>    # show a specific migration
```

## Test DB

Tests use SQLite in-memory (`tests/conftest.py`). SQLite doesn't support native ENUMs — if tests fail with ENUM errors, check that models use `native_enum=True` (Alembic handles this; SQLite will fall back to VARCHAR automatically via SQLAlchemy).
