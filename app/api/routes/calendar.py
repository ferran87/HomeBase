from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_events() -> dict:
    """Phase 2: Google Calendar integration — stub only."""
    return {"message": "Google Calendar integration coming in Phase 2"}
