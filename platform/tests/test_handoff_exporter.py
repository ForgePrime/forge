"""Unit tests for services/handoff_exporter — CGAID artifact #4 Handoff Document."""
from dataclasses import dataclass, field

from app.services.handoff_exporter import _render_handoff, _slug_title


@dataclass
class FakeAC:
    position: int
    text: str
    scenario_type: str = "positive"
    verification: str = "test"
    test_path: str | None = None
    command: str | None = None
    source_ref: str | None = None


@dataclass
class FakeKR:
    position: int
    text: str
    status: str = "NOT_STARTED"
    target_value: float | None = None


@dataclass
class FakeObjective:
    external_id: str
    title: str
    business_context: str = ""
    key_results: list = field(default_factory=list)


@dataclass
class FakeProject:
    slug: str
    contract_md: str | None = None


@dataclass
class FakeTask:
    id: int
    external_id: str
    name: str
    type: str = "feature"
    status: str = "TODO"
    origin: str | None = None
    instruction: str | None = None
    description: str | None = None
    scopes: list = field(default_factory=list)
    alignment: dict | None = None
    exclusions: list = field(default_factory=list)
    risks: list | None = None
    acceptance_criteria: list = field(default_factory=list)
    completes_kr_ids: list | None = None
    started_at: object = None
    completed_at: object = None


@dataclass
class FakeDecision:
    id: int
    external_id: str
    issue: str = ""
    recommendation: str = ""
    status: str = "OPEN"
    severity: str | None = None
    task_id: int | None = None


# ---------- All 8 CGAID sections present ----------

def test_handoff_has_all_eight_cgaid_sections():
    """Every CGAID handoff MUST render all 8 named sections, even if empty."""
    t = FakeTask(id=1, external_id="T-001", name="demo", instruction="do x")
    p = FakeProject(slug="test")
    md = _render_handoff(t, p, objective=None, open_decisions=[], closed_decisions=[])
    for section in [
        "1. Intent",
        "2. Scope",
        "3. Assumptions",
        "4. Unknowns",
        "5. Decisions needed",
        "6. Risks",
        "7. Edge cases",
        "8. Verification criteria",
    ]:
        assert f"## {section}" in md, f"Missing section: {section}"


# ---------- Intent ----------

def test_intent_uses_instruction_when_present():
    t = FakeTask(id=1, external_id="T-1", name="x", instruction="Build login endpoint")
    md = _render_handoff(t, FakeProject(slug="p"), None, [], [])
    assert "Build login endpoint" in md


def test_intent_falls_back_to_description():
    t = FakeTask(id=1, external_id="T-1", name="x", description="Login module desc")
    md = _render_handoff(t, FakeProject(slug="p"), None, [], [])
    assert "Login module desc" in md


def test_intent_includes_objective_business_context():
    t = FakeTask(id=1, external_id="T-1", name="x", instruction="do")
    obj = FakeObjective(external_id="O-1", title="Launch",
                        business_context="Q2 pilot for Acme corp")
    md = _render_handoff(t, FakeProject(slug="p"), obj, [], [])
    assert "Q2 pilot for Acme corp" in md
    assert "O-1" in md


# ---------- Scope ----------

def test_scope_renders_alignment_boundaries():
    t = FakeTask(
        id=1, external_id="T-1", name="x", instruction="do",
        alignment={
            "goal": "login works",
            "boundaries": {
                "must": "return JWT",
                "must_not": "store plaintext pw",
                "not_in_scope": "password reset",
            },
        },
        scopes=["backend", "auth"],
        exclusions=["no oauth"],
    )
    md = _render_handoff(t, FakeProject(slug="p"), None, [], [])
    assert "login works" in md
    assert "return JWT" in md
    assert "store plaintext pw" in md
    assert "password reset" in md
    assert "backend" in md
    assert "no oauth" in md


# ---------- Assumptions (contract) ----------

def test_assumptions_includes_project_contract():
    t = FakeTask(id=1, external_id="T-1", name="x", instruction="do")
    p = FakeProject(slug="p", contract_md="Use Python 3.13. No mutable defaults.")
    md = _render_handoff(t, p, None, [], [])
    assert "Python 3.13" in md
    assert "mutable defaults" in md


def test_assumptions_handles_missing_contract():
    t = FakeTask(id=1, external_id="T-1", name="x", instruction="do")
    md = _render_handoff(t, FakeProject(slug="p"), None, [], [])
    assert "no project-level contract" in md


def test_assumptions_truncates_long_contract():
    t = FakeTask(id=1, external_id="T-1", name="x", instruction="do")
    big_contract = "X" * 5000
    p = FakeProject(slug="p", contract_md=big_contract)
    md = _render_handoff(t, p, None, [], [])
    assert "truncated" in md


# ---------- Unknowns / decisions needed ----------

