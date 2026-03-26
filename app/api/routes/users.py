from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.user import User

router = APIRouter()


@router.get("/")
async def list_users(db: Session = Depends(get_db)) -> list[dict]:
    """Return all users (the two parents)."""
    users = db.query(User).order_by(User.created_at).all()
    return [{"id": str(u.id), "name": u.name, "email": u.email} for u in users]
