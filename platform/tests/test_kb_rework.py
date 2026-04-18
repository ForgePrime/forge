"""C1+C2 KB rework — non-happy-path tests.

Coverage:
- t1: anon cannot add notes/URLs/folders
- t2: empty title rejected (validation)
- t3: empty content rejected on note
- t4: short URL rejected
- t5: round-trip: add note, then read back via knowledge listing
- t6: 4 source types render in KB tab UI
- t7: PATCH description on existing source
- t8: PATCH on nonexistent source = 404
"""
import os
import time
import pytest
import requests

BASE = os.environ.get("FORGE_TEST_BASE", "http://127.0.0.1:8063")
TS = int(time.time())


@pytest.fixture(scope="module")
def session_and_slug():
    s = requests.Session()
    r = s.post(f"{BASE}/ui/signup", data={
        "email": f"kb-{TS}@t.com", "password": "pw-test-12345", "full_name": "KB",
        "org_slug": f"kb-{TS}", "org_name": "KB",
    }, allow_redirects=False)
    assert r.status_code == 303
    s.headers["X-CSRF-Token"] = s.cookies.get("forge_csrf") or ""
    slug = f"kb-{TS}"
    s.post(f"{BASE}/ui/projects", data={"slug": slug, "name": "KB", "goal": "x"},
           allow_redirects=False)
    return s, slug


def test_t1_anon_cannot_add_kb():
    s = requests.Session()
    r = s.post(f"{BASE}/api/v1/tier1/projects/x/kb/note",
               json={"title": "x", "content": "y"})
    assert r.status_code in (401, 403)


def test_t2_empty_title_rejected(session_and_slug):
    s, slug = session_and_slug
    r = s.post(f"{BASE}/api/v1/tier1/projects/{slug}/kb/note",
               json={"title": "", "content": "ok"})
    assert r.status_code == 422


def test_t3_empty_content_rejected(session_and_slug):
    s, slug = session_and_slug
    r = s.post(f"{BASE}/api/v1/tier1/projects/{slug}/kb/note",
               json={"title": "t", "content": ""})
    assert r.status_code == 422


def test_t4_short_url_rejected(session_and_slug):
    s, slug = session_and_slug
    r = s.post(f"{BASE}/api/v1/tier1/projects/{slug}/kb/url",
               json={"title": "t", "target_url": "http://"})
    assert r.status_code == 422


def test_t5_note_round_trip(session_and_slug):
    s, slug = session_and_slug
    r = s.post(f"{BASE}/api/v1/tier1/projects/{slug}/kb/note", json={
        "title": "Client meeting 2026-04-18",
        "content": "Verbal: must be on-prem, no Oracle.",
        "description": "verbal client constraints",
    })
    assert r.status_code == 200, r.text
    ext = r.json()["external_id"]
    assert ext.startswith("SRC-")

    r = s.get(f"{BASE}/ui/projects/{slug}?tab=knowledge")
    assert r.status_code == 200
    assert ext in r.text
    assert "Client meeting 2026-04-18" in r.text
    assert "verbal client constraints" in r.text


def test_t6_kb_tab_shows_four_intake_buttons(session_and_slug):
    s, slug = session_and_slug
    r = s.get(f"{BASE}/ui/projects/{slug}?tab=knowledge")
    html = r.text
    for needle in ("URL / web page", "Folder path", "Manual note",
                   "Forge reads"):
        assert needle in html, f"KB UI missing '{needle}'"


def test_t7_patch_description(session_and_slug):
    s, slug = session_and_slug
    r = s.post(f"{BASE}/api/v1/tier1/projects/{slug}/kb/note", json={
        "title": "Patch test", "content": "x",
    })
    ext = r.json()["external_id"]
    r = s.patch(f"{BASE}/api/v1/tier1/projects/{slug}/kb/{ext}",
                json={"description": "added later", "focus_hint": "look at section 3"})
    assert r.status_code == 200
    body = r.json()
    assert body["description_set"] is True
    assert body["focus_hint_set"] is True


def test_t8_patch_nonexistent_404(session_and_slug):
    s, slug = session_and_slug
    r = s.patch(f"{BASE}/api/v1/tier1/projects/{slug}/kb/SRC-9999",
                json={"description": "x"})
    assert r.status_code == 404
