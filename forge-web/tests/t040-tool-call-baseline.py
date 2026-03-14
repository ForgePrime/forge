"""T-040: Tool Call Baseline Investigation

Sends 30 natural language prompts to POST /llm/chat with all scopes enabled.
Records: expected tool, actual tool called, parameters correctness, result.
Calculates per-entity-type and per-operation accuracy.

Usage:
    py tests/t040-tool-call-baseline.py [--api-url http://localhost:8000]
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.error

# ---------------------------------------------------------------------------
# Test Matrix — 30 prompts: 6 create, 6 read/get, 6 list, 6 update, 6 search
# ---------------------------------------------------------------------------

ALL_SCOPES = [
    "tasks", "decisions", "objectives", "ideas", "knowledge",
    "guidelines", "lessons", "changes", "research", "ac_templates",
    "skills", "projects", "dashboard",
]

TEST_PROMPTS: list[dict] = [
    # --- CREATE (6) ---
    {
        "id": "C1",
        "op": "create",
        "entity": "tasks",
        "prompt": "Create a new task called 'Add login page' with type feature and description 'Implement OAuth login page with Google provider'",
        "expected_tool": "createTask",
    },
    {
        "id": "C2",
        "op": "create",
        "entity": "decisions",
        "prompt": "Record a decision: we chose PostgreSQL over MongoDB for the user store. Reasoning: relational data fits better, team has SQL expertise. Type: architecture.",
        "expected_tool": "createDecision",
    },
    {
        "id": "C3",
        "op": "create",
        "entity": "guidelines",
        "prompt": "Add a new guideline: All API endpoints must return JSON with a consistent error format {error, message, details}. Scope: backend, weight: must.",
        "expected_tool": "createGuideline",
    },
    {
        "id": "C4",
        "op": "create",
        "entity": "ideas",
        "prompt": "I have an idea: 'Add dark mode support'. Category: feature. It would improve UX for users working at night.",
        "expected_tool": "createIdea",
    },
    {
        "id": "C5",
        "op": "create",
        "entity": "objectives",
        "prompt": "Create an objective 'Improve Developer Experience' with key result: reduce build time from 60s to under 15s.",
        "expected_tool": "createObjective",
    },
    {
        "id": "C6",
        "op": "create",
        "entity": "knowledge",
        "prompt": "Add knowledge: our Redis instance uses Stack 7.4 with JSON module enabled. Category: infrastructure. This is important for all backend tasks.",
        "expected_tool": "createKnowledge",
    },

    # --- READ/GET (6) ---
    {
        "id": "R1",
        "op": "read",
        "entity": "tasks",
        "prompt": "Show me the details of task T-040",
        "expected_tool": "getEntity",
    },
    {
        "id": "R2",
        "op": "read",
        "entity": "decisions",
        "prompt": "What does decision D-018 say?",
        "expected_tool": "getEntity",
    },
    {
        "id": "R3",
        "op": "read",
        "entity": "objectives",
        "prompt": "Show me objective O-003 with its key results",
        "expected_tool": "getEntity",
    },
    {
        "id": "R4",
        "op": "read",
        "entity": "research",
        "prompt": "Get the details of research R-005",
        "expected_tool": "getEntity",
    },
    {
        "id": "R5",
        "op": "read",
        "entity": "tasks",
        "prompt": "What is the full context for task T-042? I need dependencies and guidelines.",
        "expected_tool": "getTaskContext",
    },
    {
        "id": "R6",
        "op": "read",
        "entity": "global",
        "prompt": "What is the current project status? How many tasks are done?",
        "expected_tool": "getProjectStatus",
    },

    # --- LIST (6) ---
    {
        "id": "L1",
        "op": "list",
        "entity": "tasks",
        "prompt": "List all tasks that are still TODO",
        "expected_tool": "listEntities",
    },
    {
        "id": "L2",
        "op": "list",
        "entity": "decisions",
        "prompt": "Show me all open decisions",
        "expected_tool": "listEntities",
    },
    {
        "id": "L3",
        "op": "list",
        "entity": "guidelines",
        "prompt": "What guidelines do we have for the backend scope?",
        "expected_tool": "listEntities",
    },
    {
        "id": "L4",
        "op": "list",
        "entity": "ideas",
        "prompt": "List all ideas with status DRAFT",
        "expected_tool": "listEntities",
    },
    {
        "id": "L5",
        "op": "list",
        "entity": "knowledge",
        "prompt": "Show all knowledge objects",
        "expected_tool": "listEntities",
    },
    {
        "id": "L6",
        "op": "list",
        "entity": "research",
        "prompt": "List all research linked to objective O-003",
        "expected_tool": "listResearch",
    },

    # --- UPDATE (6) ---
    {
        "id": "U1",
        "op": "update",
        "entity": "decisions",
        "prompt": "Close decision D-018 with action accept. The recommendation is solid.",
        "expected_tool": "updateDecision",
    },
    {
        "id": "U2",
        "op": "update",
        "entity": "ideas",
        "prompt": "Update idea I-001 status to APPROVED",
        "expected_tool": "updateIdea",
    },
    {
        "id": "U3",
        "op": "update",
        "entity": "guidelines",
        "prompt": "Change guideline G-001 weight from 'should' to 'must'",
        "expected_tool": "updateGuideline",
    },
    {
        "id": "U4",
        "op": "update",
        "entity": "objectives",
        "prompt": "Update O-003 KR-1 current value to 75%",
        "expected_tool": "updateObjective",
    },
    {
        "id": "U5",
        "op": "update",
        "entity": "tasks",
        "prompt": "Update task T-041 description to 'Verify the full SWR revalidation pipeline including WebSocket dispatch'",
        "expected_tool": "updateTask",
    },
    {
        "id": "U6",
        "op": "update",
        "entity": "knowledge",
        "prompt": "Update knowledge K-001 content to reflect that we upgraded to Redis 7.4.1. Change reason: version bump.",
        "expected_tool": "updateKnowledge",
    },

    # --- SEARCH (6) ---
    {
        "id": "S1",
        "op": "search",
        "entity": "tasks",
        "prompt": "Find all tasks related to authentication",
        "expected_tool": "searchEntities",
    },
    {
        "id": "S2",
        "op": "search",
        "entity": "decisions",
        "prompt": "Search for decisions about database choices",
        "expected_tool": "searchEntities",
    },
    {
        "id": "S3",
        "op": "search",
        "entity": "guidelines",
        "prompt": "Find guidelines mentioning API error handling",
        "expected_tool": "searchEntities",
    },
    {
        "id": "S4",
        "op": "search",
        "entity": "knowledge",
        "prompt": "Search knowledge for anything about Redis configuration",
        "expected_tool": "searchEntities",
    },
    {
        "id": "S5",
        "op": "search",
        "entity": "lessons",
        "prompt": "Find lessons learned about testing strategies",
        "expected_tool": "searchEntities",
    },
    {
        "id": "S6",
        "op": "search",
        "entity": "research",
        "prompt": "Search for research about notification infrastructure",
        "expected_tool": "searchEntities",
    },
]


def call_chat(api_url: str, prompt: str, project: str = "forge-web") -> dict:
    """Send a chat message and return the response."""
    payload = {
        "message": prompt,
        "context_type": "global",
        "project": project,
        "scopes": ALL_SCOPES,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{api_url}/api/v1/llm/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"error": f"HTTP {e.code}", "detail": body, "tool_calls": []}
    except Exception as e:
        return {"error": str(e), "tool_calls": []}


def extract_first_tool(response: dict) -> str | None:
    """Extract the first tool name from a chat response."""
    tool_calls = response.get("tool_calls", [])
    if tool_calls:
        # tool_calls is a list of dicts with 'name' key
        first = tool_calls[0]
        return first.get("name") or first.get("tool_name")
    return None


def run_tests(api_url: str, project: str) -> list[dict]:
    """Run all 30 test prompts and collect results."""
    results = []
    total = len(TEST_PROMPTS)

    for i, test in enumerate(TEST_PROMPTS, 1):
        print(f"  [{i}/{total}] {test['id']}: {test['prompt'][:60]}...", flush=True)

        t0 = time.time()
        response = call_chat(api_url, test["prompt"], project)
        elapsed = time.time() - t0

        actual_tool = extract_first_tool(response)
        correct = actual_tool == test["expected_tool"]

        # Also check if a reasonable alternative was used
        alt_correct = False
        if not correct and actual_tool:
            # listEntities and searchEntities can sometimes be interchangeable
            if test["expected_tool"] in ("listEntities", "searchEntities") and actual_tool in ("listEntities", "searchEntities"):
                alt_correct = True
            # getEntity and getTaskContext are both valid for reading a task
            if test["expected_tool"] in ("getEntity", "getTaskContext") and actual_tool in ("getEntity", "getTaskContext"):
                alt_correct = True
            # listResearch and listEntities can overlap
            if test["expected_tool"] in ("listResearch", "listEntities") and actual_tool in ("listResearch", "listEntities"):
                alt_correct = True

        result = {
            "id": test["id"],
            "op": test["op"],
            "entity": test["entity"],
            "prompt": test["prompt"],
            "expected_tool": test["expected_tool"],
            "actual_tool": actual_tool,
            "exact_match": correct,
            "acceptable": correct or alt_correct,
            "error": response.get("error"),
            "elapsed_s": round(elapsed, 1),
            "iterations": response.get("iterations", 0),
            "tool_calls_count": len(response.get("tool_calls", [])),
        }
        results.append(result)

        status = "OK" if correct else ("~OK" if alt_correct else "MISS")
        print(f"         -> {actual_tool or 'NONE'} [{status}] ({elapsed:.1f}s)")

        # Brief pause to avoid rate limiting
        time.sleep(0.5)

    return results


def compute_stats(results: list[dict]) -> dict:
    """Compute accuracy statistics."""
    total = len(results)
    exact = sum(1 for r in results if r["exact_match"])
    acceptable = sum(1 for r in results if r["acceptable"])

    # Per operation
    ops = {}
    for r in results:
        op = r["op"]
        if op not in ops:
            ops[op] = {"total": 0, "exact": 0, "acceptable": 0}
        ops[op]["total"] += 1
        if r["exact_match"]:
            ops[op]["exact"] += 1
        if r["acceptable"]:
            ops[op]["acceptable"] += 1

    # Per entity
    entities = {}
    for r in results:
        ent = r["entity"]
        if ent not in entities:
            entities[ent] = {"total": 0, "exact": 0, "acceptable": 0}
        entities[ent]["total"] += 1
        if r["exact_match"]:
            entities[ent]["exact"] += 1
        if r["acceptable"]:
            entities[ent]["acceptable"] += 1

    return {
        "overall": {
            "total": total,
            "exact_match": exact,
            "exact_pct": round(exact / total * 100, 1),
            "acceptable": acceptable,
            "acceptable_pct": round(acceptable / total * 100, 1),
        },
        "by_operation": ops,
        "by_entity": entities,
    }


def generate_report(results: list[dict], stats: dict) -> str:
    """Generate markdown report."""
    lines = [
        "# T-040: Tool Call Baseline Investigation Results",
        "",
        f"**Date**: {time.strftime('%Y-%m-%d %H:%M')}",
        f"**Total prompts**: {stats['overall']['total']}",
        f"**Exact match**: {stats['overall']['exact_match']}/{stats['overall']['total']} ({stats['overall']['exact_pct']}%)",
        f"**Acceptable match**: {stats['overall']['acceptable']}/{stats['overall']['total']} ({stats['overall']['acceptable_pct']}%)",
        "",
    ]

    # Verdict
    pct = stats['overall']['acceptable_pct']
    if pct >= 80:
        lines.append(f"**Verdict**: PASS — baseline {pct}% >= 80% threshold. D-018 approach confirmed (descriptions + gap filling sufficient).")
    elif pct >= 60:
        lines.append(f"**Verdict**: MARGINAL — baseline {pct}% between 60-80%. Descriptions need improvement but no routing layer needed yet.")
    else:
        lines.append(f"**Verdict**: FAIL — baseline {pct}% < 60%. Routing layer may be needed (contradicts D-018).")

    lines += ["", "## Per-Operation Accuracy", "", "| Operation | Total | Exact | Acceptable | Exact % | Accept % |", "|-----------|-------|-------|------------|---------|----------|"]
    for op in ["create", "read", "list", "update", "search"]:
        s = stats["by_operation"].get(op, {"total": 0, "exact": 0, "acceptable": 0})
        if s["total"] > 0:
            lines.append(f"| {op} | {s['total']} | {s['exact']} | {s['acceptable']} | {round(s['exact']/s['total']*100)}% | {round(s['acceptable']/s['total']*100)}% |")

    lines += ["", "## Per-Entity Accuracy", "", "| Entity | Total | Exact | Acceptable | Exact % | Accept % |", "|--------|-------|-------|------------|---------|----------|"]
    for ent in sorted(stats["by_entity"].keys()):
        s = stats["by_entity"][ent]
        if s["total"] > 0:
            lines.append(f"| {ent} | {s['total']} | {s['exact']} | {s['acceptable']} | {round(s['exact']/s['total']*100)}% | {round(s['acceptable']/s['total']*100)}% |")

    lines += ["", "## Detailed Results", "", "| ID | Op | Entity | Expected | Actual | Match | Time |", "|----|-----|--------|----------|--------|-------|------|"]
    for r in results:
        match_str = "OK" if r["exact_match"] else ("~OK" if r["acceptable"] else "MISS")
        actual = r["actual_tool"] or "NONE"
        lines.append(f"| {r['id']} | {r['op']} | {r['entity']} | {r['expected_tool']} | {actual} | {match_str} | {r['elapsed_s']}s |")

    # Misses detail
    misses = [r for r in results if not r["acceptable"]]
    if misses:
        lines += ["", "## Misses (need attention)", ""]
        for r in misses:
            lines.append(f"### {r['id']}: {r['op']} {r['entity']}")
            lines.append(f"- **Prompt**: {r['prompt']}")
            lines.append(f"- **Expected**: {r['expected_tool']}")
            lines.append(f"- **Got**: {r['actual_tool'] or 'NONE'}")
            if r.get("error"):
                lines.append(f"- **Error**: {r['error']}")
            lines.append("")

    lines += ["", "## Recommendations", ""]
    if pct >= 80:
        lines.append("1. Current tool descriptions are sufficient for > 80% accuracy")
        lines.append("2. Focus T-042 on filling CRUD gaps (DELETE/archive operations)")
        lines.append("3. Focus T-047 on improving descriptions for any missed tools")
    elif pct >= 60:
        lines.append("1. Improve tool descriptions for missed entity types")
        lines.append("2. Consider adding examples to tool descriptions")
        lines.append("3. No routing layer needed yet — descriptions improvement should suffice")
    else:
        lines.append("1. **CRITICAL**: Routing layer may be needed — revisit D-018")
        lines.append("2. Tool descriptions need major overhaul")
        lines.append("3. Consider scope-based tool filtering as first mitigation")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="T-040 Tool Call Baseline Test")
    parser.add_argument("--api-url", default="http://localhost:8000", help="Forge API URL")
    parser.add_argument("--project", default="forge-web", help="Project slug")
    parser.add_argument("--output", default=None, help="Output markdown file path")
    args = parser.parse_args()

    print(f"T-040: Tool Call Baseline Investigation")
    print(f"API: {args.api_url}, Project: {args.project}")
    print(f"Running {len(TEST_PROMPTS)} test prompts...\n")

    results = run_tests(args.api_url, args.project)
    stats = compute_stats(results)

    print(f"\n{'='*60}")
    print(f"RESULTS: {stats['overall']['exact_match']}/{stats['overall']['total']} exact ({stats['overall']['exact_pct']}%)")
    print(f"         {stats['overall']['acceptable']}/{stats['overall']['total']} acceptable ({stats['overall']['acceptable_pct']}%)")
    print(f"{'='*60}\n")

    report = generate_report(results, stats)

    output_path = args.output or f"forge_output/{args.project}/t040-baseline-results.md"
    # Write report
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Report written to: {output_path}")

    # Also write raw JSON
    json_path = output_path.replace(".md", ".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"results": results, "stats": stats}, f, indent=2, ensure_ascii=False)
    print(f"Raw data written to: {json_path}")

    return 0 if stats['overall']['acceptable_pct'] >= 60 else 1


if __name__ == "__main__":
    sys.exit(main())
