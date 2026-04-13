"""Tests for core.guidelines — project standards registry.

Tests cover:
- Adding guidelines with valid data
- Scope matching (exact match, 'general' always included)
- Weight filtering (must/should/may rendering)
- render_guidelines_context output format
- ACTIVE/DEPRECATED status handling
- derived_from field preservation
- Dedup by (scope, title)
"""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))

from guidelines import (
    CONTRACTS,
    cmd_add,
    cmd_update,
    load_or_create,
    save_json,
    guidelines_path,
    render_guidelines_context,
    scope_matches,
    validate_scope,
)
from contracts import validate_contract, atomic_write_json


# ---------------------------------------------------------------------------
# Helper to build guideline args
# ---------------------------------------------------------------------------

def _add_args(project, data_list):
    return SimpleNamespace(project=project, data=json.dumps(data_list))


def _update_args(project, data_list):
    return SimpleNamespace(project=project, data=json.dumps(data_list))


# ---------------------------------------------------------------------------
# Adding guidelines
# ---------------------------------------------------------------------------

class TestAddGuideline:
    """Tests for adding guidelines."""

    def test_add_valid_guideline(self, forge_env, project_name):
        data = [{
            "title": "Use Repository Pattern",
            "scope": "backend",
            "content": "All DB access through repositories.",
            "weight": "must",
        }]
        cmd_add(_add_args(project_name, data))

        store = load_or_create(project_name)
        assert len(store["guidelines"]) == 1
        g = store["guidelines"][0]
        assert g["id"] == "G-001"
        assert g["title"] == "Use Repository Pattern"
        assert g["scope"] == "backend"
        assert g["weight"] == "must"
        assert g["status"] == "ACTIVE"

    def test_add_multiple_guidelines_increments_ids(self, forge_env, project_name):
        data = [
            {"title": "Rule A", "scope": "backend", "content": "Do A"},
            {"title": "Rule B", "scope": "frontend", "content": "Do B"},
        ]
        cmd_add(_add_args(project_name, data))

        store = load_or_create(project_name)
        assert len(store["guidelines"]) == 2
        assert store["guidelines"][0]["id"] == "G-001"
        assert store["guidelines"][1]["id"] == "G-002"

    def test_add_rejects_invalid_weight(self):
        spec = CONTRACTS["add"]
        data = [{"title": "X", "scope": "y", "content": "z", "weight": "INVALID"}]
        errors = validate_contract(spec, data)
        assert any("weight" in e for e in errors)

    def test_add_dedup_by_scope_and_title(self, forge_env, project_name):
        """Duplicate (scope, title) should be skipped."""
        data = [{"title": "Rule A", "scope": "backend", "content": "content"}]
        cmd_add(_add_args(project_name, data))
        cmd_add(_add_args(project_name, data))  # same again

        store = load_or_create(project_name)
        assert len(store["guidelines"]) == 1

    def test_default_weight_is_should(self, forge_env, project_name):
        data = [{"title": "No weight", "scope": "general", "content": "test"}]
        cmd_add(_add_args(project_name, data))

        store = load_or_create(project_name)
        assert store["guidelines"][0]["weight"] == "should"

    def test_derived_from_preserved(self, forge_env, project_name):
        data = [{
            "title": "Latency benchmark",
            "scope": "performance",
            "content": "p95 < 200ms",
            "derived_from": "O-001",
        }]
        cmd_add(_add_args(project_name, data))

        store = load_or_create(project_name)
        assert store["guidelines"][0]["derived_from"] == "O-001"


# ---------------------------------------------------------------------------
# Scope matching
# ---------------------------------------------------------------------------

class TestScopeMatching:
    """Tests for scope filtering in render_guidelines_context."""

    def _make_guideline(self, gid, scope, weight="should", status="ACTIVE"):
        return {
            "id": gid,
            "title": f"Guideline {gid}",
            "scope": scope,
            "content": f"Content for {gid}",
            "weight": weight,
            "status": status,
            "examples": [],
        }

    def test_exact_scope_match(self):
        guidelines = [
            self._make_guideline("G-001", "backend"),
            self._make_guideline("G-002", "frontend"),
        ]
        lines = render_guidelines_context(guidelines, {"backend"})
        text = "\n".join(lines)
        assert "G-001" in text
        assert "G-002" not in text

    def test_general_always_included(self):
        guidelines = [
            self._make_guideline("G-001", "general"),
            self._make_guideline("G-002", "backend"),
        ]
        # Request scopes = {"database"} — general should still be included
        lines = render_guidelines_context(guidelines, {"database"})
        text = "\n".join(lines)
        assert "G-001" in text
        assert "G-002" not in text

    def test_multiple_scopes(self):
        guidelines = [
            self._make_guideline("G-001", "backend"),
            self._make_guideline("G-002", "database"),
            self._make_guideline("G-003", "frontend"),
        ]
        lines = render_guidelines_context(guidelines, {"backend", "database"})
        text = "\n".join(lines)
        assert "G-001" in text
        assert "G-002" in text
        assert "G-003" not in text

    def test_empty_scopes_gets_general_only(self):
        guidelines = [
            self._make_guideline("G-001", "general"),
            self._make_guideline("G-002", "backend"),
        ]
        lines = render_guidelines_context(guidelines, set())
        text = "\n".join(lines)
        assert "G-001" in text
        assert "G-002" not in text


