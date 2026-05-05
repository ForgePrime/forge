"""SemanticRelationTypes — Phase B Stage B.6.

Closes ECITP C6 (topology preservation). The free-form
`causal_edges.relation TEXT` from B.1 is augmented with a typed ENUM
that captures semantic class — requirement_of / risk_of / ac_of /
test_of / etc.

Per PLAN_MEMORY_CONTEXT B.6 + ECITP §3 C6:
    Semantic dependency relations (requirement <-> risk <-> AC <-> test)
    survive transfer via relation_semantic ENUM. CausalGraph exposes
    relation-typed queries.

Pure-Python: this module ships
- The ENUM (RelationSemantic)
- The deterministic backfill mapping table (TEXT -> ENUM)
- A backfill function over a list of free-form relation strings

The DB column migration + the extension to CausalGraph (requirements_of,
risks_of, tests_of) are downstream of this module. The CausalGraph
extension methods are added below using the existing EdgeView shape so
no new DB queries are needed.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from app.evidence.causal_graph import EdgeSource, EdgeView, Node, ancestors


class RelationSemantic(str, Enum):
    """Closed enum per PLAN A_{B.6}. Extension via ADR.

    Order matters for documentation: requirement -> risk -> AC -> test
    is the canonical ECITP C6 chain.
    """

    REQUIREMENT_OF = "requirement_of"
    RISK_OF = "risk_of"
    AC_OF = "ac_of"
    TEST_OF = "test_of"
    MITIGATES = "mitigates"
    DERIVES_FROM = "derives_from"
    PRODUCES = "produces"
    BLOCKS = "blocks"
    VERIFIES = "verifies"
    EVIDENCES = "evidences"


# Deterministic backfill table: maps free-form `relation TEXT` values
# (as written in B.1 CausalEdge or backfilled from B.2) to the typed
# RelationSemantic enum. Unmapped entries return None per
# PLAN_MEMORY_CONTEXT B.6 work item 2 ("Unmappable -> Finding, NULL
# retained").
#
# Keys are lowercase + canonicalized so callers can pass any casing.
_BACKFILL_MAP: dict[str, RelationSemantic] = {
    # requirement_of
    "requirement_of": RelationSemantic.REQUIREMENT_OF,
    "requires": RelationSemantic.REQUIREMENT_OF,
    "implements_requirement": RelationSemantic.REQUIREMENT_OF,
    "satisfies": RelationSemantic.REQUIREMENT_OF,
    # risk_of
    "risk_of": RelationSemantic.RISK_OF,
    "risk": RelationSemantic.RISK_OF,
    "risks": RelationSemantic.RISK_OF,
    # ac_of
    "ac_of": RelationSemantic.AC_OF,
    "acceptance_criterion": RelationSemantic.AC_OF,
    "ac": RelationSemantic.AC_OF,
    # test_of
    "test_of": RelationSemantic.TEST_OF,
    "tests": RelationSemantic.TEST_OF,
    "verified_by_test": RelationSemantic.TEST_OF,
    # mitigates
    "mitigates": RelationSemantic.MITIGATES,
    "mitigated_by": RelationSemantic.MITIGATES,
    # derives_from
    "derives_from": RelationSemantic.DERIVES_FROM,
    "derived_from": RelationSemantic.DERIVES_FROM,
    # produces
    "produces": RelationSemantic.PRODUCES,
    "produced_by": RelationSemantic.PRODUCES,
    # blocks
    "blocks": RelationSemantic.BLOCKS,
    "blocked_by": RelationSemantic.BLOCKS,
    # verifies
    "verifies": RelationSemantic.VERIFIES,
    "verified_by": RelationSemantic.VERIFIES,
    # evidences
    "evidences": RelationSemantic.EVIDENCES,
    "evidence": RelationSemantic.EVIDENCES,
    "evidenced_by": RelationSemantic.EVIDENCES,
    # depends_on -> common B.1 default; map to derives_from (semantic
    # closest) since "depends_on" is structural-ancestry not domain-typed.
    "depends_on": RelationSemantic.DERIVES_FROM,
}


def map_text_to_enum(relation_text: str) -> RelationSemantic | None:
    """Map a free-form relation string to a RelationSemantic.

    Case-insensitive; whitespace-trimmed. Returns None on unmapped input
    so caller can emit Finding per B.6 work item 2.

    Determinism (P6): same input -> same output.
    """
    if not relation_text:
        return None
    key = relation_text.strip().lower()
    return _BACKFILL_MAP.get(key)


@dataclass(frozen=True)
class BackfillResult:
    """Output of backfill over a batch of relation strings."""

    mapped: dict[str, RelationSemantic]  # input_text -> mapped enum
    unmapped: tuple[str, ...]  # texts that had no mapping (Finding candidates)


def backfill(relation_texts: Iterable[str]) -> BackfillResult:
    """Batch-map free-form relation strings to typed enum values.

    Args:
        relation_texts: iterable of relation strings as stored in
            causal_edges.relation TEXT.

    Returns:
        BackfillResult with mapped + unmapped sets. Idempotent: running
        twice with the same input returns the same output.
    """
    mapped: dict[str, RelationSemantic] = {}
    unmapped: list[str] = []
    seen: set[str] = set()
    for text in relation_texts:
        if text in seen:
            continue
        seen.add(text)
        result = map_text_to_enum(text)
        if result is None:
            unmapped.append(text)
        else:
            mapped[text] = result
    return BackfillResult(
        mapped=mapped,
        unmapped=tuple(sorted(unmapped)),  # sorted for determinism
    )


# ----------------------------------------------------------------------
# CausalGraph relation-typed queries (B.6 work item 3)
# ----------------------------------------------------------------------


def edges_by_relation_class(
    source: EdgeSource,
    node: Node,
    relation_class: RelationSemantic,
    *,
    depth: int = 10,
) -> list[EdgeView]:
    """Filter ancestors() by canonical relation_class.

    Walks BFS as in causal_graph.ancestors but admits an edge only if
    map_text_to_enum(edge.relation) == relation_class.

    Production caller would query DB with WHERE relation_semantic =
    enum_value directly; this implementation works on the in-memory
    EdgeSource Protocol so tests don't need DB.
    """
    matched: list[EdgeView] = []
    for edge in ancestors(source, node, depth=depth):
        if map_text_to_enum(edge.relation) == relation_class:
            matched.append(edge)
    return matched


def requirements_of(source: EdgeSource, node: Node, *, depth: int = 10) -> list[EdgeView]:
    """Edges where the relation maps to REQUIREMENT_OF."""
    return edges_by_relation_class(source, node, RelationSemantic.REQUIREMENT_OF, depth=depth)


def risks_of(source: EdgeSource, node: Node, *, depth: int = 10) -> list[EdgeView]:
    """Edges where the relation maps to RISK_OF."""
    return edges_by_relation_class(source, node, RelationSemantic.RISK_OF, depth=depth)


def tests_of(source: EdgeSource, node: Node, *, depth: int = 10) -> list[EdgeView]:
    """Edges where the relation maps to TEST_OF."""
    return edges_by_relation_class(source, node, RelationSemantic.TEST_OF, depth=depth)
