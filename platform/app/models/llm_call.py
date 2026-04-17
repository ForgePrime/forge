import datetime as dt

from sqlalchemy import String, Text, Integer, Float, Boolean, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LLMCall(Base):
    """Records every invocation of Claude CLI (or any LLM).

    One execution may have multiple llm_calls (retries, challenge round).
    Captures full prompt/response + cost/tokens/duration for audit & debugging.
    """
    __tablename__ = "llm_calls"

    id: Mapped[int] = mapped_column(primary_key=True)
    execution_id: Mapped[int | None] = mapped_column(ForeignKey("executions.id", ondelete="SET NULL"))
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"))
    purpose: Mapped[str] = mapped_column(String(40), nullable=False)  # execute|analyze|ingest|challenge
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    model_used: Mapped[str | None] = mapped_column(String(100))
    session_id: Mapped[str | None] = mapped_column(String(64))

    prompt_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_chars: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt_preview: Mapped[str] = mapped_column(Text, nullable=False)
    full_prompt: Mapped[str | None] = mapped_column(Text)

    response_text: Mapped[str | None] = mapped_column(Text)
    response_chars: Mapped[int | None] = mapped_column(Integer)

    return_code: Mapped[int] = mapped_column(Integer, nullable=False)
    is_error: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    api_error_status: Mapped[str | None] = mapped_column(String(100))
    parse_error: Mapped[str | None] = mapped_column(Text)
    stderr_tail: Mapped[str | None] = mapped_column(Text)

    duration_ms: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[float | None] = mapped_column(Float)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    cache_read_tokens: Mapped[int | None] = mapped_column(Integer)

    workspace_dir: Mapped[str | None] = mapped_column(Text)
    delivery_parsed: Mapped[dict | None] = mapped_column(JSONB)
    cli_raw_meta: Mapped[dict | None] = mapped_column(JSONB)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