# ---------------------------------------------------------------------------
# Weight filtering in render_guidelines_context
# ---------------------------------------------------------------------------

class TestWeightFiltering:
    """Tests for how different weights are rendered."""

    def _make_guideline(self, gid, scope, weight, content="Some content"):
        return {
            "id": gid,
            "title": f"Guideline {gid}",
            "scope": scope,
            "content": content,
            "weight": weight,
            "status": "ACTIVE",
            "examples": [],
        }

    def test_must_always_loaded_with_full_content(self):
        guidelines = [
            self._make_guideline("G-001", "general", "must", "Full must content"),
        ]
        lines = render_guidelines_context(guidelines, set())
        text = "\n".join(lines)
        assert "G-001" in text
        assert "MUST" in text
        assert "Full must content" in text

    def test_should_loaded_conditionally(self):
        guidelines = [
            self._make_guideline("G-001", "general", "should", "Should content here"),
        ]
        lines = render_guidelines_context(guidelines, set())
        text = "\n".join(lines)
        assert "G-001" in text
        assert "Should content here" in text

    def test_may_rendered_as_titles_only(self):
        guidelines = [
            self._make_guideline("G-001", "general", "may", "May content should not appear fully"),
        ]
        lines = render_guidelines_context(guidelines, set())
        text = "\n".join(lines)
        assert "G-001" in text
        # 'may' guidelines show title only (in the "Additional guidelines" section)
        assert "Additional guidelines" in text

    def test_must_has_must_marker(self):
        guidelines = [
            self._make_guideline("G-001", "general", "must"),
        ]
        lines = render_guidelines_context(guidelines, set())
        text = "\n".join(lines)
        assert "_(MUST)_" in text

    def test_empty_guidelines_returns_empty(self):
        lines = render_guidelines_context([], set())
        assert lines == []


# ---------------------------------------------------------------------------
# render_guidelines_context output
# ---------------------------------------------------------------------------

class TestRenderGuidelinesContext:
    """Tests for the full render_guidelines_context function."""

    def _make_guideline(self, gid, scope, weight, content="content"):
        return {
            "id": gid,
            "title": f"Guideline {gid}",
            "scope": scope,
            "content": content,
            "weight": weight,
            "status": "ACTIVE",
            "examples": ["example code"],
        }

    def test_header_shows_count(self):
        guidelines = [self._make_guideline("G-001", "general", "must")]
        lines = render_guidelines_context(guidelines, set())
        assert any("Applicable Guidelines (1)" in l for l in lines)

    def test_must_examples_included(self):
        guidelines = [self._make_guideline("G-001", "general", "must")]
        lines = render_guidelines_context(guidelines, set())
        text = "\n".join(lines)
        assert "Example:" in text

    def test_global_guidelines_bypass_scope_filter(self):
        """Global guidelines should always be included regardless of scopes."""
        project_guidelines = [
            self._make_guideline("G-001", "backend", "must"),
        ]
        global_guidelines = [
            self._make_guideline("G-G01", "infra", "must", "Global infra rule"),
        ]
        lines = render_guidelines_context(
            project_guidelines,
            {"frontend"},  # does NOT include "backend" or "infra"
            global_guidelines=global_guidelines,
        )
        text = "\n".join(lines)
        # Global should be present (bypasses scope filter)
        assert "G-G01" in text
        # Project backend guideline NOT included (scope mismatch)
        assert "G-001" not in text


# ---------------------------------------------------------------------------
# ACTIVE / DEPRECATED status
# ---------------------------------------------------------------------------

class TestGuidelineStatus:
    """Tests for ACTIVE/DEPRECATED status transitions."""

    def test_update_to_deprecated(self, forge_env, project_name):
        data = [{"title": "Old Rule", "scope": "backend", "content": "deprecated"}]
        cmd_add(_add_args(project_name, data))

        cmd_update(_update_args(project_name, [{"id": "G-001", "status": "DEPRECATED"}]))

        store = load_or_create(project_name)
        assert store["guidelines"][0]["status"] == "DEPRECATED"

    def test_deprecated_not_counted_as_active(self, forge_env, project_name):
        data = [
            {"title": "Active Rule", "scope": "general", "content": "active"},
            {"title": "Old Rule", "scope": "general", "content": "old"},
        ]
        cmd_add(_add_args(project_name, data))
        cmd_update(_update_args(project_name, [{"id": "G-002", "status": "DEPRECATED"}]))

        store = load_or_create(project_name)
        active = [g for g in store["guidelines"] if g["status"] == "ACTIVE"]
        assert len(active) == 1

    def test_invalid_status_rejected(self):
        spec = CONTRACTS["update"]
        data = [{"id": "G-001", "status": "INVALID"}]
        errors = validate_contract(spec, data)
        assert any("status" in e for e in errors)


# ---------------------------------------------------------------------------
# Scope hierarchy (Faza 2)
# ---------------------------------------------------------------------------

