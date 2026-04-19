"""Skeptical route coverage — run every major UI route against a project with
REAL data (populated via conftest_populated.build_populated_project).

This is the test that would have caught the `asda`/`O-002` NameError. Fresh-signup
fixtures don't populate AcceptanceCriterion / LLMCall / Finding → aggregation
queries never fire → import/query bugs stay hidden.

Assertion strategy:
  For every route under test, demand status 200 AND non-trivial body length
  (>5000 chars) so silent-empty template renders also fail loud.
"""
import pytest

from tests.conftest_populated import build_populated_project


@pytest.fixture(scope="module")
def populated():
    return build_populated_project(prefix="rpop")


ROUTES_TO_COVER = [
    # Dashboard
    "/ui/",
    # Per-project tabs — each must render on populated data
    "/ui/projects/{slug}",
    "/ui/projects/{slug}?tab=knowledge",
    "/ui/projects/{slug}?tab=objectives",
    "/ui/projects/{slug}?tab=tasks",
    "/ui/projects/{slug}?tab=findings",
    "/ui/projects/{slug}?tab=decisions",
    "/ui/projects/{slug}?tab=contract",
    "/ui/projects/{slug}?tab=skills",
    "/ui/projects/{slug}?tab=docs",
    "/ui/projects/{slug}?tab=llm-calls",
    "/ui/projects/{slug}?tab=guidelines",
    # Entity detail pages
    "/ui/projects/{slug}/objectives/O-001",
    "/ui/projects/{slug}/objectives/O-002",
    "/ui/projects/{slug}/tasks/T-001",
    "/ui/projects/{slug}/tasks/T-002",
    "/ui/projects/{slug}/tasks/T-003",
]


@pytest.mark.parametrize("route_tpl", ROUTES_TO_COVER)
def test_route_renders_on_populated(populated, route_tpl):
    s, slug = populated
    url = "http://127.0.0.1:8063" + route_tpl.format(slug=slug)
    r = s.get(url)
    assert r.status_code == 200, f"{url} returned {r.status_code}: {r.text[:200]}"
    body = r.text
    # body must be >= 5000 chars — catches silent-empty template renders.
    # (The empty login page is ~2-3k, so 5k is above that threshold but not onerous.)
    assert len(body) >= 5000, (
        f"{url} rendered only {len(body)} chars — likely silent-empty "
        f"template render or missing context. Head: {body[:200]}"
    )


def test_objective_detail_populated_includes_aggregation_sections(populated):
    """Regression test for `asda`/`O-002` NameError — ensure AC aggregation actually fires
    when the objective has tasks-with-ACs."""
    s, slug = populated
    r = s.get(f"http://127.0.0.1:8063/ui/projects/{slug}/objectives/O-001")
    assert r.status_code == 200
    # O-001 has T-001 which has 2 ACs (one sourced, one INVENTED)
    assert "T-001·AC-0" in r.text or "T-001 · AC-0" in r.text or "T-001·AC" in r.text
    # The unsourced badge must be visible on aggregated AC for the unsourced one
    assert "unsourced" in r.text
    # The sourced one must show the source_ref
    assert "SRC-001" in r.text


def test_task_report_populated_returns_real_cost(populated):
    s, slug = populated
    r = s.get(f"http://127.0.0.1:8063/ui/projects/{slug}/tasks/T-001")
    assert r.status_code == 200
    # Cost ledger in the page should reflect our seeded $0.05 llm_call
    assert "0.05" in r.text or "$0.0500" in r.text


def test_anti_pattern_self_seeded_on_startup(populated):
    """After startup lifespan ran, the two seeded anti-patterns must exist."""
    s, _ = populated
    r = s.get("http://127.0.0.1:8063/api/v1/lessons/anti-patterns")
    assert r.status_code == 200
    titles = [ap["title"] for ap in r.json()["anti_patterns"]]
    assert any("fresh-signup" in t or "Tests only cover fresh-signup" in t for t in titles), \
        "forge-self anti-pattern about fresh-fixture tests not seeded"
    assert any("97%" in t or "deep-render" in t.lower() or "mockup review" in t.lower() for t in titles), \
        "forge-self anti-pattern about silent-empty template renders not seeded"
