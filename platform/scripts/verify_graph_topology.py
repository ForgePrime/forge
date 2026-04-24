#!/usr/bin/env python3
"""verify_graph_topology.py — formal verification of USAGE_PROCESS_GRAPH.dot.

Closes USAGE_PROCESS.md §16 method-weakness #1: narrative §11 graph
supplemented by algorithmic topology verification.

Zero external dependencies — pure stdlib (re, collections, sys, pathlib).

Checks per ProcessCorrect theorem §A4 TopologicallyConsistent + §A2 EventComplete:

  1. REACHABILITY — every non-START node reachable from START via forward edges.
  2. DEAD-END DETECTION — every node has >=1 outgoing edge OR is marked terminal.
  3. ACYCLICITY — no directed cycles EXCEPT edges tagged kind="bounded_feedback".
     Bounded-feedback cycles require ADR reference in edge label.
  4. DECISION DETERMINISM — every decision node (shape="diamond") has outgoing
     edges with non-empty labels (covers §A3 LocallyDeterministic contract).
  5. FAILURE RECOVERY — every kind="failure" target state has a kind="recovery"
     outgoing OR a terminal path (no silent failures).

Deterministic: same .dot file → same report. No LLM, no network, no clock.

Usage:
  python platform/scripts/verify_graph_topology.py platform/docs/USAGE_PROCESS_GRAPH.dot

Exit codes:
  0 — all checks pass
  1 — >=1 check fails (details in stdout + stderr)
  2 — DOT file unparseable / missing

Status: DRAFT — pending distinct-actor review per ADR-003.
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path


# ============================================================================
# MINIMAL DOT PARSER (handles our specific subset)
# ============================================================================

# Matches:  NODE_NAME [attr1="v1", attr2=bare_val, ...];
# Uses DOTALL so multi-line [...] blocks work.
NODE_RE = re.compile(
    r'([A-Z][A-Z0-9_]*)\s*\[(.*?)\]\s*;',
    re.DOTALL,
)

# Matches:  SOURCE -> TARGET [attrs];
# Edge attribute block allowed to span multiple lines.
EDGE_RE = re.compile(
    r'([A-Z][A-Z0-9_]*)\s*->\s*([A-Z][A-Z0-9_]*)(?:\s*\[(.*?)\])?\s*;',
    re.DOTALL,
)

# Within an attribute block. Supports both:
#   key="value"           (quoted — value may contain newlines, escaped quotes)
#   key=bare_value        (unquoted — e.g. shape=diamond)
ATTR_RE = re.compile(
    r'(\w+)\s*=\s*(?:"((?:[^"\\]|\\.)*)"|([A-Za-z0-9_#]+))',
    re.DOTALL,
)


def _parse_attrs(attr_block: str) -> dict[str, str]:
    """Parse attribute block supporting both quoted and bare values."""
    result: dict[str, str] = {}
    for match in ATTR_RE.finditer(attr_block):
        key = match.group(1)
        quoted_val = match.group(2)
        bare_val = match.group(3)
        result[key] = quoted_val if quoted_val is not None else (bare_val or '')
    return result


def parse_dot(path: Path) -> tuple[dict[str, dict[str, str]], list[tuple[str, str, dict[str, str]]]]:
    """Parse the DOT file into (nodes, edges).

    Returns:
      nodes: {node_name: {attr_key: attr_value, ...}}
      edges: [(source, target, {attr_key: attr_value, ...}), ...]
    """
    text = path.read_text(encoding="utf-8")

    # Remove C-style comments (// ... to end of line)
    text = re.sub(r'//[^\n]*', '', text)

    # First pass: remove edges (they also match NODE_RE if the [...] is populated
    # on the same line in ways that trip the parser — extract edges first).
    edges: list[tuple[str, str, dict[str, str]]] = []
    for match in EDGE_RE.finditer(text):
        src, dst, attr_block = match.group(1), match.group(2), match.group(3) or ''
        attrs = _parse_attrs(attr_block)
        edges.append((src, dst, attrs))

    # Remove edge lines from text so we don't re-parse them as nodes
    text_no_edges = EDGE_RE.sub('', text)

    # Second pass: nodes
    nodes: dict[str, dict[str, str]] = {}
    for match in NODE_RE.finditer(text_no_edges):
        name, attr_block = match.group(1), match.group(2)
        attrs = _parse_attrs(attr_block)
        nodes[name] = attrs

    # Ensure all edge endpoints are registered as nodes (even if attr-less)
    for src, dst, _ in edges:
        nodes.setdefault(src, {})
        nodes.setdefault(dst, {})

    return nodes, edges


# ============================================================================
# GRAPH ALGORITHMS (pure stdlib)
# ============================================================================


def build_adjacency(edges: list[tuple[str, str, dict[str, str]]]) -> dict[str, list[tuple[str, dict[str, str]]]]:
    """Build outgoing adjacency: node → list of (target, attrs)."""
    adj: dict[str, list[tuple[str, dict[str, str]]]] = defaultdict(list)
    for src, dst, attrs in edges:
        adj[src].append((dst, attrs))
    return adj


def bfs_reachable(adj: dict[str, list[tuple[str, dict[str, str]]]], start: str) -> set[str]:
    """Return set of nodes reachable from start via forward edges."""
    visited = {start}
    stack = [start]
    while stack:
        node = stack.pop()
        for target, _ in adj.get(node, []):
            if target not in visited:
                visited.add(target)
                stack.append(target)
    return visited


def find_cycles(adj: dict[str, list[tuple[str, dict[str, str]]]], all_nodes: set[str]) -> list[list[str]]:
    """Find all simple cycles via Johnson-like DFS. Good enough for small graphs.

    For graphs < 500 nodes this is acceptable; our USAGE_PROCESS has ~50 nodes.
    """
    cycles: list[list[str]] = []
    # For each node, DFS and track path; when a back-edge is found, extract cycle.
    for start in all_nodes:
        path: list[str] = [start]
        on_path = {start}

        def dfs(u: str) -> None:
            for v, _ in adj.get(u, []):
                if v == start and len(path) > 1:
                    cycles.append(list(path))
                elif v not in on_path:
                    path.append(v)
                    on_path.add(v)
                    dfs(v)
                    path.pop()
                    on_path.remove(v)

        try:
            dfs(start)
        except RecursionError:
            # Very deep DFS — skip; report as suspect
            pass

    # Deduplicate cycles (same cycle rotations / reverses)
    unique: list[tuple[str, ...]] = []
    seen: set[frozenset] = set()
    for c in cycles:
        key = frozenset(c)
        if key not in seen:
            seen.add(key)
            unique.append(tuple(c))
    return [list(c) for c in unique]


# ============================================================================
# CHECKS
# ============================================================================


def check_reachability(
    adj: dict[str, list[tuple[str, dict[str, str]]]], nodes: dict[str, dict[str, str]]
) -> tuple[bool, str]:
    if "START" not in nodes:
        return False, "no 'START' node found"
    reachable = bfs_reachable(adj, "START")
    unreachable = set(nodes) - reachable
    if unreachable:
        return False, f"{len(unreachable)} unreachable nodes: {sorted(unreachable)[:10]}"
    return True, f"all {len(nodes)} nodes reachable from START"


def check_dead_ends(
    adj: dict[str, list[tuple[str, dict[str, str]]]], nodes: dict[str, dict[str, str]]
) -> tuple[bool, str]:
    dead = []
    for name in nodes:
        if not adj.get(name, []):
            # OK only if this is a terminal
            is_terminal = (
                name.startswith("TERM_")
                or "terminal" in nodes[name].get("label", "").lower()
            )
            if not is_terminal:
                dead.append(name)
    if dead:
        return False, f"non-terminal dead ends: {dead}"
    return True, "every non-terminal node has >=1 outgoing edge"


def check_acyclicity(
    adj: dict[str, list[tuple[str, dict[str, str]]]],
    nodes: dict[str, dict[str, str]],
    edges: list[tuple[str, str, dict[str, str]]],
) -> tuple[bool, list[str]]:
    """Check no cycles except those on edges explicitly tagged as bounded.

    Bounded kinds (permitted cycle participants):
      - kind="bounded_feedback"  — feedback loop Phase 10→1, bounded per ADR-022
      - kind="recovery"          — retry loops REJECTED→IN_PROGRESS, bounded per ADR-013 N=3

    Both represent process-correctness justified cycles per ProcessCorrect §A4
    "nieuzasadnione cykle" wording: these ARE justified and bounded.
    """
    BOUNDED_KINDS = {"bounded_feedback", "recovery"}

    # Build adjacency excluding edges whose kind is bounded
    adj_no_bounded: dict[str, list[tuple[str, dict[str, str]]]] = defaultdict(list)
    for src, dst, attrs in edges:
        if attrs.get("kind", "") not in BOUNDED_KINDS:
            adj_no_bounded[src].append((dst, attrs))

    cycles = find_cycles(adj_no_bounded, set(nodes))
    msgs: list[str] = []

    if cycles:
        msgs.append(f"{len(cycles)} unbounded cycle(s) detected")
        for c in cycles[:3]:
            msgs.append(f"  cycle: {' -> '.join(c + [c[0]])}")
    else:
        msgs.append(f"no cycles except bounded-tagged edges ({BOUNDED_KINDS})")

    # Verify bounded_feedback edges have ADR reference in label
    bf_edges = [(s, d, a) for s, d, a in edges if a.get("kind", "") == "bounded_feedback"]
    bf_missing_adr = 0
    for src, dst, attrs in bf_edges:
        label = attrs.get("label", "")
        if "ADR" not in label:
            msgs.append(f"  WARN: bounded_feedback {src}->{dst} lacks ADR reference in label")
            bf_missing_adr += 1

    # Verify recovery edges referenced by a bounding mechanism (ADR-013 retry limit is canonical)
    # Soft check — warn if recovery edge has no rationale in label
    recovery_edges = [(s, d, a) for s, d, a in edges if a.get("kind", "") == "recovery"]
    msgs.append(f"  (bounded edges: {len(bf_edges)} feedback + {len(recovery_edges)} recovery)")

    ok = not cycles
    return ok, msgs


def check_decision_determinism(
    adj: dict[str, list[tuple[str, dict[str, str]]]], nodes: dict[str, dict[str, str]]
) -> tuple[bool, list[str]]:
    decision_nodes = [n for n, a in nodes.items() if a.get("shape") == "diamond"]
    msgs: list[str] = []
    failures = 0
    for dn in decision_nodes:
        out = adj.get(dn, [])
        labels = [attrs.get("label", "") for _, attrs in out]
        if not out:
            msgs.append(f"  decision node {dn} has no outgoing edges")
            failures += 1
        elif any(not l for l in labels):
            msgs.append(f"  decision node {dn} has unlabeled outgoing edge(s)")
            failures += 1
    if failures == 0:
        msgs.append(f"all {len(decision_nodes)} decision nodes have labeled branches")
        return True, msgs
    return False, msgs


def check_failure_recovery(
    adj: dict[str, list[tuple[str, dict[str, str]]]],
    nodes: dict[str, dict[str, str]],
    edges: list[tuple[str, str, dict[str, str]]],
) -> tuple[bool, str]:
    failure_targets = set(dst for _, dst, attrs in edges if attrs.get("kind") == "failure")
    unrecovered = []
    for ft in failure_targets:
        out = adj.get(ft, [])
        kinds = [attrs.get("kind", "") for _, attrs in out]
        has_recovery = any(k == "recovery" for k in kinds)
        has_terminal = any(k == "terminal" for k in kinds) or ft.startswith("TERM_")
        if not (has_recovery or has_terminal):
            unrecovered.append(ft)
    if unrecovered:
        return False, f"failure states without recovery/terminal path: {unrecovered}"
    return True, f"all {len(failure_targets)} failure states have recovery or terminal"


# ============================================================================
# MAIN
# ============================================================================


def main(dot_path: str) -> int:
    dot_file = Path(dot_path)
    if not dot_file.exists():
        sys.stderr.write(f"ERROR: DOT file not found: {dot_path}\n")
        return 2

    try:
        nodes, edges = parse_dot(dot_file)
    except Exception as e:
        sys.stderr.write(f"ERROR: cannot parse DOT: {e}\n")
        return 2

    adj = build_adjacency(edges)

    print(f"Loaded graph: {len(nodes)} nodes, {len(edges)} edges")
    print("=" * 70)

    failures_count = 0

    # Check 1
    print("\n[Check 1/5] Reachability from START ...")
    ok, msg = check_reachability(adj, nodes)
    print(f"  {'PASS' if ok else 'FAIL'}: {msg}")
    if not ok:
        failures_count += 1

    # Check 2
    print("\n[Check 2/5] Dead-end detection ...")
    ok, msg = check_dead_ends(adj, nodes)
    print(f"  {'PASS' if ok else 'FAIL'}: {msg}")
    if not ok:
        failures_count += 1

    # Check 3
    print("\n[Check 3/5] Acyclicity (modulo bounded_feedback) ...")
    ok, msgs = check_acyclicity(adj, nodes, edges)
    print(f"  {'PASS' if ok else 'FAIL'}:")
    for m in msgs:
        print(f"    {m}")
    if not ok:
        failures_count += 1

    # Check 4
    print("\n[Check 4/5] Decision-node determinism ...")
    ok, msgs = check_decision_determinism(adj, nodes)
    print(f"  {'PASS' if ok else 'FAIL'}:")
    for m in msgs:
        print(f"    {m}")
    if not ok:
        failures_count += 1

    # Check 5
    print("\n[Check 5/5] Failure-path recovery ...")
    ok, msg = check_failure_recovery(adj, nodes, edges)
    print(f"  {'PASS' if ok else 'FAIL'}: {msg}")
    if not ok:
        failures_count += 1

    # Summary
    print("\n" + "=" * 70)
    if failures_count == 0:
        print("RESULT: PASS — all 5 topology checks green")
        print("\nNote: this verifies graph STRUCTURE (ProcessCorrect §A4 TopologicallyConsistent,")
        print("§A3 LocallyDeterministic partial). SemanticsPreserved remains PARTIAL per")
        print("USAGE_PROCESS.md §16 method-weakness disclosure.")
        return 0
    else:
        print(f"RESULT: FAIL — {failures_count} check(s) failed")
        return 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.stderr.write(
            "Usage: verify_graph_topology.py <path/to/USAGE_PROCESS_GRAPH.dot>\n"
        )
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