class TestScopeHierarchy:
    """Tests for hierarchical scope matching (parent applies to children)."""

    def _make_guideline(self, gid, scope, weight="should"):
        return {
            "id": gid,
            "title": f"Guideline {gid}",
            "scope": scope,
            "content": f"Content for {gid}",
            "weight": weight,
            "status": "ACTIVE",
            "examples": [],
        }

    def test_parent_scope_matches_child(self):
        """'backend' guideline should apply when task scope is 'backend/api'."""
        guidelines = [
            self._make_guideline("G-001", "backend"),
        ]
        lines = render_guidelines_context(guidelines, {"backend/api"})
        text = "\n".join(lines)
        assert "G-001" in text

    def test_parent_matches_deep_child(self):
        """'backend' should match 'backend/api/auth'."""
        guidelines = [
            self._make_guideline("G-001", "backend"),
        ]
        lines = render_guidelines_context(guidelines, {"backend/api/auth"})
        text = "\n".join(lines)
        assert "G-001" in text

    def test_child_does_not_match_sibling(self):
        """'backend/api' should NOT match 'backend/database'."""
        guidelines = [
            self._make_guideline("G-001", "backend/api"),
        ]
        lines = render_guidelines_context(guidelines, {"backend/database"})
        text = "\n".join(lines)
        assert "G-001" not in text

    def test_exact_child_scope_matches(self):
        """'backend/api' should match 'backend/api'."""
        guidelines = [
            self._make_guideline("G-001", "backend/api"),
        ]
        lines = render_guidelines_context(guidelines, {"backend/api"})
        text = "\n".join(lines)
        assert "G-001" in text

    def test_child_does_not_match_parent_scope(self):
        """'backend/api' guideline should NOT apply when task scope is just 'backend'."""
        guidelines = [
            self._make_guideline("G-001", "backend/api"),
        ]
        lines = render_guidelines_context(guidelines, {"backend"})
        text = "\n".join(lines)
        assert "G-001" not in text


# ---------------------------------------------------------------------------
# Lessons promote and guidelines import
# ---------------------------------------------------------------------------

class TestLessonsPromote:
    """Tests for lessons promote command."""

    def test_promote_creates_global_guideline(self, forge_env, project_name):
        """Promoting a lesson should create a global guideline."""
        from lessons import cmd_add as lessons_add, load_or_create as lessons_load

        # Create a lesson
        args = SimpleNamespace(
            project=project_name,
            data=json.dumps([{
                "category": "pattern-discovered",
                "title": "Always validate JWT audience",
                "detail": "Skipping aud validation allows cross-service token reuse",
                "severity": "critical",
                "applies_to": "Any API with auth",
                "tags": ["jwt", "security"],
            }])
        )
        lessons_add(args)

        # Promote it
        from lessons import cmd_promote
        promote_args = SimpleNamespace(lesson_id="L-001", scope="backend", weight=None)
        cmd_promote(promote_args)

        # Check global guidelines
        global_path = Path("forge_output") / "_global" / "guidelines.json"
        assert global_path.exists()
        global_data = json.loads(global_path.read_text(encoding="utf-8"))
        promoted = [g for g in global_data["guidelines"] if g.get("promoted_from") == "L-001"]
        assert len(promoted) == 1
        assert promoted[0]["weight"] == "must"  # critical → must
        assert promoted[0]["scope"] == "backend"


class TestGuidelinesImport:
    """Tests for guidelines import command."""

    def test_import_from_another_project(self, forge_env):
        """Import guidelines from source project to target."""
        source = "source-proj"
        target = "target-proj"
        Path("forge_output", source).mkdir(parents=True, exist_ok=True)
        Path("forge_output", target).mkdir(parents=True, exist_ok=True)

        # Add guidelines to source
        cmd_add(_add_args(source, [
            {"title": "Rule A", "scope": "backend", "content": "Do A", "weight": "must"},
            {"title": "Rule B", "scope": "frontend", "content": "Do B"},
        ]))

        # Import to target
        from guidelines import cmd_import
        import_args = SimpleNamespace(project=target, source=source, scope=None)
        cmd_import(import_args)

        target_store = load_or_create(target)
        assert len(target_store["guidelines"]) == 2
        # Check imported_from tracking
        assert "source-proj" in target_store["guidelines"][0].get("rationale", "")

    def test_import_dedup_by_title(self, forge_env):
        """Duplicate titles should be skipped during import."""
        source = "src-proj"
        target = "tgt-proj"
        Path("forge_output", source).mkdir(parents=True, exist_ok=True)
        Path("forge_output", target).mkdir(parents=True, exist_ok=True)

        cmd_add(_add_args(source, [
            {"title": "Same Rule", "scope": "general", "content": "Content"},
        ]))
        cmd_add(_add_args(target, [
            {"title": "Same Rule", "scope": "general", "content": "Already here"},
        ]))

        from guidelines import cmd_import
        cmd_import(SimpleNamespace(project=target, source=source, scope=None))

        target_store = load_or_create(target)
        assert len(target_store["guidelines"]) == 1  # no duplicate added
