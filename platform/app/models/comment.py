import datetime as dt

from sqlalchemy import String, Text, Integer, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TaskComment(Base):
    """Free-form comment on a task by a user.

    Phase 2 minimum collab — no @mentions, no threading.
    """
    __tablename__ = "task_comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    user_email: Mapped[str | None] = mapped_column(String(320))  # snapshot in case user deleted
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
