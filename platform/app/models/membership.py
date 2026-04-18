import datetime as dt

from sqlalchemy import String, Integer, ForeignKey, DateTime, CheckConstraint, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Membership(Base):
    """User ↔ Organization link with role.

    Roles:
    - owner: full control (billing, invite, delete projects)
    - editor: create/edit projects, run orchestrate
    - viewer: read-only (for audit/PM share)
    """
    __tablename__ = "memberships"
    __table_args__ = (
        CheckConstraint(
            "role IN ('owner','editor','viewer')",
            name="valid_membership_role",
        ),
        UniqueConstraint("user_id", "organization_id", name="uq_user_org"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="memberships")
    organization: Mapped["Organization"] = relationship(back_populates="memberships")
