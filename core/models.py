"""Forge domain models — typed dataclasses for all entity types.

These models provide:
- Type safety and IDE support (autocomplete, type checking)
- from_dict() / to_dict() for gradual adoption alongside raw dicts
- Lossless round-trips: unknown keys survive via _extras overflow
- Documentation of every field and its default

Models do NOT own validation — that stays in contracts.py.
Models do NOT change the JSON format — to_dict() produces identical output.

Usage:
    task = Task.from_dict(raw_dict)
    task.status  # attribute access instead of .get("status")
    raw_dict = task.to_dict()  # back to dict for storage
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, asdict
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Helpers — lossless round-trip with _extras overflow
# ---------------------------------------------------------------------------

def _from_dict(cls, d: dict):
    """Construct a dataclass from a raw dict.

    - Known keys → dataclass fields
    - Unknown keys → _extras dict (preserved in to_dict)
    """
    known = {f.name for f in fields(cls)} - {"_extras"}
    filtered = {k: v for k, v in d.items() if k in known}
    extras = {k: v for k, v in d.items() if k not in known}
    obj = cls(**filtered)
    object.__setattr__(obj, "_extras", extras)
    return obj


def _to_dict(obj) -> dict:
    """Serialize dataclass to dict.

    - Drops None values (optional fields not set)
    - Preserves falsy values: 0, False, "", []
    - Merges _extras back in (unknown keys from from_dict)
    """
    result = {}
    for k, v in asdict(obj).items():
        if k == "_extras":
            continue
        if v is not None:
            result[k] = v
    result.update(getattr(obj, "_extras", {}))
    return result


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

@dataclass
class Task:
    id: str = ""
    name: str = ""
    description: str = ""
    instruction: str = ""
    status: str = "TODO"
    type: str = "feature"
    depends_on: list[str] = field(default_factory=list)
    parallel: bool = False
    conflicts_with: list[str] = field(default_factory=list)
    skill: Optional[str] = None
    acceptance_criteria: list = field(default_factory=list)
    blocked_by_decisions: list[str] = field(default_factory=list)
    scopes: list[str] = field(default_factory=list)
    origin: str = ""
    knowledge_ids: list[str] = field(default_factory=list)
    alignment: Optional[dict] = None
    exclusions: list[str] = field(default_factory=list)
    produces: Optional[dict] = None
    test_requirements: Optional[dict] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    failed_reason: Optional[str] = None
    agent: Optional[str] = None
    # Subtask fields
    has_subtasks: bool = False
    subtask_total: int = 0
    subtask_done: int = 0
    subtasks: list[dict] = field(default_factory=list)
    # Runtime fields (set during execution, not at creation)
    started_at_commit: Optional[str] = None
    branch: Optional[str] = None
    worktree_path: Optional[str] = None
    claimed_at: Optional[str] = None
    gate_results: Optional[dict] = None
    ceremony_level: Optional[str] = None
    completion_trace: Optional[dict] = None
    ac_verification_results: Optional[list] = None
    ac_reasoning: Optional[str] = None
    deferred_decisions: Optional[list] = None
    skip_reason: Optional[str] = None
    # Overflow for unknown keys
    _extras: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: dict) -> Task:
        return _from_dict(cls, d)

    def to_dict(self) -> dict:
        return _to_dict(self)


# ---------------------------------------------------------------------------
# Decision
# ---------------------------------------------------------------------------

@dataclass
class Decision:
    id: str = ""
    task_id: str = ""
    type: str = ""
    issue: str = ""
    recommendation: str = ""
    reasoning: str = ""
    alternatives: list[str] = field(default_factory=list)
    confidence: str = "MEDIUM"
    status: str = "OPEN"
    decided_by: str = "claude"
    file: str = ""
    scope: str = ""
    timestamp: str = ""
    tags: list[str] = field(default_factory=list)
    # Exploration fields
    exploration_type: str = ""
    findings: list = field(default_factory=list)
    options: list = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    ready_for_tracker: bool = False
    evidence_refs: list[str] = field(default_factory=list)
    # Risk fields
    severity: str = ""
    likelihood: str = ""
    linked_entity_type: str = ""
    linked_entity_id: str = ""
    mitigation_plan: str = ""
    resolution_notes: str = ""
    # Update fields
    action: Optional[str] = None
    override_value: Optional[str] = None
    override_reason: Optional[str] = None
    updated: Optional[str] = None
    _extras: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: dict) -> Decision:
        return _from_dict(cls, d)

    def to_dict(self) -> dict:
        return _to_dict(self)


# ---------------------------------------------------------------------------
# Change
# ---------------------------------------------------------------------------

@dataclass
class Change:
    id: str = ""
    task_id: str = ""
    file: str = ""
    action: str = ""
    summary: str = ""
    reasoning_trace: list[dict] = field(default_factory=list)
    decision_ids: list[str] = field(default_factory=list)
    lines_added: int = 0
    lines_removed: int = 0
    group_id: str = ""
    guidelines_checked: list[str] = field(default_factory=list)
    timestamp: str = ""
    _extras: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: dict) -> Change:
        return _from_dict(cls, d)

    def to_dict(self) -> dict:
        return _to_dict(self)


# ---------------------------------------------------------------------------
# Guideline
# ---------------------------------------------------------------------------

@dataclass
class Guideline:
    id: str = ""
    title: str = ""
    scope: str = ""
    content: str = ""
    rationale: str = ""
    examples: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    weight: str = "should"
    derived_from: str = ""
    status: str = "ACTIVE"
    created: str = ""
    updated: str = ""
    promoted_from: Optional[str] = None
    imported_from: Optional[str] = None
    _extras: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: dict) -> Guideline:
        return _from_dict(cls, d)

    def to_dict(self) -> dict:
        return _to_dict(self)


# ---------------------------------------------------------------------------
# Lesson
# ---------------------------------------------------------------------------

@dataclass
class Lesson:
    id: str = ""
    category: str = ""
    title: str = ""
    detail: str = ""
    task_id: str = ""
    decision_ids: list[str] = field(default_factory=list)
    severity: str = "important"
    applies_to: str = ""
    tags: list[str] = field(default_factory=list)
    project: str = ""
    timestamp: str = ""
    promoted_to_guideline: Optional[str] = None
    promoted_to_knowledge: Optional[str] = None
    _extras: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: dict) -> Lesson:
        return _from_dict(cls, d)

    def to_dict(self) -> dict:
        return _to_dict(self)


# ---------------------------------------------------------------------------
# Knowledge
# ---------------------------------------------------------------------------

@dataclass
class KnowledgeVersion:
    version: int = 1
    content: str = ""
    changed_by: str = ""
    changed_at: str = ""
    change_reason: str = ""
    _extras: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: dict) -> KnowledgeVersion:
        return _from_dict(cls, d)

    def to_dict(self) -> dict:
        return _to_dict(self)


@dataclass
class Knowledge:
    id: str = ""
    title: str = ""
    category: str = ""
    content: str = ""
    status: str = "DRAFT"
    version: int = 1
    scopes: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    source: dict = field(default_factory=dict)
    linked_entities: list[dict] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    versions: list[dict] = field(default_factory=list)
    review: dict = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    created_by: str = "user"
    _extras: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: dict) -> Knowledge:
        return _from_dict(cls, d)

    def to_dict(self) -> dict:
        return _to_dict(self)


# ---------------------------------------------------------------------------
# Idea
# ---------------------------------------------------------------------------

@dataclass
class Idea:
    id: str = ""
    title: str = ""
    description: str = ""
    category: str = "feature"
    priority: str = "MEDIUM"
    tags: list[str] = field(default_factory=list)
    related_ideas: list[str] = field(default_factory=list)
    guidelines: list[str] = field(default_factory=list)
    parent_id: Optional[str] = None
    relations: list[dict] = field(default_factory=list)
    scopes: list[str] = field(default_factory=list)
    advances_key_results: list[str] = field(default_factory=list)
    knowledge_ids: list[str] = field(default_factory=list)
    status: str = "DRAFT"
    rejection_reason: str = ""
    merged_into: str = ""
    exploration_notes: str = ""
    committed_at: Optional[str] = None
    created: str = ""
    updated: str = ""
    _extras: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: dict) -> Idea:
        return _from_dict(cls, d)

    def to_dict(self) -> dict:
        return _to_dict(self)


# ---------------------------------------------------------------------------
# Key Result (nested in Objective)
# ---------------------------------------------------------------------------

@dataclass
class KeyResult:
    id: str = ""
    metric: Optional[str] = None
    baseline: float = 0
    target: Optional[float] = None
    current: Optional[float] = None
    description: Optional[str] = None
    status: Optional[str] = None
    _extras: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: dict) -> KeyResult:
        return _from_dict(cls, d)

    def to_dict(self) -> dict:
        return _to_dict(self)


# ---------------------------------------------------------------------------
# Objective
# ---------------------------------------------------------------------------

@dataclass
class Objective:
    id: str = ""
    title: str = ""
    description: str = ""
    key_results: list[dict] = field(default_factory=list)
    appetite: str = "medium"
    scope: str = "project"
    assumptions: list = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    scopes: list[str] = field(default_factory=list)
    derived_guidelines: list[str] = field(default_factory=list)
    knowledge_ids: list[str] = field(default_factory=list)
    guideline_ids: list[str] = field(default_factory=list)
    relations: list[dict] = field(default_factory=list)
    status: str = "ACTIVE"
    created: str = ""
    updated: str = ""
    _extras: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: dict) -> Objective:
        return _from_dict(cls, d)

    def to_dict(self) -> dict:
        return _to_dict(self)


# ---------------------------------------------------------------------------
# Research
# ---------------------------------------------------------------------------

@dataclass
class Research:
    id: str = ""
    title: str = ""
    topic: str = ""
    status: str = "DRAFT"
    category: str = ""
    linked_entity_type: Optional[str] = None
    linked_entity_id: Optional[str] = None
    linked_idea_id: Optional[str] = None
    skill: Optional[str] = None
    file_path: Optional[str] = None
    summary: str = ""
    key_findings: list[str] = field(default_factory=list)
    decision_ids: list[str] = field(default_factory=list)
    scopes: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    created_by: str = "claude"
    _extras: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: dict) -> Research:
        return _from_dict(cls, d)

    def to_dict(self) -> dict:
        return _to_dict(self)


# ---------------------------------------------------------------------------
# AC Template
# ---------------------------------------------------------------------------

@dataclass
class AcTemplate:
    id: str = ""
    title: str = ""
    description: str = ""
    template: str = ""
    category: str = ""
    parameters: list[dict] = field(default_factory=list)
    scopes: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    verification_method: str = ""
    status: str = "ACTIVE"
    usage_count: int = 0
    occurrences: int = 1
    source_tasks: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    _extras: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: dict) -> AcTemplate:
        return _from_dict(cls, d)

    def to_dict(self) -> dict:
        return _to_dict(self)
