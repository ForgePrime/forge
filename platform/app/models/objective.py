from sqlalchemy import String, Text, Integer, ForeignKey, CheckConstraint, Boolean, Table, Column
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


# Objective DAG dependency (mockup 03v2). Acyclic enforced at application layer.
objective_dependencies = Table(
    "objective_dependencies",
    Base.metadata,
    Column("objective_id", Integer, ForeignKey("objectives.id", ondelete="CASCADE"), primary_key=True),
    Column("depends_on_id", Integer, ForeignKey("objectives.id", ondelete="CASCADE"), primary_key=True),
    CheckConstraint("objective_id != depends_on_id", name="no_self_dep_objective"),
)


class Objective(Base, TimestampMixin):
    __tablename__ = "objectives"
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT','ACTIVE','ACHIEVED','ABANDONED')",
            name="valid_objective_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    external_id: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    business_context: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="ACTIVE")
    scopes: Mapped[list[str]] = mapped_column(ARRAY(String), server_default="{}", nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, server_default="3")
    # I3 — watchlist opt-out: objective stays manual even at project autonomy L3+
    autonomy_optout: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    # Non-happy-path scenarios as first-class JSON (mockup 09 · 🧪 Test scenarios)
    # Each: {id, label, kind: edge_case|failure_mode|security|regression, description}
    test_scenarios: Mapped[list | None] = mapped_column(JSONB)
    # Challenger-will-verify list (mockup 09) — what the challenger must check per develop task
    challenger_checks: Mapped[list | None] = mapped_column(JSONB)
    # P3.4 — narrow KB to a specific subset of source IDs (per-objective focus)
    kb_focus_ids: Mapped[list[int] | None] = mapped_column(ARRAY(Integer))

    key_results: Mapped[list["KeyResult"]] = relationship(
        back_populates="objective", cascade="all, delete-orphan", order_by="KeyResult.position"
    )
    dependencies = relationship(
        "Objective",
        secondary=objective_dependencies,
        primaryjoin="Objective.id == objective_dependencies.c.objective_id",
        secondaryjoin="Objective.id == objective_dependencies.c.depends_on_id",
        backref="dependents",
    )


class KeyResult(Base, TimestampMixin):
    __tablename__ = "key_results"
    __table_args__ = (
        CheckConstraint(
            "kr_type IN ('numeric','descriptive')",
            name="valid_kr_type",
        ),
        CheckConstraint(
            "status IN ('NOT_STARTED','IN_PROGRESS','ACHIEVED','MISSED')",
            name="valid_kr_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    objective_id: Mapped[int] = mapped_column(ForeignKey("objectives.id", ondelete="CASCADE"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    kr_type: Mapped[str] = mapped_column(String(20), nullable=False, server_default="descriptive")
    target_value: Mapped[float | None] = mapped_column()
    current_value: Mapped[float | None] = mapped_column()
    measurement_command: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="NOT_STARTED")

    objective: Mapped["Objective"] = relationship(back_populates="key_results")
