"""ContextBudget — Phase L3 Stage L3.3.

Pure-function bucket-priority allocator for the LLM context window.
Per PLAN_LLM_ORCHESTRATION §L3.3 + FORMAL_PROPERTIES_v2 P15
(Context Projection):

    BFS over CausalEdge, filtered by scope_tags U requirement_refs,
    pruned with deterministic priority (must-guidelines -> recent
    decisions -> evidence -> knowledge).

Three buckets with hard semantics:
- MUST  : non-negotiable items. If total MUST tokens exceed budget,
          fit() returns REJECTED with reason='must_exceeds_budget' —
          NEVER silent-truncate MUST. Caller must decompose the task
          (smaller scope) and retry.
- SHOULD: prioritized by priority_within_bucket desc; admitted greedily
          until budget exhausted.
- NICE  : same as SHOULD; admitted last.

Determinism (P6): same items + same budget -> same FitResult; tie-
breaking by stable sort key (priority desc, then source_ref asc).

Token counting: caller is responsible for populating
ContextItem.token_count via their tokenizer choice (tiktoken in MVP
per PLAN). This module does not import a tokenizer; that decision is
pluggable via ADR-006.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class Bucket(str, Enum):
    """Priority bucket for a context item.

    str-Enum so JSONB serialization is the string value.
    """

    MUST = "must"
    SHOULD = "should"
    NICE = "nice"


@dataclass(frozen=True)
class ContextItem:
    """A unit of context with bucket + priority + token count.

    Frozen dataclass: caller cannot mutate after construction; the
    fitter relies on stable identity for deduplication.
    """

    content: str  # the actual context text (may be JSON-serialized)
    bucket: Bucket
    priority_within_bucket: int  # higher = admitted first
    source_ref: str  # stable ID for traceability + tie-breaking
    token_count: int


@dataclass(frozen=True)
class FitResult:
    """Outcome of fitting context items into a budget."""

    status: str  # 'ACCEPTED' | 'REJECTED'
    included: tuple[ContextItem, ...]
    excluded: tuple[ContextItem, ...]
    total_tokens: int
    budget_tokens: int
    reason: str | None = None  # populated when REJECTED


def fit(items: Iterable[ContextItem], budget_tokens: int) -> FitResult:
    """Allocate items into the token budget per bucket priority.

    Args:
        items: ContextItems to fit. Order does not matter (sorted
            internally for determinism).
        budget_tokens: hard ceiling on total token count of included items.

    Returns:
        FitResult.

    Semantics:
        1. Sum total MUST tokens.
        2. If MUST > budget: REJECTED with reason='must_exceeds_budget';
           returned `included` is empty (do not partially admit MUST —
           that violates the hard guarantee).
        3. Else admit ALL MUST items.
        4. Sort SHOULD by (priority_within_bucket desc, source_ref asc);
           admit greedily until budget exhausted.
        5. Same for NICE.
        6. Return ACCEPTED with included + excluded.
    """
    items_list = list(items)

    # Partition by bucket.
    must = [i for i in items_list if i.bucket == Bucket.MUST]
    should = [i for i in items_list if i.bucket == Bucket.SHOULD]
    nice = [i for i in items_list if i.bucket == Bucket.NICE]

    # Step 1+2: MUST hard-check.
    must_total = sum(i.token_count for i in must)
    if must_total > budget_tokens:
        return FitResult(
            status="REJECTED",
            included=(),
            excluded=tuple(items_list),
            total_tokens=must_total,
            budget_tokens=budget_tokens,
            reason=(
                f"must_exceeds_budget: MUST items total {must_total} tokens "
                f"but budget is {budget_tokens}; decompose task or raise budget"
            ),
        )

    included: list[ContextItem] = []
    excluded: list[ContextItem] = []
    used_tokens = 0

    # Step 3: admit all MUST in stable sort order.
    for item in sorted(must, key=lambda i: (-i.priority_within_bucket, i.source_ref)):
        included.append(item)
        used_tokens += item.token_count

    # Step 4+5: greedy fit SHOULD then NICE.
    for bucket_items in (
        sorted(should, key=lambda i: (-i.priority_within_bucket, i.source_ref)),
        sorted(nice, key=lambda i: (-i.priority_within_bucket, i.source_ref)),
    ):
        for item in bucket_items:
            if used_tokens + item.token_count <= budget_tokens:
                included.append(item)
                used_tokens += item.token_count
            else:
                excluded.append(item)

    return FitResult(
        status="ACCEPTED",
        included=tuple(included),
        excluded=tuple(excluded),
        total_tokens=used_tokens,
        budget_tokens=budget_tokens,
        reason=None,
    )
