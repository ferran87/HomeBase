from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.household_task import HouseholdTask

router = APIRouter()


@router.get("/tasks")
async def get_tasks(
    status: str | None = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    """Return household tasks, optionally filtered by status."""
    query = db.query(HouseholdTask)
    if status:
        query = query.filter(HouseholdTask.status == status)
    tasks = query.order_by(HouseholdTask.created_at.desc()).all()
    return [
        {
            "id": str(t.id),
            "title": t.title,
            "description": t.description,
            "assigned_to": str(t.assigned_to) if t.assigned_to else None,
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "is_recurring": t.is_recurring,
            "recurrence": t.recurrence,
            "status": t.status,
            "created_at": t.created_at.isoformat(),
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
        }
        for t in tasks
    ]


@router.patch("/tasks/{task_id}/done")
async def mark_task_done(task_id: str, db: Session = Depends(get_db)) -> dict:
    """Mark a task as done."""
    import uuid
    from datetime import datetime, timezone

    task = db.get(HouseholdTask, uuid.UUID(task_id))
    if not task:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = "done"
    task.completed_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "done", "task_id": task_id}
