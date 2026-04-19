"""P3.4 — per-objective KB scoping + P3.5 — last_read_at."""
import datetime as dt

import pytest

from app.database import SessionLocal
from app.models import Knowledge, Objective, Project
from app.services.kb_scope import resolve_scoped_kb_ids, mark_read
from tests.conftest_populated import build_populated_project

BASE = "http://127.0.0.1:8063"


@pytest.fixture(scope="module")
def ps():
    return build_populated_project(prefix="p3kb")


def _seed_kb(db, project_id: int, ext: str, title: str = "src") -> Knowledge:
    k = Knowledge(
        project_id=project_id, external_id=ext, title=title,
        category="source-document", content="x" * 50, status="ACTIVE",
    )
    db.add(k); db.commit(); db.refresh(k)
    return k


# ---- Resolver --------------------------------------------------

def test_resolve_returns_none_when_no_kb_focus(ps):
    _s, slug = ps
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        obj = db.query(Objective).filter(Objective.project_id == proj.id).first()
        obj.kb_focus_ids = None
        db.commit()
        assert resolve_scoped_kb_ids(db, obj.id) is None
    finally:
        db.close()


def test_resolve_returns_unique_int_list_when_focused(ps):
    _s, slug = ps
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        obj = db.query(Objective).filter(Objective.project_id == proj.id).first()
        # Set with duplicates + bogus to test cleanup
        obj.kb_focus_ids = [11, 22, 11, None, 22, 33]  # type: ignore
        db.commit()
        ids = resolve_scoped_kb_ids(db, obj.id)
        assert ids == [11, 22, 33]
    finally:
        db.close()


def test_resolve_unknown_objective_returns_none(ps):
    db = SessionLocal()
    try:
        assert resolve_scoped_kb_ids(db, 999_999_999) is None
    finally:
        db.close()


# ---- mark_read --------------------------------------------------

def test_mark_read_updates_timestamp(ps):
    _s, slug = ps
    db = SessionLocal()
    kid = None
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        ts = int(dt.datetime.now().timestamp()) % 100000
        k = _seed_kb(db, proj.id, ext=f"SRC-LR-{ts}")
        kid = k.id
        before = k.last_read_at
        n = mark_read(db, [k.id])
        db.refresh(k)
        assert n == 1
        assert k.last_read_at is not None
        assert before is None or k.last_read_at >= before
    finally:
        if kid:
            db.query(Knowledge).filter(Knowledge.id == kid).delete()
            db.commit()
        db.close()


def test_mark_read_handles_empty_list(ps):
    db = SessionLocal()
    try:
        assert mark_read(db, []) == 0
    finally:
        db.close()


def test_mark_read_dedupes_ids(ps):
    """Calling mark_read([1,1,2,2,2]) should not double-update; row count == unique ids that exist."""
    _s, slug = ps
    db = SessionLocal()
    kids = []
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        ts = int(dt.datetime.now().timestamp()) % 100000
        a = _seed_kb(db, proj.id, ext=f"SRC-DEDUP-A-{ts}")
        b = _seed_kb(db, proj.id, ext=f"SRC-DEDUP-B-{ts}")
        kids = [a.id, b.id]
        n = mark_read(db, [a.id, a.id, b.id, b.id, b.id])
        assert n == 2
    finally:
        if kids:
            db.query(Knowledge).filter(Knowledge.id.in_(kids)).delete(synchronize_session=False)
            db.commit()
        db.close()


# ---- API endpoints ----------------------------------------------

def test_set_kb_focus_endpoint_round_trip(ps):
    s, slug = ps
    db = SessionLocal()
    kids = []
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        ts = int(dt.datetime.now().timestamp()) % 100000
        a = _seed_kb(db, proj.id, ext=f"SRC-FOC-A-{ts}")
        b = _seed_kb(db, proj.id, ext=f"SRC-FOC-B-{ts}")
        kids = [a.id, b.id]
        obj = db.query(Objective).filter(Objective.project_id == proj.id).first()
        obj_ext = obj.external_id
        a_ext, b_ext = a.external_id, b.external_id
    finally:
        db.close()

    r = s.put(f"{BASE}/api/v1/tier1/projects/{slug}/objectives/{obj_ext}/kb-focus",
              json={"knowledge_external_ids": [a_ext, b_ext]})
    assert r.status_code == 200
    assert r.json()["count"] == 2

    g = s.get(f"{BASE}/api/v1/tier1/projects/{slug}/objectives/{obj_ext}/kb-focus")
    assert g.status_code == 200
    j = g.json()
    assert j["scoped"] is True
    ext_ids = sorted(src["external_id"] for src in j["sources"])
    assert ext_ids == sorted([a_ext, b_ext])

    # Empty list → unscoped
    r2 = s.put(f"{BASE}/api/v1/tier1/projects/{slug}/objectives/{obj_ext}/kb-focus",
               json={"knowledge_external_ids": []})
    assert r2.status_code == 200
    g2 = s.get(f"{BASE}/api/v1/tier1/projects/{slug}/objectives/{obj_ext}/kb-focus")
    assert g2.json()["scoped"] is False

    db = SessionLocal()
    try:
        db.query(Knowledge).filter(Knowledge.id.in_(kids)).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def test_set_kb_focus_silently_drops_unknown_external_ids(ps):
    s, slug = ps
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        obj = db.query(Objective).filter(Objective.project_id == proj.id).first()
        obj_ext = obj.external_id
    finally:
        db.close()
    r = s.put(f"{BASE}/api/v1/tier1/projects/{slug}/objectives/{obj_ext}/kb-focus",
              json={"knowledge_external_ids": ["SRC-does-not-exist"]})
    assert r.status_code == 200
    assert r.json()["count"] == 0


def test_kb_list_endpoint_includes_last_read_at(ps):
    s, slug = ps
    db = SessionLocal()
    kid = None
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        ts = int(dt.datetime.now().timestamp()) % 100000
        k = _seed_kb(db, proj.id, ext=f"SRC-LR-API-{ts}")
        kid = k.id
        mark_read(db, [k.id])
    finally:
        db.close()

    r = s.get(f"{BASE}/api/v1/projects/{slug}/knowledge")
    assert r.status_code == 200
    items = r.json()
    ours = [i for i in items if i["id"] == kid]
    assert ours
    assert ours[0]["last_read_at"] is not None

    db = SessionLocal()
    try:
        db.query(Knowledge).filter(Knowledge.id == kid).delete()
        db.commit()
    finally:
        db.close()
