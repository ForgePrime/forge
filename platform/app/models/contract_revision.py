"""Contract revision history (mockup 12)."""
import datetime as dt

from sqlalchemy import Text, ForeignKey, DateTime, func, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ContractRevision(Base):
    __tablename__ = "contract_revisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"),
                                             nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content_md: Mapped[str] = mapped_column(Text, nullable=False)
    saved_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    saved_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False,
                                                   server_default=func.now())
    note: Mapped[str | None] = mapped_column(Text)
