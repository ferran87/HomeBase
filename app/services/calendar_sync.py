"""
Phase 2: Google Calendar integration.

Creates events on the shared family Google Calendar when Claude classifies
a voice input as a calendar_event.

OAuth2 setup:
1. Create a project in Google Cloud Console
2. Enable Google Calendar API
3. Download credentials.json (OAuth2 desktop client)
4. On first run, authenticate → token.json is saved for subsequent calls
5. Set GOOGLE_CALENDAR_ID in .env
"""
# TODO Phase 2: implement Google Calendar sync
# from google.oauth2.credentials import Credentials
# from googleapiclient.discovery import build


def create_event(event_data: dict, calendar_id: str) -> str:
    """Create a Google Calendar event. Returns the google_event_id."""
    raise NotImplementedError("Google Calendar sync is a Phase 2 feature")
