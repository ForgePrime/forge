from sqlalchemy import String, Text, Integer, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class Guideline(Base, TimestampMixin):
    __tablename__ = "guidelines"
    __table_args__ = (
        CheckConstraint("weight IN ('must', 'should', 'may')", name="valid_weight"),
        CheckConstraint("status IN ('ACTIVE', 'DEPRECATED')", name="valid_guideline_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"))
    external_id: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    scope: Mapped[str] = mapped_column(String(50), nullable=False, server_default="general")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text)
    weight: Mapped[str] = mapped_column(String(10), nullable=False, server_default="should")
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="ACTIVE")
    examples: Mapped[list[str] | None] = mapped_column(ARRAY(String))

    project: Mapped["Project | None"] = relationship(back_populates="guidelines")
