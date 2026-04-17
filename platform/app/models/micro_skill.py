from sqlalchemy import String, Text, Integer, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class MicroSkill(Base, TimestampMixin):
    __tablename__ = "micro_skills"
    __table_args__ = (
        CheckConstraint("type IN ('reputation', 'technique', 'verification')", name="valid_skill_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"))
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    applicable_to: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), server_default="{}", nullable=False)
    relevance_score: Mapped[int] = mapped_column(Integer, server_default="50", nullable=False)

    project: Mapped["Project | None"] = relationship(back_populates="micro_skills")
