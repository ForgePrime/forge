import enum

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.database import Base


class UserRole(str, enum.Enum):
    operator = "operator"
    manager = "manager"
    director = "director"


class User(Base):
    __tablename__ = "users"

    id = sa.Column(sa.Integer, primary_key=True, index=True)
    email = sa.Column(sa.String(200), unique=True, nullable=False, index=True)
    password_hash = sa.Column(sa.String(255), nullable=False)
    role = sa.Column(
        postgresql.ENUM("operator", "manager", "director", name="user_role", create_type=False),
        nullable=False,
    )
    warehouse_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=True,
    )
