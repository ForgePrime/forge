"""P2.2 — AC rows expose referenced test code inline.

Mockup 07 promised a ▸ caret next to each AC that reveals the actual test
source. We now surface the code via a JSON endpoint + a button in _ac_row.html.

These tests prove:
  1. Endpoint returns the full file when test_path has no symbol.
  2. Endpoint slices the function body when test_path is "file::symbol".
  3. Path traversal outside the workspace is rejected.
  4. Missing file returns exists=False (not 500).
  5. AC without test_path → 404.
  6. Oversized files get truncated with a flag.
  7. The HTML ac row includes the ▸ code button wired to the endpoint.
"""
import pathlib

import pytest

from app.database import SessionLocal
from app.models import AcceptanceCriterion, Project, Task
from tests.conftest_populated import build_populated_project

BASE = "http://127.0.0.1:8063"


@pytest.fixture(scope="module")
def ps():
    return build_populated_project(prefix="p2ac")


def _prep_test_file(slug: str, rel: str, content: str) -> pathlib.Path:
    """Write a file into the project's workspace dir."""
    from app.api.pipeline import _workspace as _ws
    ws = pathlib.Path(_ws(slug))
    target = ws / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


def _set_ac_test_path(db, task_id: int, position: int, test_path: str) -> None:
    ac = db.query(AcceptanceCriterion).filter(
        AcceptanceCriterion.task_id == task_id,
        AcceptanceCriterion.position == position,
    ).first()
    assert ac, f"ac at position {position} missing"
    ac.test_path = test_path
    ac.verification = "test"
    db.commit()


def _any_task_with_ac(db, proj_id: int):
    t = (db.query(Task)
           .filter(Task.project_id == proj_id)
           .join(AcceptanceCriterion)
           .first())
    return t


def test_test_code_returns_full_file_when_no_symbol(ps):
    s, slug = ps
    _prep_test_file(slug, "tests/test_thing.py",
                    "def test_alpha():\n    assert 1 + 1 == 2\n\n"
                    "def test_beta():\n    assert True\n")
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        task = _any_task_with_ac(db, proj.id)
        pos = task.acceptance_criteria[0].position
        _set_ac_test_path(db, task.id, pos, "tests/test_thing.py")
        task_ext = task.external_id
    finally:
        db.close()

    r = s.get(f"{BASE}/api/v1/tier1/projects/{slug}/tasks/{task_ext}/ac/{pos}/test-code")
    assert r.status_code == 200
    j = r.json()
    assert j["exists"] is True
    assert j["symbol"] is None
    assert "test_alpha" in j["source"]
    assert "test_beta" in j["source"]
    assert j["line_range"][0] == 1
    assert j["language"] == "py"


def test_test_code_slices_function_when_symbol_given(ps):
    s, slug = ps
    _prep_test_file(slug, "tests/test_slice.py",
                    "def test_one():\n    x = 1\n    assert x == 1\n\n"
                    "def test_two():\n    assert 'rare-marker' == 'rare-marker'\n")
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        task = _any_task_with_ac(db, proj.id)
        pos = task.acceptance_criteria[0].position
        _set_ac_test_path(db, task.id, pos, "tests/test_slice.py::test_two")
        task_ext = task.external_id
    finally:
        db.close()

    r = s.get(f"{BASE}/api/v1/tier1/projects/{slug}/tasks/{task_ext}/ac/{pos}/test-code")
    assert r.status_code == 200
    j = r.json()
    assert j["exists"] is True
    assert j["symbol"] == "test_two"
    assert "rare-marker" in j["source"]
    assert "test_one" not in j["source"]
    assert j["line_range"][0] > 1


def test_test_code_rejects_path_traversal(ps):
    s, slug = ps
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        task = _any_task_with_ac(db, proj.id)
        pos = task.acceptance_criteria[0].position
        _set_ac_test_path(db, task.id, pos, "../../../etc/passwd")
        task_ext = task.external_id
    finally:
        db.close()

    r = s.get(f"{BASE}/api/v1/tier1/projects/{slug}/tasks/{task_ext}/ac/{pos}/test-code")
    assert r.status_code == 400
    assert "workspace" in r.json()["detail"].lower()


def test_test_code_reports_missing_file(ps):
    s, slug = ps
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        task = _any_task_with_ac(db, proj.id)
        pos = task.acceptance_criteria[0].position
        _set_ac_test_path(db, task.id, pos, "tests/file_that_does_not_exist.py")
        task_ext = task.external_id
    finally:
        db.close()

    r = s.get(f"{BASE}/api/v1/tier1/projects/{slug}/tasks/{task_ext}/ac/{pos}/test-code")
    assert r.status_code == 200
    j = r.json()
    assert j["exists"] is False
    assert j["source"] is None
    assert j["note"]


def test_test_code_404_for_ac_without_test_path(ps):
    s, slug = ps
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        task = _any_task_with_ac(db, proj.id)
        pos = task.acceptance_criteria[0].position
        _set_ac_test_path(db, task.id, pos, "")  # clear test_path
        task_ext = task.external_id
    finally:
        db.close()

    r = s.get(f"{BASE}/api/v1/tier1/projects/{slug}/tasks/{task_ext}/ac/{pos}/test-code")
    assert r.status_code == 404
    assert "test_path" in r.json()["detail"]


def test_test_code_truncates_huge_files(ps):
    s, slug = ps
    # 500 lines → should truncate to 400
    body = "\n".join(f"LINE_{i:04d}" for i in range(500))
    _prep_test_file(slug, "tests/huge.py", body)
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        task = _any_task_with_ac(db, proj.id)
        pos = task.acceptance_criteria[0].position
        _set_ac_test_path(db, task.id, pos, "tests/huge.py")
        task_ext = task.external_id
    finally:
        db.close()

    r = s.get(f"{BASE}/api/v1/tier1/projects/{slug}/tasks/{task_ext}/ac/{pos}/test-code")
    assert r.status_code == 200
    j = r.json()
    assert j["truncated"] is True
    assert j["source"].count("\n") <= 400


def test_ac_row_template_includes_code_button(ps):
    """The ▸ code button must be in the rendered ac row HTML."""
    s, slug = ps
    # Seed a test file + set AC test_path so the button renders
    _prep_test_file(slug, "tests/test_btn.py", "def test_btn():\n    assert True\n")
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        task = _any_task_with_ac(db, proj.id)
        pos = task.acceptance_criteria[0].position
        _set_ac_test_path(db, task.id, pos, "tests/test_btn.py")
        task_ext = task.external_id
    finally:
        db.close()

    r = s.get(f"{BASE}/ui/projects/{slug}/tasks/{task_ext}")
    assert r.status_code == 200
    html = r.text
    assert "▸ code" in html
    assert "/test-code" in html
