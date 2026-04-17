from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.models import User, UserRole


def get_visible_warehouse_ids(user: User, db: Session) -> list[int]:
    if user.role == UserRole.operator:
        return [user.warehouse_id]
    rows = db.execute(text("SELECT id FROM warehouses ORDER BY id")).scalars().all()
    return list(rows)


def assert_write_access(user: User, target_warehouse_id: int) -> None:
    if user.role == UserRole.director:
        raise HTTPException(status_code=403, detail="Directors do not have write access")
    if user.warehouse_id != target_warehouse_id:
        raise HTTPException(status_code=403, detail="Access denied: warehouse not in scope")
