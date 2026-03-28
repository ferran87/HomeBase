import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.routes import voice, baby, dog, household, shifts, calendar, users
from app.config import settings
from app.db.database import engine, SessionLocal
from app.models.base import Base
from app.models.user import User


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.database_url.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)
    _seed_users_if_empty()
    yield


def _seed_users_if_empty() -> None:
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            db.add_all([
                User(id=uuid.uuid4(), name="Ferran"),
                User(id=uuid.uuid4(), name="Marta"),
            ])
            db.commit()
    finally:
        db.close()


app = FastAPI(title="HomeBase", version="0.1.0", lifespan=lifespan)

app.include_router(voice.router, prefix="/api/voice", tags=["voice"])
app.include_router(baby.router, prefix="/api/baby", tags=["baby"])
app.include_router(dog.router, prefix="/api/dog", tags=["dog"])
app.include_router(household.router, prefix="/api/household", tags=["household"])
app.include_router(shifts.router, prefix="/api/shifts", tags=["shifts"])
app.include_router(calendar.router, prefix="/api/calendar", tags=["calendar"])
app.include_router(users.router, prefix="/api/users", tags=["users"])

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def serve_frontend() -> FileResponse:
    return FileResponse("static/index.html")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
