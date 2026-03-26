from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.routes import voice, baby, dog, household, shifts, calendar, users

app = FastAPI(title="HomeBase", version="0.1.0")

# Routers
app.include_router(voice.router, prefix="/api/voice", tags=["voice"])
app.include_router(baby.router, prefix="/api/baby", tags=["baby"])
app.include_router(dog.router, prefix="/api/dog", tags=["dog"])
app.include_router(household.router, prefix="/api/household", tags=["household"])
app.include_router(shifts.router, prefix="/api/shifts", tags=["shifts"])
app.include_router(calendar.router, prefix="/api/calendar", tags=["calendar"])
app.include_router(users.router, prefix="/api/users", tags=["users"])

# Serve frontend
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def serve_frontend() -> FileResponse:
    return FileResponse("static/index.html")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
