"""P5.3 — Plan validation gate for source-doc traceability.

When the project ingested source documents (Knowledge.category in
{'source-document', 'feature-spec', 'requirement'}), every feature/bug/develop
task in a generated plan must declare which source fragment it implements.
Otherwise the plan re-creates the pilot's accountability gap: 10 tasks DONE,
nobody can answer "which SOW paragraph did T-005 satisfy?".

This module is pure: it takes the raw `tasks_data` list (the dict shape Claude
returned) plus a flag for whether the project has source docs, and returns a
list of violation messages. Empty list = the gate passes.

Why a helper module: the same logic is exercised both by the live plan endpoint
and by tests (without spinning a real LLM call)."""
from __future__ import annotations

import re


# Tasks where traceability is non-negotiable. chore/investigation/analysis are
# legitimately allowed to skip refs (housekeeping, exploration, ingestion).
_REQUIRES_REFS_TYPES: frozenset[str] = frozenset({"feature", "bug", "develop"})


# Token shape we accept in requirement_refs. Generous on purpose:
#   SRC-001
#   SRC-001 §2.4
#   SRC-001 punkt 3
#   SRC-001 sec 4.2
_REF_TOKEN_RE = re.compile(r"^[A-Z]+-\d+(\s.+)?$")


def _is_well_formed(ref: object) -> bool:
    if not isinstance(ref, str):
        return False
    s = ref.strip()
    if not s:
        return False
    return bool(_REF_TOKEN_RE.match(s))


def validate_plan_requirement_refs(
    tasks_data: list[dict],
    *,
    project_has_source_docs: bool,
) -> list[str]:
    """Return a list of human-readable violations. Empty list = gate passes.

    Rules (only applied when `project_has_source_docs=True`):
      1. Every feature/bug/develop task must have a non-empty `requirement_refs` list.
      2. Each ref must look like `SRC-NNN` optionally followed by a fragment locator.
    """
    if not project_has_source_docs:
        return []
    if not tasks_data:
        return []

    violations: list[str] = []
    for t in tasks_data:
        if not isinstance(t, dict):
            continue
        ttype = (t.get("type") or "feature").lower()
        if ttype not in _REQUIRES_REFS_TYPES:
            continue
        ext = t.get("external_id") or t.get("name") or "(unnamed)"
        refs = t.get("requirement_refs")
        if not refs or not isinstance(refs, list):
            violations.append(
                f"{ext} ({ttype}): requirement_refs is empty — must reference at "
                f"least one source-doc token (e.g. 'SRC-001 §2.4'). "
                f"Project has source documents; traceability is mandatory."
            )
            continue
        bad_tokens = [r for r in refs if not _is_well_formed(r)]
        if bad_tokens:
            preview = ", ".join(repr(r)[:60] for r in bad_tokens[:3])
            violations.append(
                f"{ext} ({ttype}): requirement_refs contains malformed tokens "
                f"({preview}). Expected `SRC-NNN [fragment]` form."
            )
    return violations
