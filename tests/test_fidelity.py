"""Tests for Fidelity Chain — semantic comparison utilities and checks."""

import sys
from pathlib import Path

import pytest

# Add core/ to path
FORGE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(FORGE_ROOT / "core"))

from pipeline_context import _extract_key_terms, _term_overlap, FIDELITY_STOP_WORDS


# ---------------------------------------------------------------------------
# _extract_key_terms
# ---------------------------------------------------------------------------

class TestExtractKeyTerms:

    def test_basic_extraction(self):
        terms = _extract_key_terms("eligible invoices with priority controls")
        assert "eligible" in terms
        assert "invoices" in terms
        assert "priority" in terms
        assert "controls" in terms

    def test_stop_words_filtered(self):
        terms = _extract_key_terms("must create this task with build pattern")
        assert "must" not in terms
        assert "create" not in terms
        assert "this" not in terms
        assert "with" not in terms
        assert "task" not in terms
        assert "build" not in terms
        assert "pattern" not in terms  # in stop words

    def test_short_terms_filtered(self):
        terms = _extract_key_terms("a is on UI at DB")
        assert len(terms) == 0  # all < 4 chars

    def test_empty_input(self):
        assert _extract_key_terms("") == set()
        assert _extract_key_terms(None) == set()

    def test_punctuation_split(self):
        terms = _extract_key_terms("user_email;country_code/priority_order")
        assert "user" in terms
        assert "email" in terms
        assert "country" in terms
        assert "code" in terms
        assert "priority" in terms
        assert "order" in terms

    def test_min_length_parameter(self):
        terms = _extract_key_terms("eligible invoices batch", min_length=6)
        assert "eligible" in terms
        assert "invoices" in terms
        assert "batch" not in terms  # 5 chars < min_length 6

    def test_case_insensitive(self):
        terms = _extract_key_terms("Eligible INVOICES Priority")
        assert "eligible" in terms
        assert "invoices" in terms
        assert "priority" in terms


# ---------------------------------------------------------------------------
# _term_overlap
# ---------------------------------------------------------------------------

class TestTermOverlap:

    def test_full_overlap(self):
        source = {"eligible", "invoices", "priority"}
        target = {"eligible", "invoices", "priority", "controls"}
        matched, missing, ratio = _term_overlap(source, target)
        assert matched == source
        assert missing == set()
        assert ratio == 1.0

    def test_no_overlap(self):
        source = {"eligible", "invoices"}
        target = {"buttons", "controls"}
        matched, missing, ratio = _term_overlap(source, target)
        assert matched == set()
        assert missing == source
        assert ratio == 0.0

    def test_partial_overlap(self):
        source = {"eligible", "invoices", "priority", "debtor"}
        target = {"priority", "invoices", "buttons"}
        matched, missing, ratio = _term_overlap(source, target)
        assert matched == {"priority", "invoices"}
        assert missing == {"eligible", "debtor"}
        assert ratio == 0.5

    def test_empty_source(self):
        matched, missing, ratio = _term_overlap(set(), {"something"})
        assert ratio == 0.0
        assert matched == set()


# ---------------------------------------------------------------------------
# Compound requirement detection (knowledge.py)
# ---------------------------------------------------------------------------

class TestCompoundDetection:

    def test_short_content_no_warning(self, capsys):
        """Short content with 'and' should NOT warn (< 100 chars)."""
        from knowledge import Knowledge
        Knowledge._warn_compound_requirement("Invoice and customer priority", "K-001")
        captured = capsys.readouterr()
        assert "FIDELITY_WARNING" not in captured.err

    def test_long_compound_warns(self, capsys):
        """Long content with 'and' connecting clauses should warn."""
        from knowledge import Knowledge
        content = (
            "System shows eligible invoices for upcoming Auto-Buy run "
            "and user can reorder invoice priorities with up/down controls "
            "and filter by customer/debtor"
        )
        Knowledge._warn_compound_requirement(content, "K-042")
        captured = capsys.readouterr()
        assert "FIDELITY_WARNING" in captured.err
        assert "K-042" in captured.err
        assert "compound" in captured.err

    def test_long_without_markers_warns_on_length(self, capsys):
        """Content > 200 chars without compound markers should warn on length."""
        from knowledge import Knowledge
        content = "x" * 201
        Knowledge._warn_compound_requirement(content, "K-099")
        captured = capsys.readouterr()
        assert "FIDELITY_WARNING" in captured.err
        assert "201 chars" in captured.err


