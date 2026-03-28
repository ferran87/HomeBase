"""Seed the database with the two parent users (Ferran and Marta)."""
import uuid
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db.database import engine, SessionLocal
from app.models.user import User
from app.models.base import Base

PARENTS = [
    {"name": "Ferran", "email": ""},
    {"name": "Marta", "email": ""},
]


def seed_users(db: Session) -> None:
    existing = db.query(User).count()
    if existing > 0:
        print(f"Users table already has {existing} rows — skipping seed.")
        return

    for p in PARENTS:
        user = User(id=uuid.uuid4(), name=p["name"], email=p["email"] or None)
        db.add(user)
        print(f"  Created user: {user.name} ({user.id})")

    db.commit()
    print("Seed complete.")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_users(db)
    finally:
        db.close()
