import uuid
from datetime import datetime, date

from sqlalchemy import Date, Text, Integer, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

DOG_ACTIVITY = SAEnum(
    "walk", "feed", "vet", "grooming", "medication",
    name="dog_activity_enum", native_enum=True,
)


class DogLog(Base):
    __tablename__ = "dog_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    voice_entry_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("voice_entries.id"), nullable=False)
    log_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    activity_type: Mapped[str] = mapped_column(DOG_ACTIVITY, nullable=False)
    duration_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    done_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    voice_entry: Mapped["VoiceEntry"] = relationship(back_populates="dog_log")  # noqa: F821