def test_unknowns_lists_open_decisions_scoped_to_task():
    t = FakeTask(id=42, external_id="T-1", name="x", instruction="do")
    d_task = FakeDecision(id=10, external_id="D-001", issue="DB choice?", task_id=42)
    d_proj = FakeDecision(id=11, external_id="D-002", issue="Auth strategy?", task_id=None)
    md = _render_handoff(t, FakeProject(slug="p"), None,
                         open_decisions=[d_task, d_proj], closed_decisions=[])
    assert "D-001" in md
    assert "DB choice?" in md
    assert "D-002" in md
    assert "1 open decision(s) on this task" in md


def test_decisions_needed_highlights_high_severity():
    t = FakeTask(id=1, external_id="T-1", name="x", instruction="do")
    d = FakeDecision(
        id=1, external_id="D-005", issue="Persist audit log 7y or 5y?",
        recommendation="7y per GDPR art.17", status="OPEN", severity="HIGH",
    )
    md = _render_handoff(t, FakeProject(slug="p"), None, [d], [])
    assert "D-005" in md
    assert "HIGH" in md
    assert "7y per GDPR" in md


def test_no_open_decisions_shows_clean_message():
    t = FakeTask(id=1, external_id="T-1", name="x", instruction="do")
    md = _render_handoff(t, FakeProject(slug="p"), None, [], [])
    assert "no open questions" in md.lower()


# ---------- Risks (CGAID addition) ----------

def test_risks_rendered_when_present():
    t = FakeTask(
        id=1, external_id="T-1", name="x", instruction="do",
        risks=[
            {"risk": "DB migration down-time", "mitigation": "blue-green deploy",
             "severity": "HIGH", "owner": "alice"},
            {"risk": "test data PII leak", "mitigation": "fake data generator",
             "severity": "MEDIUM"},
        ],
    )
    md = _render_handoff(t, FakeProject(slug="p"), None, [], [])
    assert "DB migration down-time" in md
    assert "blue-green deploy" in md
    assert "alice" in md
    assert "HIGH" in md
    assert "PII leak" in md


def test_risks_empty_shows_placeholder():
    t = FakeTask(id=1, external_id="T-1", name="x", instruction="do")
    md = _render_handoff(t, FakeProject(slug="p"), None, [], [])
    assert "no explicit risks captured" in md


# ---------- Edge cases ----------

def test_edge_cases_filters_negative_and_edge_scenarios():
    t = FakeTask(
        id=1, external_id="T-1", name="x", instruction="do",
        acceptance_criteria=[
            FakeAC(position=0, text="happy", scenario_type="positive"),
            FakeAC(position=1, text="reject dup", scenario_type="negative",
                   verification="test", test_path="tests/test.py::test_dup"),
            FakeAC(position=2, text="boundary", scenario_type="edge_case",
                   verification="test", test_path="tests/test.py::test_edge"),
        ],
    )
    md = _render_handoff(t, FakeProject(slug="p"), None, [], [])
    # Happy path should NOT appear in Edge cases section — only in section 8
    # Edge section must contain the 2 failure modes
    edge_section = md.split("## 7. Edge cases")[1].split("## 8.")[0]
    assert "reject dup" in edge_section
    assert "boundary" in edge_section
    assert "happy" not in edge_section


def test_no_edge_cases_warns_about_rejection():
    """Feature/bug with only positive AC should warn — contract_validator.py:133 will FAIL."""
    t = FakeTask(
        id=1, external_id="T-1", name="x", instruction="do",
        acceptance_criteria=[
            FakeAC(position=0, text="happy", scenario_type="positive"),
        ],
    )
    md = _render_handoff(t, FakeProject(slug="p"), None, [], [])
    assert "REJECTED" in md or "contract_validator" in md


# ---------- Verification criteria ----------

def test_verification_lists_all_acs_with_test_paths():
    t = FakeTask(
        id=1, external_id="T-1", name="x", instruction="do",
        acceptance_criteria=[
            FakeAC(position=0, text="happy", scenario_type="positive",
                   verification="test", test_path="tests/x.py::test_ok",
                   source_ref="SRC-001 §2.1"),
        ],
    )
    md = _render_handoff(t, FakeProject(slug="p"), None, [], [])
    verif = md.split("## 8. Verification criteria")[1]
    assert "tests/x.py::test_ok" in verif
    assert "SRC-001" in verif


def test_verification_includes_kr_linkage_when_present():
    t = FakeTask(
        id=1, external_id="T-1", name="x", instruction="do",
        origin="O-1", completes_kr_ids=["KR0"],
    )
    obj = FakeObjective(
        external_id="O-1", title="o",
        key_results=[FakeKR(position=0, text="Sign-up live", target_value=1)],
    )
    md = _render_handoff(t, FakeProject(slug="p"), obj, [], [])
    verif = md.split("## 8. Verification criteria")[1]
    assert "KR0" in verif
    assert "Sign-up live" in verif
    assert "target=1" in verif


# ---------- slug_title ----------

def test_slug_title_keeps_alphanumeric_only():
    assert _slug_title("Hello World!") == "hello-world"


def test_slug_title_truncates_long():
    assert len(_slug_title("x" * 100, max_len=20)) <= 20
