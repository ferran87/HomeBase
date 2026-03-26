import uuid
from datetime import datetime

from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

CATEGORY = SAEnum("baby", "dog", "household", name="category_enum", native_enum=True)
ENTRY_TYPE = SAEnum(
    "diary_entry", "calendar_event", "task", "reminder", "note",
    name="entry_type_enum", native_enum=True,
)


class VoiceEntry(Base):
    __tablename__ = "voice_entries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    speaker_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    category: Mapped[str] = mapped_column(CATEGORY, nullable=False)
    entry_type: Mapped[str] = mapped_column(ENTRY_TYPE, nullable=False)
    raw_transcription: Mapped[str] = mapped_column(Text, nullable=False)
    language_detected: Mapped[str] = mapped_column(String(5), nullable=True)
    extracted_data: Mapped[dict] = mapped_column(JSONB, nullable=True)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    speaker: Mapped["User"] = relationship(back_populates="voice_entries")  # noqa: F821
    baby_log: Mapped["BabyLog | None"] = relationship(back_populates="voice_entry")  # noqa: F821
    dog_log: Mapped["DogLog | None"] = relationship(back_populates="voice_entry")  # noqa: F821
    household_task: Mapped["HouseholdTask | None"] = relationship(back_populates="voice_entry")  # noqa: F821
    calendar_event: Mapped["CalendarEvent | None"] = relationship(back_populates="voice_entry")  # noqa: F821
