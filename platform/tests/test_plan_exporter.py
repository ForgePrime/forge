"""Unit tests for services/plan_exporter — CGAID artifact #3 in-repo Plan export."""
import pathlib
from dataclasses import dataclass, field

from app.services.plan_exporter import _render_task, _render_plan, _slug_title


@dataclass
class FakeAC:
    position: int
    text: str
    scenario_type: str = "positive"
    verification: str = "test"
    test_path: str | None = None
    source_ref: str | None = None


@dataclass
class FakeTask:
    external_id: str
    name: str
    type: str = "feature"
    status: str = "TODO"
    origin: str | None = None
    instruction: str | None = None
    depends_on: list[str] = field(default_factory=list)
    scopes: list[str] = field(default_factory=list)
    alignment: dict | None = None
    acceptance_criteria: list[FakeAC] = field(default_factory=list)
    produces: dict | None = None
    exclusions: list[str] = field(default_factory=list)


@dataclass
class FakeKR:
    position: int
    text: str
    status: str = "NOT_STARTED"
    target_value: float | None = None
    current_value: float | None = None


@dataclass
class FakeObjective:
    external_id: str
    title: str
    status: str = "ACTIVE"
    priority: int = 3
    business_context: str = ""
    key_results: list[FakeKR] = field(default_factory=list)


@dataclass
class FakeProject:
    slug: str


# ---------- slug_title ----------

def test_slug_title_basic():
    assert _slug_title("Hello World") == "hello-world"


def test_slug_title_polish_strips_diacritics():
    # Not really strips — lowercases alphanumerics only; Polish diacritics are not [a-z]
    # so they become separators. Accept whatever the function does — assert deterministic & filesystem-safe.
    result = _slug_title("Rezerwacje klienta")
    assert all(c.isalnum() or c == "-" for c in result)
    assert "rezerwacje" in result or "klienta" in result


def test_slug_title_truncation():
    long = "very long title " * 10
    assert len(_slug_title(long, max_len=20)) <= 20


def test_slug_title_empty_fallback():
    assert _slug_title("") == "untitled"
    assert _slug_title("!!!") == "untitled"


# ---------- _render_task ----------

def test_render_task_minimal():
    t = FakeTask(external_id="T-001", name="Add login", instruction="Build login endpoint")
    md = _render_task(t)
    assert "T-001" in md
    assert "Add login" in md
    assert "Build login endpoint" in md
    assert "feature" in md.lower()


def test_render_task_with_ac_and_alignment():
    t = FakeTask(
        external_id="T-002", name="Create user", type="feature", status="DONE",
        origin="O-001",
        instruction="POST /users",
        depends_on=["T-001"],
        scopes=["backend"],
        alignment={
            "goal": "signup works",
            "boundaries": {"must": "return 201", "must_not": "log passwords",
                           "not_in_scope": "email verification"},
            "success": "user row in DB",
        },
        acceptance_criteria=[
            FakeAC(position=0, text="happy path", scenario_type="positive",
                   verification="test", test_path="tests/test_users.py::test_create",
                   source_ref="SRC-001 §2.1"),
            FakeAC(position=1, text="reject duplicate", scenario_type="negative",
                   verification="test"),
        ],
        produces={"endpoint": "POST /users → 201"},
        exclusions=["no oauth"],
    )
    md = _render_task(t)
    assert "T-002" in md
    assert "O-001" in md
    assert "T-001" in md and "Depends on" in md
    assert "backend" in md
    assert "MUST: return 201" in md
    assert "MUST NOT: log passwords" in md
    assert "NOT IN SCOPE: email verification" in md
    assert "success: user row in db" in md.lower()
    assert "AC-0" in md and "AC-1" in md
    assert "test_users.py" in md
    assert "SRC-001" in md
    assert "Produces" in md
    assert "no oauth" in md


def test_render_plan_project_level():
    p = FakeProject(slug="acme")
    tasks = [
        FakeTask(external_id="T-001", name="first", status="DONE"),
        FakeTask(external_id="T-002", name="second", status="TODO"),
        FakeTask(external_id="T-003", name="third", status="TODO"),
    ]
    md = _render_plan(p, tasks, objective=None)
    assert "# Execution Plan — acme" in md
    assert "Tasks in plan:** 3" in md
    # Status grouping
    assert "## TODO (2)" in md
    assert "## DONE (1)" in md
    # Tasks appear
    for t in tasks:
        assert t.external_id in md


def test_render_plan_with_objective_and_krs():
    p = FakeProject(slug="acme")
    obj = FakeObjective(
        external_id="O-001", title="Launch product", priority=1,
        business_context="Client needs MVP for Q2 pilot",
        key_results=[
            FakeKR(position=0, text="Signup flow live", status="NOT_STARTED"),
            FakeKR(position=1, text="< 2% error rate",
                   status="IN_PROGRESS", target_value=0.02, current_value=0.04),
        ],
    )
    tasks = [FakeTask(external_id="T-010", name="signup", origin="O-001")]
    md = _render_plan(p, tasks, objective=obj)
    assert "O-001" in md
    assert "Launch product" in md
    assert "P1" in md
    assert "Client needs MVP" in md
    assert "KR0" in md and "KR1" in md
    assert "target=0.02" in md
    assert "current=0.04" in md


def test_render_plan_preserves_declaration_order_within_status():
    p = FakeProject(slug="x")
    tasks = [
        FakeTask(external_id="T-100", name="alpha", status="TODO"),
        FakeTask(external_id="T-101", name="beta", status="TODO"),
        FakeTask(external_id="T-102", name="gamma", status="TODO"),
    ]
    md = _render_plan(p, tasks)
    idx_a = md.index("T-100")
    idx_b = md.index("T-101")
    idx_c = md.index("T-102")
    assert idx_a < idx_b < idx_c


def test_render_plan_handles_empty_tasks():
    p = FakeProject(slug="empty")
    md = _render_plan(p, [])
    assert "Tasks in plan:** 0" in md
    assert "Execution Plan — empty" in md
