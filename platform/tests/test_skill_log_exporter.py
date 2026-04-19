"""Unit tests for services/skill_log_exporter — CGAID Artifact #8."""
import pathlib
from dataclasses import dataclass, field
from unittest.mock import MagicMock

from app.services.skill_log_exporter import (
    _render_lesson, _render_anti_pattern, _render_skill,
)


# ---------- Fake models ----------

@dataclass
class FakeLesson:
    id: int = 1
    title: str = "Don't trust manual AC"
    kind: str = "didnt_work"
    description: str = "Manual AC declared PASSED but actually failed in prod."
    tags: list = field(default_factory=lambda: ["phase-a", "trust"])
    source: str = "llm-extract"
    objective_external_id: str | None = "O-001"
    created_at: object = None


@dataclass
class FakeAntiPattern:
    id: int = 1
    title: str = "single-write when dual-write required"
    description: str = "Write to only one table when SRC requires dual-write"
    example: str | None = "INSERT INTO users_new VALUES (...)"
    correct_way: str | None = "INSERT INTO users_new VALUES (...); INSERT INTO users_legacy VALUES (...)"
    applies_to_kinds: list = field(default_factory=lambda: ["migration", "code"])
    times_seen: int = 3
    promoted_from_lesson_id: int | None = 42
    active: bool = True
    created_at: object = None


@dataclass
class FakeSkill:
    id: int = 1
    external_id: str = "SK-security-owasp"
    category: str = "opinion"
    name: str = "OWASP security reviewer"
    description: str | None = "Reviews delivery for OWASP top 10"
    cost_impact_usd: float | None = 0.047


@dataclass
class FakeProjectSkill:
    id: int = 1
    project_id: int = 1
    skill_id: int = 1
    attach_mode: str = "auto"
    invocations: int = 17
    last_used_at: object = None


# ---------- Lesson rendering ----------

def test_render_lesson_has_title_and_meta():
    out = "\n".join(_render_lesson(FakeLesson()))
    assert "Don't trust manual AC" in out
    assert "didnt_work" in out
    assert "O-001" in out
    assert "llm-extract" in out


def test_render_lesson_with_tags_visible():
    out = "\n".join(_render_lesson(FakeLesson(tags=["x", "y", "z"])))
    assert "tags:" in out
    assert "x, y, z" in out


def test_render_lesson_empty_description_placeholder():
    out = "\n".join(_render_lesson(FakeLesson(description="")))
    assert "no description" in out


# ---------- Anti-pattern rendering ----------

def test_render_anti_pattern_has_title_and_promoted_link():
    out = "\n".join(_render_anti_pattern(FakeAntiPattern()))
    assert "single-write when dual-write required" in out
    assert "#42" in out  # promoted from lesson id
    assert "seen: 3×" in out


def test_render_anti_pattern_renders_example_and_correct_way_as_code():
    out = "\n".join(_render_anti_pattern(FakeAntiPattern()))
    assert "Don't do this:" in out
    assert "Do this instead:" in out
    # Code fences surround the examples
    assert "```" in out


def test_render_anti_pattern_inactive_noted():
    ap = FakeAntiPattern(active=False)
    out = "\n".join(_render_anti_pattern(ap))
    assert "active: no" in out


def test_render_anti_pattern_empty_optional_fields():
    """example/correct_way None → no code block emitted."""
    ap = FakeAntiPattern(example=None, correct_way=None)
    out = "\n".join(_render_anti_pattern(ap))
    assert "Don't do this" not in out
    assert "Do this instead" not in out


# ---------- Skill rendering ----------

def test_render_skill_includes_cost_and_invocations():
    ps = FakeProjectSkill()
    sk = FakeSkill()
    out = "\n".join(_render_skill(ps, sk))
    assert "OWASP security reviewer" in out
    assert "SK-security-owasp" in out
    assert "invocations: 17" in out
    assert "$0.04" in out  # float rendered to 4 decimals, truncated in assert


def test_render_skill_missing_cost_impact():
    sk = FakeSkill(cost_impact_usd=None)
    ps = FakeProjectSkill()
    out = "\n".join(_render_skill(ps, sk))
    # Should not include "cost impact" line when value is None
    assert "cost impact" not in out.lower()


def test_render_skill_missing_description():
    sk = FakeSkill(description=None)
    ps = FakeProjectSkill()
    out = "\n".join(_render_skill(ps, sk))
    # Description section simply absent; no crash
    assert "SK-security-owasp" in out


# ---------- Integration-ish: no-DB happy call via MagicMock ----------

def test_export_writes_file_with_expected_shape(tmp_path):
    """End-to-end: exporter produces file with all 3 CGAID sections."""
    from app.services.skill_log_exporter import export_skill_change_log

    project = MagicMock()
    project.id = 7
    project.slug = "test-proj"
    project.organization_id = 1

    db = MagicMock()

    # Craft query chain responses
    def query(*models):
        """Accept variable model args — exporter calls db.query(ProjectSkill, Skill)."""
        q = MagicMock()
        from app.models import ProjectLesson, AntiPattern, ProjectSkill, Skill
        first = models[0] if models else None
        if first is ProjectLesson:
            q.filter.return_value.order_by.return_value.all.return_value = [FakeLesson()]
        elif first is AntiPattern:
            q.filter.return_value.order_by.return_value.all.return_value = [FakeAntiPattern()]
        elif first is ProjectSkill:
            q.join.return_value.filter.return_value.order_by.return_value.all.return_value = [
                (FakeProjectSkill(), FakeSkill()),
            ]
        return q

    db.query.side_effect = query

    path = export_skill_change_log(db, project, str(tmp_path))
    assert path is not None
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    # All 3 CGAID sections present
    assert "## 1. What failed" in content
    assert "## 2. What changed" in content
    assert "## 3. Observed impact" in content
    # Known-limitation disclosure inline
    assert "limitation" in content.lower()
    # Path convention
    assert path.parent.name == ".ai"
    assert path.name == "SKILL_CHANGE_LOG.md"


def test_export_handles_empty_project():
    """Empty project → sections explicitly labeled '(none captured)'."""
    from app.services.skill_log_exporter import export_skill_change_log
    import tempfile

    project = MagicMock()
    project.id = 99
    project.slug = "empty-proj"
    project.organization_id = None

    db = MagicMock()
    def query(*models):
        q = MagicMock()
        q.filter.return_value.order_by.return_value.all.return_value = []
        q.join.return_value.filter.return_value.order_by.return_value.all.return_value = []
        return q
    db.query.side_effect = query

    with tempfile.TemporaryDirectory() as tmp:
        path = export_skill_change_log(db, project, tmp)
        assert path is not None
        content = path.read_text(encoding="utf-8")
        assert "no lessons captured yet" in content
        assert "no active anti-patterns" in content
        assert "no skills attached" in content
