import uuid
from datetime import datetime, date, timezone

from sqlalchemy import Date, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class NightShift(Base):
    __tablename__ = "night_shifts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    shift_date: Mapped[date] = mapped_column(Date, nullable=False)
    on_duty: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    on_duty_user: Mapped["User"] = relationship(back_populates="night_shifts")  # noqa: F821
