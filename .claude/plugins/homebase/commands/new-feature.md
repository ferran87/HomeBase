---
description: Scaffold a new HomeBase feature module (route + model + service + migration reminder)
argument-hint: <feature-name>
allowed-tools: [Read, Write, Edit, Bash]
---

# /new-feature — Scaffold a New Feature

The user wants to add a new feature called: $ARGUMENTS

A HomeBase feature consists of three files + registration in `main.py`:

1. **`app/api/routes/<feature_name>.py`** — FastAPI router
2. **`app/models/<feature_name>.py`** — SQLAlchemy model
3. **`app/services/<feature_name>.py`** — Business logic

## Steps

### 1. Create the route file

```python
# app/api/routes/<feature_name>.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db

router = APIRouter()

@router.get("/")
async def list_items(db: Session = Depends(get_db)) -> list[dict]:
    return []
```

### 2. Create the model file

Follow the pattern in `app/models/baby_log.py`:
- Import `Base` from `app.models.base`
- Use `Mapped` + `mapped_column` (SQLAlchemy 2.0 style)
- UUID primary key with `default=uuid.uuid4`
- `created_at` timestamp

### 3. Create the service file

```python
# app/services/<feature_name>.py
"""
<Feature name> service.
"""
```

### 4. Register in `app/models/__init__.py`

Add the new model to the imports so Alembic autogenerate picks it up.

### 5. Register in `app/main.py`

```python
from app.api.routes import <feature_name>
app.include_router(<feature_name>.router, prefix="/api/<feature_name>", tags=["<feature_name>"])
```

### 6. Create migration

```bash
alembic revision --autogenerate -m "create_<feature_name>_table"
alembic upgrade head
```

### 7. Add tests

Create `tests/test_<feature_name>.py` following the pattern in `tests/test_entry_router.py`.