# ---------------------------------------------------------------------------
# Semantic coverage gap detection
# ---------------------------------------------------------------------------

class TestSemanticCoverage:

    def test_semantic_gap_detected(self, forge_env, project_name):
        """Task instruction missing key terms from requirement should produce SEMANTIC_GAP."""
        import json
        from pipeline_planning import _check_semantic_coverage

        # Set up knowledge with a requirement
        project_dir = forge_env / "forge_output" / project_name
        project_dir.mkdir(parents=True)
        knowledge_data = {
            "knowledge": [{
                "id": "K-003",
                "title": "Priority UI shows eligible invoices",
                "category": "requirement",
                "status": "ACTIVE",
                "content": "Frontend shows list of eligible invoices for upcoming Auto-Buy run with filter by debtor and cut-off time display",
            }]
        }
        (project_dir / "knowledge.json").write_text(json.dumps(knowledge_data))

        # Task instruction that diverges from requirement
        draft_tasks = [{
            "id": "_1",
            "name": "priority-crud-page",
            "description": "CRUD page for priorities",
            "instruction": "Create page with table showing priorities. Add/delete buttons. Country selector.",
            "knowledge_ids": ["K-003"],
        }]

        warnings = _check_semantic_coverage(draft_tasks, project_name)
        assert len(warnings) >= 1
        assert "SEMANTIC_GAP" in warnings[0]
        assert "K-003" in warnings[0]

    def test_no_gap_when_terms_match(self, forge_env, project_name):
        """Task instruction with matching terms should produce no warnings."""
        import json
        from pipeline_planning import _check_semantic_coverage

        project_dir = forge_env / "forge_output" / project_name
        project_dir.mkdir(parents=True)
        knowledge_data = {
            "knowledge": [{
                "id": "K-010",
                "title": "Up/down priority controls",
                "category": "requirement",
                "status": "ACTIVE",
                "content": "User can reorder invoice priorities with up/down arrow controls",
            }]
        }
        (project_dir / "knowledge.json").write_text(json.dumps(knowledge_data))

        draft_tasks = [{
            "id": "_1",
            "name": "priority-reorder",
            "instruction": "Add up/down arrow buttons to reorder invoice priorities in the table.",
            "knowledge_ids": ["K-010"],
        }]

        warnings = _check_semantic_coverage(draft_tasks, project_name)
        assert len(warnings) == 0


# ---------------------------------------------------------------------------
# Cross-objective task overlap detection
# ---------------------------------------------------------------------------

