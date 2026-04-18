import datetime as dt

from sqlalchemy import String, Text, Integer, Float, DateTime, CheckConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Organization(Base):
    """Tenant root — every project belongs to exactly one organization.

    anthropic_api_key_encrypted: BYO (bring-your-own) Anthropic key per tenant,
    AES-GCM encrypted with FORGE_ENCRYPTION_KEY. Null means "not set" — orchestrate
    will error out until admin sets it. Design: klient płaci Anthropic directly,
    zero platform pass-through revenue on LLM (Phase 1 decision Q12).

    budget_usd_monthly: soft limit. Hard stop enforced by middleware before LLM call.
    """
    __tablename__ = "organizations"
    __table_args__ = (
        CheckConstraint(
            "plan IN ('pilot','starter','growth','enterprise')",
            name="valid_org_plan",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    anthropic_api_key_encrypted: Mapped[str | None] = mapped_column(Text)
    budget_usd_monthly: Mapped[float | None] = mapped_column(Float)
    plan: Mapped[str] = mapped_column(String(32), nullable=False, server_default="pilot")
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    memberships: Mapped[list["Membership"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    projects: Mapped[list["Project"]] = relationship(back_populates="organization")
