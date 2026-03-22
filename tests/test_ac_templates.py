"""Tests for core.ac_templates — PROPOSED status, occurrences, source_tasks."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))

from ac_templates import (
    CONTRACTS,
    cmd_add,
    cmd_read,
    cmd_show,
    cmd_update,
    cmd_instantiate,
    load_or_create,
    save_json,
    find_template,
)
from contracts import validate_contract
from errors import PreconditionError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_project(tmp_path, monkeypatch):
    """Create a temporary project directory for ac_templates."""
    project = "test-proj"
    project_dir = tmp_path / "forge_output" / project
    project_dir.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    return project


def make_args(**kwargs):
    return SimpleNamespace(**kwargs)


def add_template(project, template_data):
    """Helper to add a template via cmd_add."""
    args = make_args(project=project, data=json.dumps(template_data))
    cmd_add(args)


# ---------------------------------------------------------------------------
# Contract validation
# ---------------------------------------------------------------------------

class TestContracts:
    """Verify contract accepts new fields."""

    def test_add_contract_accepts_proposed_status(self):
        items = [{
            "title": "Test Template",
            "template": "Endpoint {path} returns 200",
            "category": "functionality",
            "status": "PROPOSED",
            "source_tasks": ["T-001"],
            "occurrences": 1,
        }]
        errors = validate_contract(CONTRACTS["add"], items)
        assert errors == []

    def test_add_contract_rejects_invalid_status(self):
        items = [{
            "title": "Test",
            "template": "Test {x}",
            "category": "quality",
            "status": "INVALID",
        }]
        errors = validate_contract(CONTRACTS["add"], items)
        assert any("status" in e for e in errors)

    def test_update_contract_accepts_occurrences(self):
        items = [{"id": "AC-001", "occurrences": 5, "source_tasks": ["T-010"]}]
        errors = validate_contract(CONTRACTS["update"], items)
        assert errors == []

    def test_update_contract_accepts_proposed_status(self):
        items = [{"id": "AC-001", "status": "PROPOSED"}]
        errors = validate_contract(CONTRACTS["update"], items)
        assert errors == []


# ---------------------------------------------------------------------------
# cmd_add — PROPOSED templates
# ---------------------------------------------------------------------------

class TestAddProposed:
    """Test adding templates with PROPOSED status."""

    def test_add_proposed_stores_status(self, tmp_project):
        add_template(tmp_project, [{
            "title": "Response check",
            "template": "API returns {status_code}",
            "category": "functionality",
            "status": "PROPOSED",
            "source_tasks": ["T-001", "T-003"],
        }])
        data = load_or_create(tmp_project)
        t = data["ac_templates"][0]
        assert t["status"] == "PROPOSED"
        assert t["source_tasks"] == ["T-001", "T-003"]
        assert t["occurrences"] == 1

    def test_add_default_status_is_active(self, tmp_project):
        add_template(tmp_project, [{
            "title": "Perf check",
            "template": "Responds within {ms}ms",
            "category": "performance",
        }])
        data = load_or_create(tmp_project)
        assert data["ac_templates"][0]["status"] == "ACTIVE"

    def test_add_with_explicit_occurrences(self, tmp_project):
        add_template(tmp_project, [{
            "title": "Security check",
            "template": "Input {field} is sanitized",
            "category": "security",
            "status": "PROPOSED",
            "occurrences": 3,
            "source_tasks": ["T-001", "T-002", "T-005"],
        }])
        data = load_or_create(tmp_project)
        assert data["ac_templates"][0]["occurrences"] == 3


# ---------------------------------------------------------------------------
# cmd_update — occurrences and source_tasks
# ---------------------------------------------------------------------------

class TestUpdateProposed:
    """Test updating PROPOSED templates."""

    def test_update_increments_occurrences(self, tmp_project):
        add_template(tmp_project, [{
            "title": "Error handling",
            "template": "Endpoint {path} returns proper error on {error_type}",
            "category": "quality",
            "status": "PROPOSED",
            "source_tasks": ["T-001"],
        }])
        data = load_or_create(tmp_project)
        ac_id = data["ac_templates"][0]["id"]

        args = make_args(project=tmp_project, data=json.dumps([
            {"id": ac_id, "occurrences": 2, "source_tasks": ["T-005"]}
        ]))
        cmd_update(args)

        data = load_or_create(tmp_project)
        t = find_template(data, ac_id)
        assert t["occurrences"] == 2
        assert t["source_tasks"] == ["T-001", "T-005"]

    def test_source_tasks_append_merge_no_duplicates(self, tmp_project):
        add_template(tmp_project, [{
            "title": "Validation",
            "template": "Field {name} validates {rule}",
            "category": "quality",
            "status": "PROPOSED",
            "source_tasks": ["T-001", "T-002"],
        }])
        data = load_or_create(tmp_project)
        ac_id = data["ac_templates"][0]["id"]

        args = make_args(project=tmp_project, data=json.dumps([
            {"id": ac_id, "source_tasks": ["T-002", "T-003"]}
        ]))
        cmd_update(args)

        data = load_or_create(tmp_project)
        t = find_template(data, ac_id)
        # T-002 should not be duplicated
        assert t["source_tasks"] == ["T-001", "T-002", "T-003"]

    def test_promote_proposed_to_active(self, tmp_project):
        add_template(tmp_project, [{
            "title": "Auth check",
            "template": "Endpoint {path} requires authentication",
            "category": "security",
            "status": "PROPOSED",
        }])
        data = load_or_create(tmp_project)
        ac_id = data["ac_templates"][0]["id"]

        args = make_args(project=tmp_project, data=json.dumps([
            {"id": ac_id, "status": "ACTIVE"}
        ]))
        cmd_update(args)

        data = load_or_create(tmp_project)
        assert find_template(data, ac_id)["status"] == "ACTIVE"


# ---------------------------------------------------------------------------
# cmd_instantiate — PROPOSED guard
# ---------------------------------------------------------------------------

class TestInstantiateGuard:
    """PROPOSED templates cannot be instantiated."""

    def test_instantiate_proposed_exits(self, tmp_project):
        add_template(tmp_project, [{
            "title": "Rate limit",
            "template": "Endpoint {path} has rate limit of {rps} req/s",
            "category": "security",
            "status": "PROPOSED",
        }])
        data = load_or_create(tmp_project)
        ac_id = data["ac_templates"][0]["id"]

        args = make_args(
            project=tmp_project,
            template_id=ac_id,
            params='{"path": "/api/test", "rps": 100}',
        )
        with pytest.raises(PreconditionError):
            cmd_instantiate(args)

    def test_instantiate_active_succeeds(self, tmp_project, capsys):
        add_template(tmp_project, [{
            "title": "Rate limit",
            "template": "Endpoint {path} has rate limit of {rps} req/s",
            "category": "security",
            "status": "ACTIVE",
            "parameters": [
                {"name": "path", "type": "string"},
                {"name": "rps", "type": "number"},
            ],
        }])
        # Clear the add output
        capsys.readouterr()

        data = load_or_create(tmp_project)
        ac_id = data["ac_templates"][0]["id"]

        args = make_args(
            project=tmp_project,
            template_id=ac_id,
            params='{"path": "/api/test", "rps": 100}',
        )
        cmd_instantiate(args)
        out = capsys.readouterr().out
        result = json.loads(out)
        assert result["text"] == "Endpoint /api/test has rate limit of 100 req/s"
