import uuid
from datetime import datetime, date

from sqlalchemy import Date, Text, String, Boolean, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

TASK_STATUS = SAEnum("pending", "done", "overdue", name="task_status_enum", native_enum=True)


class HouseholdTask(Base):
    __tablename__ = "household_tasks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    voice_entry_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("voice_entries.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    recurrence: Mapped[str | None] = mapped_column(String(20), nullable=True)  # daily, weekly, biweekly, monthly
    status: Mapped[str] = mapped_column(TASK_STATUS, default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    voice_entry: Mapped["VoiceEntry | None"] = relationship(back_populates="household_task")  # noqa: F821
