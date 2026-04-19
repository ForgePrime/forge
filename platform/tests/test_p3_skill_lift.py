"""P3.2 — skill success-lift calculator + endpoint."""
import datetime as dt

import pytest

from app.database import SessionLocal
from app.models import Project, ProjectSkill, Skill, Task
from app.services.skill_lift import compute_project_skill_lifts
from tests.conftest_populated import build_populated_project

BASE = "http://127.0.0.1:8063"


@pytest.fixture(scope="module")
def ps():
    return build_populated_project(prefix="p3lift")


def _seed_skill(db, name: str = "lift-test") -> Skill:
    sk = Skill(
        external_id=f"SK-{name}-{int(dt.datetime.now().timestamp() * 1000)}",
        category="SKILL", name=name, prompt_text="x", applies_to_phases=[],
    )
    db.add(sk); db.commit(); db.refresh(sk)
    return sk


def _attach(db, project_id: int, skill_id: int, created_at: dt.datetime) -> ProjectSkill:
    ps = ProjectSkill(project_id=project_id, skill_id=skill_id, attach_mode="manual")
    db.add(ps); db.flush()
    # Override the server-set created_at for the test
    db.execute(
        ProjectSkill.__table__.update()
        .where(ProjectSkill.id == ps.id)
        .values(created_at=created_at)
    )
    db.commit(); db.refresh(ps)
    return ps


def _seed_task(db, project_id: int, status: str, completed_at: dt.datetime, ext: str) -> Task:
    t = Task(
        project_id=project_id, external_id=ext,
        name="lift-task", type="feature",
        description="seeded for lift test", instruction="do the thing",
        status=status,
        started_at=completed_at - dt.timedelta(seconds=10),
        completed_at=completed_at,
    )
    db.add(t); db.commit(); db.refresh(t)
    return t


def _cleanup(db, *ids_pairs):
    """ids_pairs: tuples like (Model, [ids])"""
    for model, ids in ids_pairs:
        db.query(model).filter(model.id.in_(ids)).delete(synchronize_session=False)
    db.commit()


def test_lift_returns_empty_when_no_attached_skills(ps):
    _s, slug = ps
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        # Wipe any pre-existing attached skills
        db.query(ProjectSkill).filter(ProjectSkill.project_id == proj.id).delete()
        db.commit()
        out = compute_project_skill_lifts(db, proj.id)
        assert out == []
    finally:
        db.close()


def test_lift_computes_pass_rate_before_and_after(ps):
    _s, slug = ps
    db = SessionLocal()
    task_ids = []
    skill_id = ps_id = None
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        # Clean slate
        db.query(ProjectSkill).filter(ProjectSkill.project_id == proj.id).delete()
        db.commit()

        cutoff = dt.datetime(2026, 4, 10, 12, 0, 0, tzinfo=dt.timezone.utc)
        # Before cutoff: 4 tasks, 1 DONE + 3 FAILED → 25% pass
        for i, st in enumerate(["DONE", "FAILED", "FAILED", "FAILED"], start=1):
            t = _seed_task(db, proj.id, st, cutoff - dt.timedelta(days=i),
                           f"T-LB-{i}-{int(dt.datetime.now().timestamp()*1000)}")
            task_ids.append(t.id)

        sk = _seed_skill(db, "lift-pre-post")
        skill_id = sk.id
        psk = _attach(db, proj.id, sk.id, cutoff)
        ps_id = psk.id

        # After cutoff: 4 tasks, 3 DONE + 1 FAILED → 75% pass
        for i, st in enumerate(["DONE", "DONE", "DONE", "FAILED"], start=1):
            t = _seed_task(db, proj.id, st, cutoff + dt.timedelta(days=i),
                           f"T-LA-{i}-{int(dt.datetime.now().timestamp()*1000)}")
            task_ids.append(t.id)

        out = compute_project_skill_lifts(db, proj.id)
        ours = [r for r in out if r["external_id"] == sk.external_id]
        assert len(ours) == 1
        row = ours[0]
        assert row["n_before"] == 4
        assert row["n_after"] == 4
        assert row["pass_rate_before"] == 25.0
        assert row["pass_rate_after"] == 75.0
        assert row["delta_pp"] == 50.0
    finally:
        if skill_id:
            db.query(ProjectSkill).filter(ProjectSkill.id == ps_id).delete()
            db.query(Skill).filter(Skill.id == skill_id).delete()
        db.query(Task).filter(Task.id.in_(task_ids)).delete(synchronize_session=False)
        db.commit()
        db.close()


def test_lift_handles_zero_before_or_after(ps):
    """When n_before or n_after is 0, the corresponding rate is None and delta is None."""
    _s, slug = ps
    db = SessionLocal()
    skill_id = ps_id = None
    task_ids = []
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        db.query(ProjectSkill).filter(ProjectSkill.project_id == proj.id).delete()
        db.commit()
        cutoff = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
        sk = _seed_skill(db, "lift-zero")
        skill_id = sk.id
        psk = _attach(db, proj.id, sk.id, cutoff)
        ps_id = psk.id
        # Only AFTER tasks
        for i, st in enumerate(["DONE", "DONE"], start=1):
            t = _seed_task(db, proj.id, st, cutoff + dt.timedelta(days=i),
                           f"T-Z-{i}-{int(dt.datetime.now().timestamp()*1000)}")
            task_ids.append(t.id)
        out = compute_project_skill_lifts(db, proj.id)
        ours = [r for r in out if r["external_id"] == sk.external_id][0]
        assert ours["n_before"] == 0
        assert ours["pass_rate_before"] is None
        assert ours["delta_pp"] is None
    finally:
        if ps_id:
            db.query(ProjectSkill).filter(ProjectSkill.id == ps_id).delete()
        if skill_id:
            db.query(Skill).filter(Skill.id == skill_id).delete()
        db.query(Task).filter(Task.id.in_(task_ids)).delete(synchronize_session=False)
        db.commit()
        db.close()


def test_lift_endpoint_returns_attached_skill_metrics(ps):
    s, slug = ps
    db = SessionLocal()
    skill_id = ps_id = None
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        db.query(ProjectSkill).filter(ProjectSkill.project_id == proj.id).delete()
        db.commit()
        sk = _seed_skill(db, "endpoint-lift")
        skill_id = sk.id
        psk = _attach(db, proj.id, sk.id, dt.datetime(2026, 4, 1, tzinfo=dt.timezone.utc))
        ps_id = psk.id
    finally:
        db.close()

    r = s.get(f"{BASE}/api/v1/skills/projects/{slug}/lift")
    assert r.status_code == 200
    j = r.json()
    assert "lifts" in j
    extids = [x["external_id"] for x in j["lifts"]]
    assert any("endpoint-lift" in x for x in extids)

    db = SessionLocal()
    try:
        if ps_id:
            db.query(ProjectSkill).filter(ProjectSkill.id == ps_id).delete()
        if skill_id:
            db.query(Skill).filter(Skill.id == skill_id).delete()
        db.commit()
    finally:
        db.close()