class TestCompletedTaskOverlap:

    def test_overlap_detected_cross_objective(self, forge_env, project_name):
        """New task duplicating DONE task from different objective should produce OVERLAP."""
        import json
        from pipeline_planning import _check_completed_task_overlap

        project_dir = forge_env / "forge_output" / project_name
        project_dir.mkdir(parents=True)

        # Existing tracker with a DONE task
        tracker = {
            "tasks": [{
                "id": "T-025",
                "name": "settings-auto-schedules",
                "description": "Auto-buy schedule configuration per country",
                "instruction": "Add toggle auto-buy enabled, purchase day selector, save schedule per country",
                "status": "DONE",
                "origin": "O-003",
            }]
        }
        (project_dir / "tracker.json").write_text(json.dumps(tracker))

        # New task from different objective that duplicates
        draft_tasks = [{
            "id": "_1",
            "name": "schedule-maintenance-page",
            "description": "Auto-buy schedule configuration per country with grid",
            "instruction": "Create page with toggle auto-buy enabled, purchase day selector, save schedule per country, add country modal",
            "origin": "O-014",
        }]

        warnings = _check_completed_task_overlap(draft_tasks, project_name)
        assert len(warnings) >= 1
        assert "OVERLAP" in warnings[0]
        assert "T-025" in warnings[0]

    def test_no_overlap_same_objective(self, forge_env, project_name):
        """Tasks from same objective should NOT trigger overlap warning."""
        import json
        from pipeline_planning import _check_completed_task_overlap

        project_dir = forge_env / "forge_output" / project_name
        project_dir.mkdir(parents=True)

        tracker = {
            "tasks": [{
                "id": "T-071",
                "name": "refactor-schedule-api",
                "description": "Refactor schedule API to v1 spec",
                "instruction": "Create 7 endpoints for schedule configuration management",
                "status": "DONE",
                "origin": "O-014",
            }]
        }
        (project_dir / "tracker.json").write_text(json.dumps(tracker))

        draft_tasks = [{
            "id": "_1",
            "name": "schedule-frontend",
            "description": "Schedule frontend page using v1 API",
            "instruction": "Build page calling schedule configuration endpoints",
            "origin": "O-014",
        }]

        warnings = _check_completed_task_overlap(draft_tasks, project_name)
        assert len(warnings) == 0

    def test_no_overlap_when_no_done_tasks(self, forge_env, project_name):
        """Empty tracker should produce no warnings."""
        import json
        from pipeline_planning import _check_completed_task_overlap

        project_dir = forge_env / "forge_output" / project_name
        project_dir.mkdir(parents=True)
        (project_dir / "tracker.json").write_text(json.dumps({"tasks": []}))

        draft_tasks = [{"id": "_1", "name": "something", "instruction": "do stuff", "origin": "O-001"}]
        warnings = _check_completed_task_overlap(draft_tasks, project_name)
        assert len(warnings) == 0


# ---------------------------------------------------------------------------
# Over-coverage detection
# ---------------------------------------------------------------------------

class TestOverCoverage:

    def test_over_coverage_detected(self, forge_env, project_name):
        """Same requirement covered by tasks from different objectives should warn."""
        import json
        from pipeline_planning import _check_over_coverage

        project_dir = forge_env / "forge_output" / project_name
        project_dir.mkdir(parents=True)

        knowledge_data = {
            "knowledge": [{
                "id": "K-024",
                "title": "Schedule config per country",
                "category": "requirement",
                "status": "ACTIVE",
                "content": "Configure auto-buy schedule per country",
            }]
        }
        (project_dir / "knowledge.json").write_text(json.dumps(knowledge_data))

        tracker = {
            "tasks": [{
                "id": "T-025",
                "name": "settings-auto-schedules",
                "status": "DONE",
                "origin": "O-003",
                "knowledge_ids": ["K-024"],
                "source_requirements": [],
            }]
        }
        (project_dir / "tracker.json").write_text(json.dumps(tracker))

        new_tasks = [{
            "id": "_1",
            "name": "schedule-maintenance",
            "origin": "O-014",
            "knowledge_ids": ["K-024"],
            "source_requirements": [],
        }]

        warnings = _check_over_coverage(new_tasks, project_name)
        assert len(warnings) >= 1
        assert "OVER_COVERAGE" in warnings[0]
        assert "K-024" in warnings[0]

    def test_no_over_coverage_same_objective(self, forge_env, project_name):
        """Same requirement covered by tasks from same objective is OK."""
        import json
        from pipeline_planning import _check_over_coverage

        project_dir = forge_env / "forge_output" / project_name
        project_dir.mkdir(parents=True)

        knowledge_data = {
            "knowledge": [{
                "id": "K-024",
                "title": "Schedule config",
                "category": "requirement",
                "status": "ACTIVE",
                "content": "Configure schedule",
            }]
        }
        (project_dir / "knowledge.json").write_text(json.dumps(knowledge_data))

        tracker = {
            "tasks": [{
                "id": "T-071",
                "status": "DONE",
                "origin": "O-014",
                "knowledge_ids": ["K-024"],
                "source_requirements": [],
            }]
        }
        (project_dir / "tracker.json").write_text(json.dumps(tracker))

        new_tasks = [{
            "id": "_1",
            "origin": "O-014",
            "knowledge_ids": ["K-024"],
            "source_requirements": [],
        }]

        warnings = _check_over_coverage(new_tasks, project_name)
        assert len(warnings) == 0


