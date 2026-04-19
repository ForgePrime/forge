"""P2.4 / P2.5 — budget + veto config endpoints and helper.

Tests:
  1. Budget GET returns defaults when not set.
  2. Budget PUT persists and GET reflects the saved values.
  3. Validation: negative / huge budget rejected by Pydantic.
  4. Veto GET/PUT round-trip (endpoint already existed, re-verified).
  5. Helper `veto_match` matches fnmatch patterns including globs.
  6. Helper `warn_level` classifies ok / warn / over correctly.
  7. Helper `remaining_usd` never goes negative.
  8. Contract tab HTML renders both config cards.
"""
import pytest

from app.database import SessionLocal
from app.models import Project
from app.services.budget_guard import (
    remaining_usd, warn_level, veto_match, task_budget_usd, run_budget_usd,
)
from tests.conftest_populated import build_populated_project

BASE = "http://127.0.0.1:8063"


@pytest.fixture(scope="module")
def ps():
    return build_populated_project(prefix="p2bv")


def test_budget_config_defaults_when_unset(ps):
    s, slug = ps
    # Clear config first
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        cfg = dict(proj.config or {})
        for k in ("budget_task_usd", "budget_run_usd", "warn_at_pct"):
            cfg.pop(k, None)
        proj.config = cfg
        db.commit()
    finally:
        db.close()

    r = s.get(f"{BASE}/api/v1/tier1/projects/{slug}/budget-config")
    assert r.status_code == 200
    j = r.json()
    assert j["budget_task_usd"] == 1.0
    assert j["budget_run_usd"] == 5.0
    assert j["warn_at_pct"] == 80


def test_budget_config_put_persists(ps):
    s, slug = ps
    r = s.put(f"{BASE}/api/v1/tier1/projects/{slug}/budget-config",
              json={"budget_task_usd": 0.50, "budget_run_usd": 3.00, "warn_at_pct": 60})
    assert r.status_code == 200
    j = r.json()
    assert j["budget_task_usd"] == 0.50
    assert j["budget_run_usd"] == 3.00
    # GET reflects the change
    g = s.get(f"{BASE}/api/v1/tier1/projects/{slug}/budget-config").json()
    assert g["budget_task_usd"] == 0.50
    assert g["warn_at_pct"] == 60


def test_budget_config_rejects_negative(ps):
    s, slug = ps
    r = s.put(f"{BASE}/api/v1/tier1/projects/{slug}/budget-config",
              json={"budget_task_usd": -1, "budget_run_usd": 1.0})
    assert r.status_code == 422


def test_budget_config_rejects_huge(ps):
    s, slug = ps
    r = s.put(f"{BASE}/api/v1/tier1/projects/{slug}/budget-config",
              json={"budget_task_usd": 1.0, "budget_run_usd": 9999.0})
    assert r.status_code == 422


def test_veto_config_round_trip(ps):
    s, slug = ps
    r = s.put(f"{BASE}/api/v1/tier1/projects/{slug}/veto-config",
              json={"veto_paths": ["migrations/**", ".env*", "infra/prod/**"],
                    "budget_hard_cap_pct": 90})
    assert r.status_code == 200
    j = r.json()
    assert "migrations/**" in j["veto_paths"]
    assert j["budget_hard_cap_pct"] == 90
    g = s.get(f"{BASE}/api/v1/tier1/projects/{slug}/veto-config").json()
    assert sorted(g["veto_paths"]) == sorted(["migrations/**", ".env*", "infra/prod/**"])


def test_veto_config_drops_blank_paths(ps):
    s, slug = ps
    r = s.put(f"{BASE}/api/v1/tier1/projects/{slug}/veto-config",
              json={"veto_paths": ["", "  ", "secrets.py", ""]})
    assert r.status_code == 200
    assert r.json()["veto_paths"] == ["secrets.py"]


# ---- Pure helper tests ---------------------------------------------------

def test_task_budget_defaults():
    assert task_budget_usd(None) == 1.0
    assert task_budget_usd({}) == 1.0
    assert task_budget_usd({"budget_task_usd": 0.25}) == 0.25


def test_run_budget_defaults():
    assert run_budget_usd(None) == 5.0
    assert run_budget_usd({"budget_run_usd": 2.5}) == 2.5


def test_warn_level_under_warn_is_ok():
    cfg = {"budget_run_usd": 10, "warn_at_pct": 80}
    assert warn_level(cfg, 0) == "ok"
    assert warn_level(cfg, 7.99) == "ok"


def test_warn_level_at_warn_threshold():
    cfg = {"budget_run_usd": 10, "warn_at_pct": 80}
    assert warn_level(cfg, 8.0) == "warn"
    assert warn_level(cfg, 9.99) == "warn"


def test_warn_level_over_cap():
    cfg = {"budget_run_usd": 10}
    assert warn_level(cfg, 10.0) == "over"
    assert warn_level(cfg, 42.0) == "over"


def test_remaining_usd_never_negative():
    cfg = {"budget_run_usd": 5}
    assert remaining_usd(cfg, 3.0) == 2.0
    assert remaining_usd(cfg, 9999.0) == 0.0


def test_veto_match_simple_pattern():
    cfg = {"veto_paths": [".env*", "migrations/**"]}
    assert veto_match(cfg, ".env") == ".env*"
    assert veto_match(cfg, ".env.prod") == ".env*"
    assert veto_match(cfg, "migrations/v1/a.py") == "migrations/**"


def test_veto_match_no_match_returns_none():
    cfg = {"veto_paths": [".env*"]}
    assert veto_match(cfg, "app/config.py") is None
    assert veto_match(None, "anything") is None
    assert veto_match({"veto_paths": []}, "anything") is None


def test_veto_match_empty_path_never_matches():
    assert veto_match({"veto_paths": ["*"]}, "") is None


# ---- UI ------------------------------------------------------------------

def test_contract_tab_renders_budget_and_veto_cards(ps):
    s, slug = ps
    r = s.get(f"{BASE}/ui/projects/{slug}?tab=contract")
    assert r.status_code == 200
    html = r.text
    assert "💰 Budget" in html
    assert "🚫 Veto paths" in html
    assert "budget_task_usd" in html
    assert "veto_paths" in html
    # Fetches must point to the right endpoints
    assert "/budget-config" in html
    assert "/veto-config" in html
