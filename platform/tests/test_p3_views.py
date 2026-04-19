"""P3.3 — tasks tab view toggles (list / kanban / timeline)."""
import pytest

from tests.conftest_populated import build_populated_project

BASE = "http://127.0.0.1:8063"


@pytest.fixture(scope="module")
def ps():
    return build_populated_project(prefix="p3view")


def test_tasks_default_view_is_list(ps):
    s, slug = ps
    r = s.get(f"{BASE}/ui/projects/{slug}?tab=tasks")
    assert r.status_code == 200
    html = r.text
    assert "View:" in html
    # The List pill should be the active one (semibold class)
    assert "📋 List" in html


def test_tasks_kanban_view_renders_columns(ps):
    s, slug = ps
    r = s.get(f"{BASE}/ui/projects/{slug}?tab=tasks&view=kanban")
    assert r.status_code == 200
    html = r.text
    for label in ("Queued", "In progress", "Done", "Failed"):
        assert label in html
    assert 'id="kanban-board"' in html


def test_tasks_timeline_view_renders_ordered_list(ps):
    s, slug = ps
    r = s.get(f"{BASE}/ui/projects/{slug}?tab=tasks&view=timeline")
    assert r.status_code == 200
    html = r.text
    # Timeline uses an <ol> with relative border
    assert "border-l border-slate-300" in html


def test_invalid_view_falls_back_to_list(ps):
    s, slug = ps
    r = s.get(f"{BASE}/ui/projects/{slug}?tab=tasks&view=trojan")
    assert r.status_code == 200
    # Falls back to list — no kanban board markup
    assert 'id="kanban-board"' not in r.text


def test_view_toggle_links_set_query_param(ps):
    s, slug = ps
    r = s.get(f"{BASE}/ui/projects/{slug}?tab=tasks")
    assert r.status_code == 200
    html = r.text
    assert "?tab=tasks&view=kanban" in html
    assert "?tab=tasks&view=timeline" in html
    assert "?tab=tasks&view=list" in html
