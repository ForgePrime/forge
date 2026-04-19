"""Skill library (F1) — reusable LLM capabilities + persona prompts.

Three categories:
  SKILL  — broad capability (e.g. "security review", "test scenario generator")
  MICRO  — narrow deterministic helper (e.g. "pytest parametrize wrapper")
  OPINION — persona prompt (e.g. "act as best senior Django developer")

Skills are scoped to:
  organization_id IS NULL  → global (built-in)
  organization_id IS NOT NULL → org-private

ProjectSkill join links a skill to a project with attach_mode (auto / manual / default).
"""
import datetime as dt

from sqlalchemy import String, Text, ForeignKey, CheckConstraint, DateTime, Boolean, func, Float, Integer
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Skill(Base):
    __tablename__ = "skills"
    __table_args__ = (
        CheckConstraint(
            "category IN ('SKILL', 'MICRO', 'OPINION')",
            name="valid_skill_category",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)  # e.g. SK-security-owasp
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), index=True)
    category: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    applies_to_phases: Mapped[list[str]] = mapped_column(
        ARRAY(String), server_default="{}", nullable=False
    )
    auto_attach_rule: Mapped[dict | None] = mapped_column(JSONB)
    cost_impact_usd: Mapped[float | None] = mapped_column(Float)
    # P5.8 — per-skill timeout hint for hook invocations. NULL → caller default.
    recommended_timeout_sec: Mapped[int | None] = mapped_column(Integer)
    is_built_in: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ProjectSkill(Base):
    __tablename__ = "project_skills"
    __table_args__ = (
        CheckConstraint(
            "attach_mode IN ('auto', 'manual', 'default')",
            name="valid_project_skill_attach",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), nullable=False)
    attach_mode: Mapped[str] = mapped_column(String(16), nullable=False, server_default="manual")
    invocations: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    last_used_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
