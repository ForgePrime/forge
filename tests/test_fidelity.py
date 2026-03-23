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