# ---------------------------------------------------------------------------
# Feature Registry
# ---------------------------------------------------------------------------

class TestFeatureRegistry:

    def test_extract_routes_from_diff(self):
        from feature_registry import _extract_routes_from_diff
        diff = '''
+@router.get("/api/priorities/lock-status")
+    router.push("/itrp/settings")
+app/maintenance/autobuy-schedule/page.tsx
'''
        routes = _extract_routes_from_diff(diff)
        assert "/api/priorities/lock-status" in routes
        assert "/itrp/settings" in routes
        assert "/maintenance/autobuy-schedule" in routes

    def test_extract_components_from_diff(self):
        from feature_registry import _extract_components_from_diff
        diff = '''
+export default function AutoBuySchedulePage() {
+export function AddCountryModal({ open }) {
+router = APIRouter(prefix="/api/v1/schedule")
'''
        components = _extract_components_from_diff(diff)
        assert "AutoBuySchedulePage" in components
        assert "AddCountryModal" in components
        assert "router:/api/v1/schedule" in components

    def test_register_and_check_conflict(self, forge_env, project_name):
        """Full round-trip: register feature, then check for conflict."""
        import json
        from feature_registry import register_feature, check_conflicts

        project_dir = forge_env / "forge_output" / project_name
        project_dir.mkdir(parents=True)

        # Register a feature
        task = {
            "id": "T-025",
            "name": "settings-auto-schedules",
            "origin": "O-003",
            "instruction": "Build auto-buy schedule UI in /itrp/settings page",
            "description": "Auto schedules configuration per country",
            "scopes": ["frontend"],
        }
        diff = '+app/itrp/settings/page.tsx\n+router.push("/itrp/settings")'
        register_feature(project_name, task, diff)

        # Check that a new task creating same route conflicts
        new_tasks = [{
            "id": "_1",
            "name": "schedule-maintenance-page",
            "origin": "O-014",
            "instruction": "Create new page at app/itrp/settings/autobuy for schedule config",
            "description": "Schedule maintenance with grid for all countries",
        }]
        warnings = check_conflicts(project_name, new_tasks)
        # Should detect feature overlap via key terms
        assert len(warnings) >= 1
        assert "FEATURE" in warnings[0]

    def test_no_conflict_same_objective(self, forge_env, project_name):
        """Features from same objective should not conflict."""
        import json
        from feature_registry import register_feature, check_conflicts

        project_dir = forge_env / "forge_output" / project_name
        project_dir.mkdir(parents=True)

        register_feature(project_name, {
            "id": "T-071", "name": "api-refactor", "origin": "O-014",
            "instruction": "Refactor schedule API endpoints", "description": "7 schedule endpoints",
            "scopes": ["backend"],
        }, '+@router.get("/api/v1/schedule/config")')

        new_tasks = [{
            "id": "_1", "name": "schedule-frontend", "origin": "O-014",
            "instruction": "Build frontend calling /api/v1/schedule/config",
            "description": "Schedule UI",
        }]
        warnings = check_conflicts(project_name, new_tasks)
        # Same objective — route reference is expected, not a conflict
        route_conflicts = [w for w in warnings if "FEATURE_CONFLICT" in w]
        assert len(route_conflicts) == 0
