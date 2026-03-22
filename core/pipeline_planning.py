"""Pipeline planning — draft plan, approval, validation."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_common import (
    _get_storage, _trace, load_tracker, save_tracker,
    print_task_list, STATUS_ICONS,
)
from pipeline_tasks import (
    _build_task_entry, _remap_temp_ids, validate_dag,
    cmd_add_tasks, CONTRACTS,
)
from pipeline_execution import _validate_ac_reasoning, _warn_ac_quality
from contracts import validate_contract
from errors import ForgeError, ValidationError, EntityNotFound, PreconditionError
from storage import JSONFileStorage, load_json_data, now_iso, tracker_lock
from trace import trace_cmd


def _validate_plan_references(entries: list, project: str) -> list:
    """Validate origin, scopes, knowledge_ids references. Returns list of warning strings."""
    warnings = []
    _s = _get_storage()

    # Collect valid IDs for batch checking
    valid_idea_ids = set()
    valid_obj_ids = set()
    valid_k_ids = set()
    valid_scopes = set()

    if _s.exists(project, 'ideas'):
        ideas = _s.load_data(project, 'ideas').get("ideas", [])
        valid_idea_ids = {i["id"] for i in ideas}
    if _s.exists(project, 'objectives'):
        objs = _s.load_data(project, 'objectives').get("objectives", [])
        valid_obj_ids = {o["id"] for o in objs}
    if _s.exists(project, 'knowledge'):
        k_data = _s.load_data(project, 'knowledge').get("knowledge", [])
        valid_k_ids = {k["id"] for k in k_data if k.get("status") == "ACTIVE"}
    if _s.exists(project, 'guidelines'):
        g_data = _s.load_data(project, 'guidelines').get("guidelines", [])
        valid_scopes = {g["scope"] for g in g_data if g.get("scope") and g.get("status") == "ACTIVE"}
        valid_scopes.add("general")

    for t in entries:
        tid = t.get("id", "?")

        # Origin validation
        origin = t.get("origin", "")
        if origin:
            if origin.startswith("I-") and origin not in valid_idea_ids:
                warnings.append(f"  {tid}: origin '{origin}' — idea not found")
            elif origin.startswith("O-") and origin not in valid_obj_ids:
                warnings.append(f"  {tid}: origin '{origin}' — objective not found")

        # Scope validation (only warn if guidelines exist for the project)
        for scope in t.get("scopes", []):
            if valid_scopes and scope != "general" and scope not in valid_scopes:
                warnings.append(f"  {tid}: scope '{scope}' — no guidelines with this scope")

        # Knowledge validation
        for kid in t.get("knowledge_ids", []):
            if kid not in valid_k_ids:
                warnings.append(f"  {tid}: knowledge '{kid}' — not found or not ACTIVE")

    return warnings


def _validate_plan_context(entries: list, project: str) -> tuple[list, list]:
    """Auto-load project context and validate plan against it.

    Returns (errors: list[str], context_summary: list[str]).
    Errors are blocking. Context summary is informational (shows what exists).

    Checks:
    1. Feature/bug tasks with origin O-XXX should inherit objective's scopes
    2. Tasks should reference valid scopes from existing guidelines
    3. Must-guidelines exist but no task references their scope -> warning
    4. Knowledge exists but no task links it -> warning
    5. Objective KR exists but no task addresses it -> warning
    """
    errors = []
    summary = []
    _s = _get_storage()

    # -- Load project context --
    must_guidelines = []
    all_guidelines = []
    all_knowledge = []
    all_objectives = []
    objective_scopes = {}  # O-XXX -> set of scopes

    if _s.exists(project, 'guidelines'):
        g_data = _s.load_data(project, 'guidelines')
        all_guidelines = [g for g in g_data.get("guidelines", []) if g.get("status") == "ACTIVE"]
        must_guidelines = [g for g in all_guidelines if g.get("weight") == "must"]

    if _s.exists(project, 'knowledge'):
        k_data = _s.load_data(project, 'knowledge')
        all_knowledge = [k for k in k_data.get("knowledge", []) if k.get("status") in ("ACTIVE", "DRAFT")]

    if _s.exists(project, 'objectives'):
        obj_data = _s.load_data(project, 'objectives')
        all_objectives = [o for o in obj_data.get("objectives", []) if o.get("status") == "ACTIVE"]
        objective_scopes = {o["id"]: set(o.get("scopes", [])) for o in all_objectives}

    # -- Context summary (always printed so LLM sees what exists) --
    if must_guidelines:
        summary.append(f"  MUST guidelines ({len(must_guidelines)}):")
        for g in must_guidelines:
            summary.append(f"    {g['id']} [{g.get('scope', 'general')}]: {g.get('title', g.get('content', '')[:60])}")

    guideline_scopes = {g.get("scope", "general") for g in all_guidelines}
    if guideline_scopes:
        summary.append(f"  Available scopes: {', '.join(sorted(guideline_scopes))}")

    if all_knowledge:
        summary.append(f"  Knowledge objects ({len(all_knowledge)}):")
        for k in all_knowledge:
            scopes_str = f" [{', '.join(k.get('scopes', []))}]" if k.get('scopes') else ""
            summary.append(f"    {k['id']}: {k.get('title', '')}{scopes_str}")

    if all_objectives:
        summary.append(f"  Active objectives ({len(all_objectives)}):")
        for o in all_objectives:
            kr_count = len(o.get("key_results", []))
            scopes_str = f" [{', '.join(o.get('scopes', []))}]" if o.get('scopes') else ""
            summary.append(f"    {o['id']}: {o.get('title', '')} ({kr_count} KRs){scopes_str}")

    # -- Validation checks --

    # Collect what the plan references
    plan_scopes = set()
    plan_origins = set()
    plan_knowledge_ids = set()
    for t in entries:
        plan_scopes.update(t.get("scopes", []))
        if t.get("origin"):
            plan_origins.add(t["origin"])
        plan_knowledge_ids.update(t.get("knowledge_ids", []))

    # Check 1: Tasks with origin O-XXX should have scopes from that objective
    for t in entries:
        tid = t.get("id", "?")
        ttype = t.get("type", "feature")
        origin = t.get("origin", "")
        task_scopes = set(t.get("scopes", []))

        if origin.startswith("O-") and origin in objective_scopes:
            obj_scopes = objective_scopes[origin]
            if obj_scopes and not task_scopes:
                errors.append(
                    f"  {tid}: origin {origin} has scopes {obj_scopes} but task has no scopes. "
                    f"Add scopes to ensure correct guidelines are loaded during execution."
                )
            elif obj_scopes and not (task_scopes & obj_scopes):
                errors.append(
                    f"  {tid}: origin {origin} has scopes {obj_scopes} but task scopes {task_scopes} "
                    f"don't overlap. Task may miss relevant guidelines during execution."
                )

    # Check 2: Must-guidelines scopes are covered by plan
    if must_guidelines:
        must_scopes = {g.get("scope", "general") for g in must_guidelines} - {"general"}
        uncovered_must_scopes = must_scopes - plan_scopes
        if uncovered_must_scopes:
            errors.append(
                f"  MUST guidelines exist for scopes {uncovered_must_scopes} but NO task in the plan "
                f"has these scopes. Tasks without proper scopes will NOT receive these guidelines "
                f"during execution. Add scopes to relevant tasks."
            )

    # Check 3: Knowledge exists but no task references it
    if all_knowledge and not plan_knowledge_ids:
        k_ids = [k["id"] for k in all_knowledge]
        summary.append(
            f"  NOTE: {len(all_knowledge)} knowledge object(s) exist ({', '.join(k_ids)}) "
            f"but no task in the plan references knowledge_ids. "
            f"Consider linking relevant knowledge to tasks."
        )

    # Check 4: Active objectives exist but no task has origin
    obj_ids_in_plan = {o for o in plan_origins if o.startswith("O-")}
    unlinked_objs = [o for o in all_objectives if o["id"] not in obj_ids_in_plan]
    if unlinked_objs and plan_origins:
        # Only warn if some tasks DO have origin — means LLM is aware of objectives
        for o in unlinked_objs:
            summary.append(
                f"  NOTE: Objective {o['id']} ({o.get('title', '')}) has no tasks in this plan."
            )

    return errors, summary


def _check_assumptions_readiness(assumptions_raw):
    """Parse and validate assumptions for readiness gate.

    Returns (parsed_assumptions, high_count).
    Exits on invalid JSON or schema.
    """
    try:
        assumptions = load_json_data(assumptions_raw)
    except (json.JSONDecodeError, Exception) as e:
        raise ValidationError(f"Invalid assumptions JSON: {e}")

    if not isinstance(assumptions, list):
        raise ValidationError("--assumptions must be a JSON array")

    valid_severities = {"HIGH", "MED", "LOW"}
    for i, a in enumerate(assumptions):
        if not isinstance(a, dict):
            raise ValidationError(f"Assumption {i+1} must be an object with assumption, basis, severity")
        for field in ("assumption", "basis", "severity"):
            if field not in a:
                raise ValidationError(f"Assumption {i+1} missing required field '{field}'")
        if a["severity"] not in valid_severities:
            raise ValidationError(f"Assumption {i+1} severity must be HIGH, MED, or LOW (got '{a['severity']}')")

    high_count = sum(1 for a in assumptions if a["severity"] == "HIGH")
    return assumptions, high_count


def _check_coverage(coverage_raw):
    """Parse and validate coverage data. Blocks if any requirement has status MISSING.

    Each item: {requirement, source, covered_by, status, reason?}
    status: COVERED | DEFERRED | OUT_OF_SCOPE | MISSING
    DEFERRED and OUT_OF_SCOPE require reason field.

    Returns (parsed_coverage, missing_count, deferred_items).
    Exits on invalid JSON or schema.
    """
    try:
        coverage = load_json_data(coverage_raw)
    except (json.JSONDecodeError, Exception) as e:
        raise ValidationError(f"Invalid coverage JSON: {e}")

    if not isinstance(coverage, list):
        raise ValidationError("--coverage must be a JSON array")

    valid_statuses = {"COVERED", "DEFERRED", "OUT_OF_SCOPE", "MISSING"}
    missing = []
    deferred = []

    for i, item in enumerate(coverage):
        if not isinstance(item, dict):
            raise ValidationError(f"Coverage item {i+1} must be an object")

        for field in ("requirement", "status"):
            if field not in item:
                raise ValidationError(f"Coverage item {i+1} missing required field '{field}'")

        st = item["status"].upper()
        item["status"] = st

        if st not in valid_statuses:
            raise ValidationError(f"Coverage item {i+1} status must be one of {sorted(valid_statuses)} (got '{st}')")

        if st in ("DEFERRED", "OUT_OF_SCOPE") and not item.get("reason"):
            raise ValidationError(f"Coverage item {i+1} '{item['requirement'][:50]}' has status {st} but no reason.")

        if st == "MISSING":
            missing.append(item)
        elif st in ("DEFERRED", "OUT_OF_SCOPE"):
            deferred.append(item)

    return coverage, len(missing), deferred


CRITICAL_CATEGORIES = {
    "deployment": {
        "question": "Where will this system run? (cloud provider, Docker, serverless, on-prem)",
        "knowledge_match": {"categories": {"infrastructure"}, "tags": {"deploy", "docker", "kubernetes", "serverless", "cloud"}, "keywords": {"deploy", "hosting", "container", "server"}},
    },
    "stack": {
        "question": "What programming language, framework, and database are used?",
        "knowledge_match": {"categories": {"technical-context", "architecture"}, "tags": {"framework", "language", "database", "stack"}, "keywords": {"python", "node", "java", "react", "postgres", "mongo", "redis"}},
    },
    "users": {
        "question": "Who uses this system? What roles/permissions exist?",
        "knowledge_match": {"categories": {"business-context", "domain-rules"}, "tags": {"user", "role", "persona", "auth"}, "keywords": {"user", "role", "admin", "permission", "persona"}},
    },
    "data-in": {
        "question": "What data enters the system? (APIs, files, events, user input)",
        "knowledge_match": {"categories": {"api-reference", "integration"}, "tags": {"input", "api", "endpoint", "event"}, "keywords": {"request", "input", "upload", "import", "receive"}},
    },
    "data-out": {
        "question": "What data leaves the system? (responses, reports, exports, notifications)",
        "knowledge_match": {"categories": {"api-reference", "integration"}, "tags": {"output", "response", "export", "notification"}, "keywords": {"response", "export", "report", "send", "notify"}},
    },
    "persistence": {
        "question": "How is state stored? (database schema, files, cache)",
        "knowledge_match": {"categories": {"architecture", "technical-context"}, "tags": {"database", "storage", "schema", "cache", "persistence"}, "keywords": {"table", "schema", "store", "persist", "save", "database"}},
    },
    "error-handling": {
        "question": "What happens on failure? (retries, alerts, fallbacks, error responses)",
        "knowledge_match": {"categories": {"architecture", "technical-context"}, "tags": {"error", "retry", "fallback", "resilience"}, "keywords": {"error", "fail", "retry", "fallback", "exception", "timeout"}},
    },
    "scale": {
        "question": "Expected load and performance requirements?",
        "knowledge_match": {"categories": {"business-context", "technical-context"}, "tags": {"performance", "scale", "load", "concurrent"}, "keywords": {"concurrent", "throughput", "latency", "scale", "performance", "users per"}},
    },
    "definition-of-done": {
        "question": "How does the user verify the system works? What does 'done' look like?",
        "knowledge_match": {"categories": {"business-context", "requirement"}, "tags": {"done", "success", "acceptance", "criteria"}, "keywords": {"done", "success", "complete", "acceptance", "verify", "deliver"}},
    },
}


def _check_understanding_completeness(project: str, assumptions: list = None):
    """Check that critical knowledge categories are covered (known or assumed).

    Only runs if project has source-document knowledge (indicating docs were registered).
    Returns (verdict: "PASS"|"WARN"|"FAIL"|"SKIP", details: dict)
    """
    _s = _get_storage()

    if not _s.exists(project, 'knowledge'):
        return "SKIP", {}

    k_data = _s.load_data(project, 'knowledge')
    all_knowledge = [k for k in k_data.get("knowledge", []) if k.get("status") == "ACTIVE"]

    # Only run if source documents have been registered
    has_source_docs = any(k.get("category") == "source-document" for k in all_knowledge)
    if not has_source_docs:
        return "SKIP", {}

    # Check each critical category
    covered = {}
    missing = {}

    for cat_name, cat_def in CRITICAL_CATEGORIES.items():
        match = cat_def["knowledge_match"]
        found = False

        for k in all_knowledge:
            # Match by category
            if k.get("category") in match["categories"]:
                found = True
                break
            # Match by tags
            k_tags = {t.lower() for t in k.get("tags", [])}
            if k_tags & match["tags"]:
                found = True
                break
            # Match by keywords in content
            content_lower = (k.get("content", "") + " " + k.get("title", "")).lower()
            if any(kw in content_lower for kw in match["keywords"]):
                found = True
                break

        # Also check assumptions
        if not found and assumptions:
            for a in assumptions:
                a_text = (a.get("assumption", "") + " " + a.get("basis", "")).lower()
                if any(kw in a_text for kw in match["keywords"]):
                    found = True
                    break

        if found:
            covered[cat_name] = True
        else:
            missing[cat_name] = cat_def["question"]

    gap_count = len(missing)
    details = {"covered": list(covered.keys()), "missing": missing, "gap_count": gap_count}

    if gap_count <= 2:
        return "PASS", details
    elif gap_count <= 4:
        return "WARN", details
    else:
        return "FAIL", details


def cmd_draft_plan(args):
    """Store a draft plan for user review before materializing into pipeline."""
    tracker = load_tracker(args.project)

    try:
        draft_tasks = load_json_data(args.data)
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON: {e}")

    if not isinstance(draft_tasks, list):
        raise ValidationError("--data must be a JSON array")

    _trace(args.project, {"event": "draft_plan.start",
           "task_count": len(draft_tasks),
           "has_assumptions": bool(getattr(args, "assumptions", None)),
           "has_coverage": bool(getattr(args, "coverage", None)),
           "objective": getattr(args, "objective", None),
           "idea": getattr(args, "idea", None)})

    # Validate against add-tasks contract
    errors = validate_contract(CONTRACTS["add-tasks"], draft_tasks)
    _trace(args.project, {"event": "draft_plan.contract_validation",
           "errors": len(errors), "first_errors": errors[:5]})
    if errors:
        detail = "\n".join(f"  {e}" for e in errors[:10])
        raise ValidationError(f"{len(errors)} validation issues:\n{detail}")

    # Readiness gate: check assumptions if provided
    assumptions = None
    high_count = 0
    assumptions_raw = getattr(args, "assumptions", None)
    if assumptions_raw:
        assumptions, high_count = _check_assumptions_readiness(assumptions_raw)
        if high_count >= 5:
            high_details = "\n".join(f"  - {a['assumption']} (basis: {a['basis']})"
                                     for a in assumptions if a["severity"] == "HIGH")
            raise PreconditionError(
                f"Readiness gate FAILED — {high_count} HIGH-severity assumptions.\n"
                f"A plan built on 5+ unverified assumptions is not a plan. Clarify before planning:\n"
                f"{high_details}"
            )

    # Understanding completeness gate
    understanding_verdict, understanding_details = _check_understanding_completeness(
        args.project, assumptions)
    if understanding_verdict == "FAIL":
        missing = understanding_details["missing"]
        questions = "\n".join(f"  ? {cat}: {q}" for cat, q in missing.items())
        raise PreconditionError(
            f"Understanding gate FAILED — {understanding_details['gap_count']} critical knowledge gaps:\n"
            f"{questions}\n\n"
            f"Resolve by:\n"
            f"  1. Ingest source documents: knowledge add + research add (category=ingestion)\n"
            f"  2. Add knowledge: python -m core.knowledge add {{project}} --data '[...]'\n"
            f"  3. Add assumptions: --assumptions '[...]'"
        )
    if understanding_verdict == "WARN":
        missing = understanding_details["missing"]
        print(f"\n**UNDERSTANDING WARNING**: {understanding_details['gap_count']} knowledge gaps:", file=sys.stderr)
        for cat, q in missing.items():
            print(f"  ? {cat}: {q}", file=sys.stderr)
        print(f"  Plan saved but verify these before starting execution.\n", file=sys.stderr)
    trace_cmd(args.project, "pipeline", "understanding_gate",
              verdict=understanding_verdict, **understanding_details)

    # OPEN decisions gate: block on unresolved clarifications and HIGH risks
    _s = _get_storage()
    if _s.exists(args.project, 'decisions'):
        dec_data = _s.load_data(args.project, 'decisions')
        open_decisions = [d for d in dec_data.get("decisions", []) if d.get("status") == "OPEN"]
        blocking_clarifications = [d for d in open_decisions if d.get("type") == "clarification_needed"]
        blocking_risks = [d for d in open_decisions
                          if d.get("type") == "risk" and d.get("severity") == "HIGH"]
        warn_risks = [d for d in open_decisions
                      if d.get("type") == "risk" and d.get("severity") in ("MEDIUM", "LOW")]

        if blocking_clarifications:
            details = "\n".join(f"  {d['id']}: {d.get('issue', '')}" for d in blocking_clarifications)
            raise PreconditionError(
                f"Cannot plan — {len(blocking_clarifications)} OPEN clarification(s) need resolution:\n"
                f"{details}\n\n"
                f"Resolve by closing these decisions (answer the questions) or convert to assumptions."
            )
        if blocking_risks:
            details = "\n".join(f"  {d['id']} [{d.get('severity')}]: {d.get('issue', '')}" for d in blocking_risks)
            raise PreconditionError(
                f"Cannot plan — {len(blocking_risks)} OPEN HIGH-severity risk(s) unresolved:\n"
                f"{details}\n\n"
                f"Resolve by: update status to ANALYZING/MITIGATED/ACCEPTED, or add mitigation_plan."
            )
        if warn_risks:
            print(f"\n**RISK WARNING**: {len(warn_risks)} OPEN risk(s) (MEDIUM/LOW):", file=sys.stderr)
            for d in warn_risks[:5]:
                print(f"  {d['id']}: {d.get('issue', '')[:80]}", file=sys.stderr)
            print(f"  Plan saved — review before starting execution.\n", file=sys.stderr)

        trace_cmd(args.project, "pipeline", "open_decisions_gate",
                  blocking_clarifications=len(blocking_clarifications),
                  blocking_risks=len(blocking_risks),
                  warn_risks=len(warn_risks))

    # Requirement → Objective mapping check (warning, not blocking)
    if _s.exists(args.project, 'knowledge'):
        k_data = _s.load_data(args.project, 'knowledge')
        requirements = [k for k in k_data.get("knowledge", [])
                        if k.get("category") == "requirement" and k.get("status") == "ACTIVE"]
        if requirements:
            unmapped = []
            for req in requirements:
                has_objective_link = any(
                    le.get("entity_type") == "objective"
                    for le in req.get("linked_entities", [])
                )
                if not has_objective_link:
                    unmapped.append(req)
            if unmapped:
                print(f"\n**REQUIREMENT WARNING**: {len(unmapped)} requirement(s) not linked to any Objective:",
                      file=sys.stderr)
                for r in unmapped[:10]:
                    print(f"  {r['id']}: {r.get('title', '')[:60]}", file=sys.stderr)
                print(f"  Link with: knowledge link {{project}} --data "
                      f"'[{{\"knowledge_id\": \"K-NNN\", \"entity_type\": \"objective\", "
                      f"\"entity_id\": \"O-NNN\", \"relation\": \"required\"}}]'\n",
                      file=sys.stderr)
            trace_cmd(args.project, "pipeline", "requirement_mapping_check",
                      total_requirements=len(requirements), unmapped=len(unmapped))

    # Coverage gate: check all source requirements are accounted for
    coverage = None
    coverage_deferred = []
    coverage_raw = getattr(args, "coverage", None)
    if coverage_raw:
        coverage, missing_count, coverage_deferred = _check_coverage(coverage_raw)
        if missing_count > 0:
            missing_details = "\n".join(f"  MISSING: {item['requirement']}"
                                        for item in coverage if item["status"] == "MISSING")
            raise PreconditionError(
                f"Coverage gate FAILED — {missing_count} requirement(s) with status MISSING.\n"
                f"Every source requirement must be COVERED by a task, or explicitly DEFERRED/OUT_OF_SCOPE with a reason:\n"
                f"{missing_details}"
            )

    # Store draft (overwrite previous draft)
    tracker["draft_plan"] = {
        "source_idea_id": args.idea if hasattr(args, "idea") and args.idea else None,
        "source_objective_id": args.objective if hasattr(args, "objective") and args.objective else None,
        "created": now_iso(),
        "tasks": draft_tasks,
        "assumptions": assumptions,
        "coverage": coverage,
    }

    save_tracker(args.project, tracker)

    # AC quality warnings (non-blocking at draft time — shows errors for user to fix)
    _warn_ac_quality(draft_tasks)

    # Reference validation (non-blocking at draft time)
    ref_warnings = _validate_plan_references(draft_tasks, args.project)
    if ref_warnings:
        print()
        print(f"**REFERENCE WARNINGS** ({len(ref_warnings)}):")
        for w in ref_warnings:
            print(w)
        print("Tip: fix invalid origins/scopes/knowledge_ids before approving.")
        print()

    # Context validation: auto-load project context, validate plan against it
    ctx_errors, ctx_summary = _validate_plan_context(draft_tasks, args.project)
    if ctx_summary:
        print()
        print("**PROJECT CONTEXT** (auto-loaded — verify your plan accounts for these):")
        for line in ctx_summary:
            print(line)
        print()
    if ctx_errors:
        print(f"**CONTEXT ERRORS** ({len(ctx_errors)}) — fix before approving:")
        for e in ctx_errors:
            print(e)
        print()

    # Assumptions warnings
    if assumptions and 3 <= high_count <= 4:
        print(f"**ASSUMPTION WARNING**: {high_count} HIGH-severity assumptions — verify before Phase 1.")
        for a in assumptions:
            if a["severity"] == "HIGH":
                print(f"  - {a['assumption']}")
        print()

    # Coverage summary
    if coverage_deferred:
        print(f"**DEFERRED/OUT_OF_SCOPE** ({len(coverage_deferred)}):")
        for item in coverage_deferred:
            print(f"  [{item['status']}] {item['requirement']}: {item.get('reason', '')}")
        print()

    print(f"## Draft Plan: {args.project}")
    if tracker["draft_plan"]["source_idea_id"]:
        print(f"Source idea: {tracker['draft_plan']['source_idea_id']}")
    if tracker["draft_plan"].get("source_objective_id"):
        print(f"Source objective: {tracker['draft_plan']['source_objective_id']}")
    print(f"Tasks in draft: {len(draft_tasks)}")
    if assumptions:
        high = sum(1 for a in assumptions if a["severity"] == "HIGH")
        med = sum(1 for a in assumptions if a["severity"] == "MED")
        low = sum(1 for a in assumptions if a["severity"] == "LOW")
        print(f"Assumptions: {len(assumptions)} ({high} HIGH, {med} MED, {low} LOW)")
    if coverage:
        covered = sum(1 for c in coverage if c["status"] == "COVERED")
        deferred = sum(1 for c in coverage if c["status"] in ("DEFERRED", "OUT_OF_SCOPE"))
        print(f"Coverage: {covered} covered, {deferred} deferred/out-of-scope, {len(coverage)} total requirements")
    print()

    _print_draft_tasks(draft_tasks)

    print()
    print("**This is a DRAFT. Tasks are NOT yet in the pipeline.**")
    print("Review the plan above, then:")
    print("  - `python -m core.pipeline approve-plan {project}` — materialize into pipeline")
    print("  - `python -m core.pipeline show-draft {project}` — view again")
    print("  - `python -m core.pipeline draft-plan {project} --data '...'` — replace with new draft")

    _trace(args.project, {
        "event": "draft_plan.complete",
        "task_count": len(draft_tasks),
        "tasks": [{"id": t.get("id"), "name": t.get("name"), "type": t.get("type"),
                   "scopes": t.get("scopes", []), "origin": t.get("origin", ""),
                   "ac_count": len(t.get("acceptance_criteria", [])),
                   "depends_on": t.get("depends_on", []),
                   "knowledge_ids": t.get("knowledge_ids", [])}
                  for t in draft_tasks],
        "assumptions_high": high_count,
        "assumptions_total": len(assumptions) if assumptions else 0,
        "coverage_total": len(coverage) if coverage else 0,
        "ctx_errors": ctx_errors,
        "ctx_summary": ctx_summary,
        "ref_warnings": ref_warnings,
        "source_objective": tracker["draft_plan"].get("source_objective_id"),
        "source_idea": tracker["draft_plan"].get("source_idea_id"),
    })


def cmd_show_draft(args):
    """Show the current draft plan."""
    tracker = load_tracker(args.project)
    draft = tracker.get("draft_plan")

    if not draft or not draft.get("tasks"):
        print(f"No draft plan for '{args.project}'.")
        return

    print(f"## Draft Plan: {args.project}")
    if draft.get("source_idea_id"):
        print(f"Source idea: {draft['source_idea_id']}")
    if draft.get("source_objective_id"):
        print(f"Source objective: {draft['source_objective_id']}")
    print(f"Created: {draft.get('created', '')}")
    print(f"Tasks: {len(draft['tasks'])}")
    print()

    _print_draft_tasks(draft["tasks"])

    print()
    print("**DRAFT — not yet in pipeline.**")
    print("Run `approve-plan` to materialize, or `draft-plan` to replace.")


def cmd_approve_plan(args):
    """Approve draft plan: materialize tasks into pipeline and mark idea COMMITTED."""
    mapping = {}
    entries = []

    # Atomic section: lock -> load -> remap -> validate -> save
    with tracker_lock(args.project):
        tracker = load_tracker(args.project)
        draft = tracker.get("draft_plan")

        if not draft or not draft.get("tasks"):
            raise PreconditionError(f"No draft plan for '{args.project}'.")

        draft_tasks = draft["tasks"]
        source_idea_id = draft.get("source_idea_id")
        source_objective_id = draft.get("source_objective_id")

        # Remap temporary IDs
        mapping = _remap_temp_ids(draft_tasks, tracker["tasks"])

        # Check for duplicate IDs against existing tasks (after remap)
        existing_ids = {t["id"] for t in tracker["tasks"]}
        for t in draft_tasks:
            if t["id"] in existing_ids:
                raise ValidationError(f"Duplicate task ID '{t['id']}' — already exists in pipeline.")

        # Build task entries (same logic as cmd_add_tasks)
        entries = []
        for t in draft_tasks:
            entry = _build_task_entry(t, source_idea_id=source_idea_id,
                                      source_objective_id=source_objective_id)
            entries.append(entry)

        # AC hard gate: feature/bug tasks must have acceptance criteria
        has_ac_errors = _warn_ac_quality(entries)
        if has_ac_errors:
            raise ValidationError("Cannot approve plan — feature/bug tasks without acceptance criteria.")

        # Reference validation (non-blocking warnings)
        ref_warnings = _validate_plan_references(entries, args.project)
        if ref_warnings:
            print(f"**REFERENCE WARNINGS** ({len(ref_warnings)}):", file=sys.stderr)
            for w in ref_warnings:
                print(w, file=sys.stderr)

        # Context validation (blocking: scope/guideline mismatches)
        ctx_errors, _ = _validate_plan_context(entries, args.project)
        if ctx_errors:
            if not getattr(args, "force", False):
                detail = "\n".join(ctx_errors)
                raise ValidationError(
                    f"Context validation failed ({len(ctx_errors)} issues):\n{detail}\n"
                    f"Fix scope assignments or use --force to override."
                )
            else:
                print(f"WARNING: Context validation failed ({len(ctx_errors)} issues):", file=sys.stderr)
                for e in ctx_errors:
                    print(e, file=sys.stderr)
                print("Proceeding due to --force.", file=sys.stderr)

        # Validate DAG
        all_tasks = tracker["tasks"] + entries
        dag_errors = validate_dag(all_tasks)
        if dag_errors:
            detail = "\n".join(f"  {e}" for e in dag_errors)
            raise ValidationError(f"Task graph validation failed:\n{detail}")

        # Materialize
        tracker["tasks"].extend(entries)
        tracker["plan_approved_at"] = now_iso()

        # Clear draft
        tracker.pop("draft_plan", None)

        save_tracker(args.project, tracker)

    # Print ID mapping (outside lock)
    if mapping:
        print("ID mapping:")
        for temp, real in sorted(mapping.items()):
            print(f"  {temp} -> {real}")

    # Mark source idea as COMMITTED (outside lock — separate entity)
    if source_idea_id:
        _s = _get_storage()
        if _s.exists(args.project, 'ideas'):
            ideas_data = _s.load_data(args.project, 'ideas')
            for idea in ideas_data.get("ideas", []):
                if idea["id"] == source_idea_id:
                    if idea["status"] == "APPROVED":
                        idea["status"] = "COMMITTED"
                        idea["committed_at"] = now_iso()
                        idea["updated"] = now_iso()
                        _s.save_data(args.project, 'ideas', ideas_data)
                        print(f"Idea {source_idea_id} marked as COMMITTED.")
                    elif idea["status"] == "COMMITTED":
                        pass  # already committed
                    else:
                        print(f"WARNING: Idea {source_idea_id} is {idea['status']}, "
                              f"expected APPROVED. Not changing status.",
                              file=sys.stderr)
                    break

    print(f"## Plan approved: {args.project}")
    print(f"Materialized {len(entries)} tasks into pipeline.")
    print()
    print_task_list(tracker)
    print(f"\nRun `next {args.project}` to start execution.")

    _trace(args.project, {
        "event": "approve_plan.complete", "task_count": len(entries),
        "id_mapping": mapping,
        "tasks_materialized": [{"id": e["id"], "name": e["name"], "type": e.get("type"),
                                "scopes": e.get("scopes", []), "origin": e.get("origin", ""),
                                "ac_count": len(e.get("acceptance_criteria", []))}
                               for e in entries],
    })


def _print_draft_tasks(tasks: list):
    """Print draft tasks in a readable format."""
    print("| # | ID | Name | Dependencies | Type | Scopes |")
    print("|---|-----|------|-------------|------|--------|")
    for i, t in enumerate(tasks, 1):
        deps = ", ".join(t.get("depends_on", [])) or "—"
        task_type = t.get("type", "feature")
        scopes = ", ".join(t.get("scopes", [])) or "—"
        print(f"| {i} | {t['id']} | {t['name']} | {deps} | {task_type} | {scopes} |")

    # Show details
    print()
    for t in tasks:
        print(f"### {t['id']}: {t['name']}")
        if t.get("description"):
            print(f"  {t['description']}")
        if t.get("instruction"):
            print(f"  **Instruction**: {t['instruction'][:100]}...")
        if t.get("acceptance_criteria"):
            print(f"  **Acceptance criteria**: {len(t['acceptance_criteria'])} items")
            for ac in t["acceptance_criteria"]:
                if isinstance(ac, dict):
                    text = ac.get("text", "")
                    tmpl = ac.get("from_template")
                    print(f"    - {text}" + (f" (from {tmpl})" if tmpl else ""))
                else:
                    print(f"    - {ac}")
        print()
