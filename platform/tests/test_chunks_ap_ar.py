"""Chunks AP+AQ+AR — docs-polished · auto-attach · impact alert · replay button · tool-call surface."""
import os
import pytest
import requests

from tests.conftest_populated import build_populated_project

BASE = "http://127.0.0.1:8063"


@pytest.fixture(scope="module")
def ps():
    return build_populated_project(prefix="apar")


# Chunk AP — docs polished
def test_docs_polished_empty_when_no_doc_tasks(ps):
    s, slug = ps
    r = s.get(f"{BASE}/api/v1/tier1/projects/{slug}/docs/polished")
    assert r.status_code == 200
    assert r.json()["count"] == 0


def test_docs_tab_includes_polished_section(ps):
    s, slug = ps
    r = s.get(f"{BASE}/ui/projects/{slug}?tab=docs")
    assert r.status_code == 200
    assert "LLM-polished" in r.text
    assert "doc-polished" in r.text


# Chunk AQ — integrations tab + auto-attach
def test_integrations_tab_renders(ps):
    s, slug = ps
    r = s.get(f"{BASE}/ui/projects/{slug}?tab=integrations")
    assert r.status_code == 200
    for needle in ("Webhooks", "Share links", "SharePoint", "Jira", "Planned"):
        assert needle in r.text


def test_skill_attach_engine_matches_by_phase_and_type(ps):
    from app.database import SessionLocal
    from app.models import Project, Skill, ProjectSkill
    from app.services.skill_attach import TaskContext, resolve_skills
    s, slug = ps
    # Seed skills library by hitting /api/v1/skills (this triggers _seed_built_ins)
    s.get(f"{BASE}/api/v1/skills")
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        # Resolve for analysis phase — should include SK-scenario-gen-nonhappy (applies to analysis)
        # Simulate an auto attachment to make it candidate
        sk = db.query(Skill).filter(Skill.external_id == "SK-scenario-gen-nonhappy").first()
        assert sk, "seed not run"
        # Add an auto attach
        db.add(ProjectSkill(project_id=proj.id, skill_id=sk.id, attach_mode="auto"))
        # auto rule on SK-scenario-gen-nonhappy is None → won't match. Give it one:
        sk.auto_attach_rule = {"if_task_type": ["analysis"]}
        db.commit()

        ctx = TaskContext(project_id=proj.id, task_type="analysis", phase="analysis")
        picked = resolve_skills(db, ctx)
        ext_ids = [x.external_id for x in picked]
        assert "SK-scenario-gen-nonhappy" in ext_ids
    finally:
        db.close()


# Chunk AR — replay button + base.html impact guard
def test_llm_call_page_has_replay_button(ps):
    """Any llm_call in populated fixture — open its /ui/llm-calls/{id} and check page has replay button."""
    from app.database import SessionLocal
    from app.models import LLMCall, Project
    s, slug = ps
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        call = db.query(LLMCall).filter(LLMCall.project_id == proj.id).first()
        assert call, "populated fixture should have ≥1 llm_call"
        cid = call.id
    finally:
        db.close()
    r = s.get(f"{BASE}/ui/llm-calls/{cid}")
    assert r.status_code == 200
    # Replay button + Copy prompt button
    assert "Replay with current config" in r.text
    assert "Copy prompt" in r.text


def test_base_html_has_destructive_pattern_guard(ps):
    s, _slug = ps
    r = s.get(f"{BASE}/ui/")
    assert r.status_code == 200
    # JS guard registered
    assert "DESTRUCTIVE_PATTERNS" in r.text
    assert "destructiveHit" in r.text
