"""Centralized constants for Forge core.

Single source of truth for status values, entity types, ID prefixes,
and configuration defaults. Replaces magic strings scattered across modules.
"""

from enum import Enum


# -- Task --

class TaskStatus(str, Enum):
    TODO = "TODO"
    CLAIMING = "CLAIMING"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


TERMINAL_TASK_STATUSES = frozenset({
    TaskStatus.DONE, TaskStatus.FAILED, TaskStatus.SKIPPED,
})


class TaskType(str, Enum):
    FEATURE = "feature"
    BUG = "bug"
    CHORE = "chore"
    INVESTIGATION = "investigation"


GATE_EXEMPT_TASK_TYPES = frozenset({TaskType.CHORE, TaskType.INVESTIGATION})


class CeremonyLevel(str, Enum):
    MINIMAL = "MINIMAL"
    LIGHT = "LIGHT"
    STANDARD = "STANDARD"
    FULL = "FULL"


# -- Decisions --

class DecisionStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    DEFERRED = "DEFERRED"
    ANALYZING = "ANALYZING"
    MITIGATED = "MITIGATED"
    ACCEPTED = "ACCEPTED"


class DecisionType(str, Enum):
    STANDARD = "standard"
    EXPLORATION = "exploration"
    RISK = "risk"


# -- Guidelines --

class GuidelineWeight(str, Enum):
    MUST = "must"
    SHOULD = "should"
    MAY = "may"


# -- Shared entity status --

class EntityStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    ARCHIVED = "ARCHIVED"
    DRAFT = "DRAFT"


# -- ID prefixes --

ID_PREFIXES = {
    "tasks": "T",
    "guidelines": "G",
    "lessons": "L",
    "knowledge": "K",
    "ideas": "I",
    "objectives": "O",
    "decisions": "D",
    "changes": "C",
    "ac_templates": "AC",
    "research": "R",
}


# -- Display --

STATUS_ICONS = {
    TaskStatus.TODO: "[ ]",
    TaskStatus.CLAIMING: "[?]",
    TaskStatus.IN_PROGRESS: "[>]",
    TaskStatus.DONE: "[x]",
    TaskStatus.SKIPPED: "[-]",
    TaskStatus.FAILED: "[!]",
}


# -- Timeouts & limits --

CLAIM_WAIT_SECONDS = 1.5
TRACKER_LOCK_TIMEOUT = 30.0
AC_VERIFICATION_TIMEOUT = 120
MIN_AC_REASONING_LENGTH = 50
MIN_SKIP_REASON_LENGTH = 50
