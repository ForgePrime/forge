import datetime as dt

from sqlalchemy import String, Text, Integer, ForeignKey, DateTime, CheckConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class Execution(Base, TimestampMixin):
    __tablename__ = "executions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PROMPT_ASSEMBLED', 'IN_PROGRESS', 'DELIVERED', 'VALIDATING', "
            "'ACCEPTED', 'REJECTED', 'EXPIRED', 'FAILED')",
            name="valid_execution_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    agent: Mapped[str] = mapped_column(String(100), nullable=False, server_default="default")
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="PROMPT_ASSEMBLED")
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    # E1 — execution mode: 'direct' (parser→LLM) or 'crafted' (parser→crafter→executor)
    mode: Mapped[str | None] = mapped_column(String(16))  # direct | crafted
    # For crafted mode: which LLMCall produced the detailed prompt
    crafter_call_id: Mapped[int | None] = mapped_column(ForeignKey("llm_calls.id"))

    # Prompt (what AI received)
    prompt_text: Mapped[str | None] = mapped_column(Text)
    prompt_hash: Mapped[str | None] = mapped_column(String(80))
    prompt_meta: Mapped[dict | None] = mapped_column(JSONB)

    # Contract (what AI must return)
    contract: Mapped[dict | None] = mapped_column(JSONB)
    contract_version: Mapped[int | None] = mapped_column(Integer)

    # Delivery (what AI returned)
    delivery: Mapped[dict | None] = mapped_column(JSONB)
    delivered_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    # Validation (result of checking delivery vs contract)
    validation_result: Mapped[dict | None] = mapped_column(JSONB)
    validated_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    # Lease
    lease_expires_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    lease_renewals: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)

    # Lifecycle
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    # Relations
    task: Mapped["Task"] = relationship(back_populates="executions")
    prompt_sections: Mapped[list["PromptSection"]] = relationship(
        back_populates="execution", cascade="all, delete-orphan", order_by="PromptSection.position"
    )
    prompt_elements: Mapped[list["PromptElement"]] = relationship(
        back_populates="execution", cascade="all, delete-orphan"
    )


class PromptSection(Base):
    __tablename__ = "prompt_sections"

    id: Mapped[int] = mapped_column(primary_key=True)
    execution_id: Mapped[int] = mapped_column(ForeignKey("executions.id", ondelete="CASCADE"), nullable=False)
    section_name: Mapped[str] = mapped_column(String(50), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    included: Mapped[bool] = mapped_column(default=True, nullable=False)
    exclusion_reason: Mapped[str | None] = mapped_column(Text)
    rendered_text: Mapped[str | None] = mapped_column(Text)
    char_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    element_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)

    execution: Mapped["Execution"] = relationship(back_populates="prompt_sections")


class PromptElement(Base):
    __tablename__ = "prompt_elements"

    id: Mapped[int] = mapped_column(primary_key=True)
    execution_id: Mapped[int] = mapped_column(ForeignKey("executions.id", ondelete="CASCADE"), nullable=False)
    section_id: Mapped[int | None] = mapped_column(ForeignKey("prompt_sections.id", ondelete="CASCADE"))

    source_table: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[int | None] = mapped_column(Integer)
    source_external_id: Mapped[str | None] = mapped_column(String(30))
    source_version: Mapped[int | None] = mapped_column(Integer)
    content_snapshot: Mapped[str] = mapped_column(Text, nullable=False)

    included: Mapped[bool] = mapped_column(default=True, nullable=False)
    selection_reason: Mapped[str | None] = mapped_column(Text)
    exclusion_reason: Mapped[str | None] = mapped_column(Text)
    scope_details: Mapped[dict | None] = mapped_column(JSONB)
    budget_details: Mapped[dict | None] = mapped_column(JSONB)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)

    execution: Mapped["Execution"] = relationship(back_populates="prompt_elements")
