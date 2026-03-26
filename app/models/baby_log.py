import uuid
from datetime import datetime, date, time

from sqlalchemy import Date, Time, Text, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class BabyLog(Base):
    __tablename__ = "baby_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    voice_entry_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("voice_entries.id"), nullable=False)
    log_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    wake_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    feed_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    feed_type: Mapped[str | None] = mapped_column(String(20), nullable=True)  # breast, bottle, solid
    diaper_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    diaper_type: Mapped[str | None] = mapped_column(String(20), nullable=True)  # wet, dirty, both
    sleep_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    medication: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    logged_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    voice_entry: Mapped["VoiceEntry"] = relationship(back_populates="baby_log")  # noqa: F821
