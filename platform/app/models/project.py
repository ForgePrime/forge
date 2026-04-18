from sqlalchemy import String, Text, Integer, ForeignKey, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id", ondelete="RESTRICT"), index=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    goal: Mapped[str | None] = mapped_column(Text)
    config: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"), nullable=False)

    organization: Mapped["Organization | None"] = relationship(back_populates="projects")
    tasks: Mapped[list["Task"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    guidelines: Mapped[list["Guideline"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    micro_skills: Mapped[list["MicroSkill"]] = relationship(back_populates="project")
    decisions: Mapped[list["Decision"]] = relationship(back_populates="project", cascade="all, delete-orphan")
