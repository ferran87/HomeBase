import uuid
from datetime import datetime, date, time

from sqlalchemy import Date, Time, Text, Integer, String, Boolean, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

EVENT_CATEGORY = SAEnum("baby", "dog", "household", name="event_category_enum", native_enum=True)


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    voice_entry_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("voice_entries.id"), nullable=False)
    category: Mapped[str] = mapped_column(EVENT_CATEGORY, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    event_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    duration_min: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    google_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    voice_entry: Mapped["VoiceEntry"] = relationship(back_populates="calendar_event")  # noqa: F821
