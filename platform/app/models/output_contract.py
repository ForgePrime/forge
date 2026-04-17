from sqlalchemy import String, Integer, Boolean, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class OutputContract(Base, TimestampMixin):
    __tablename__ = "output_contracts"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_type: Mapped[str] = mapped_column(String(20), nullable=False)
    ceremony_level: Mapped[str] = mapped_column(String(20), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    definition: Mapped[dict] = mapped_column(JSONB, nullable=False)
