import pytest
from fastapi import HTTPException
from sqlalchemy import text

from app.auth.models import User, UserRole
from app.stock.permissions import assert_write_access, get_visible_warehouse_ids


@pytest.fixture
def warehouses(db_session):
    """Insert three warehouses and return their IDs in order."""
    ids = []
    for i in range(1, 4):
        wid = db_session.execute(
            text(
                "INSERT INTO warehouses (name, city) VALUES (:name, :city) RETURNING id"
            ),
            {"name": f"Magazyn {i}", "city": f"Miasto {i}"},
        ).scalar_one()
        ids.append(wid)
    return ids


def _user(role: UserRole, warehouse_id: int | None = None) -> User:
    u = User()
    u.role = role
    u.warehouse_id = warehouse_id
    return u


# ---------------------------------------------------------------------------
# AC-0: operator sees only own warehouse
# ---------------------------------------------------------------------------

def test_operator_visible_warehouses_only_own(db_session, warehouses):
    """Operator with warehouse_id equal to warehouses[1] sees only that id."""
    own_id = warehouses[1]  # middle warehouse — not first, not last
    user = _user(UserRole.operator, warehouse_id=own_id)

    result = get_visible_warehouse_ids(user, db_session)

    assert result == [own_id], (
        f"Operator must see exactly [own_id], got {result}"
    )
    for other_id in (warehouses[0], warehouses[2]):
        assert other_id not in result, (
            f"Operator must NOT see warehouse {other_id}"
        )


# ---------------------------------------------------------------------------
# AC-1: manager and director see all warehouses
# ---------------------------------------------------------------------------

def test_manager_director_see_all_warehouse_ids(db_session, warehouses):
    """Manager and director both get all warehouse IDs from the database."""
    for role in (UserRole.manager, UserRole.director):
        user = _user(role, warehouse_id=warehouses[0])
        result = get_visible_warehouse_ids(user, db_session)

        assert sorted(result) == sorted(warehouses), (
            f"{role} should see all warehouse ids {warehouses}, got {result}"
        )


# ---------------------------------------------------------------------------
# AC-2: operator cannot write to a foreign warehouse
# ---------------------------------------------------------------------------

def test_operator_write_to_foreign_warehouse_raises_403(db_session, warehouses):
    """Operator with warehouse_id=warehouses[0] writing to warehouses[1] → 403."""
    user = _user(UserRole.operator, warehouse_id=warehouses[0])

    with pytest.raises(HTTPException) as exc_info:
        assert_write_access(user, warehouses[1])

    assert exc_info.value.status_code == 403


def test_operator_write_to_own_warehouse_is_allowed(db_session, warehouses):
    """Operator writing to own warehouse_id must NOT raise."""
    user = _user(UserRole.operator, warehouse_id=warehouses[0])
    assert_write_access(user, warehouses[0])  # no exception


def test_manager_write_to_own_warehouse_is_allowed(db_session, warehouses):
    """Manager writing to own warehouse_id must NOT raise."""
    user = _user(UserRole.manager, warehouse_id=warehouses[0])
    assert_write_access(user, warehouses[0])  # no exception


def test_manager_write_to_foreign_warehouse_raises_403(db_session, warehouses):
    """Manager with warehouse_id=warehouses[0] writing to warehouses[1] → 403."""
    user = _user(UserRole.manager, warehouse_id=warehouses[0])

    with pytest.raises(HTTPException) as exc_info:
        assert_write_access(user, warehouses[1])

    assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# AC-3: director never has write access
# ---------------------------------------------------------------------------

def test_director_write_raises_403(db_session, warehouses):
    """Director raises 403 regardless of which warehouse is targeted."""
    user = _user(UserRole.director, warehouse_id=warehouses[0])

    for wid in warehouses:
        with pytest.raises(HTTPException) as exc_info:
            assert_write_access(user, wid)
        assert exc_info.value.status_code == 403, (
            f"Director must be denied write to warehouse {wid}"
        )
