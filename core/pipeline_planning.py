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


def _validate_plan_references(entries: list, project: str) -> tuple:
    """Validate origin, scopes, knowledge_ids references (Contract C3).

    Returns (errors: list[str], warnings: list[str]).
    Errors = hard gate (invalid origin/knowledge refs).
    Warnings = soft (scope mismatches).
    """
    errors = []
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
        valid_k_ids = {k["id"] for k in k_data
                       if k.get("status", "ACTIVE") in ("ACTIVE", "DRAFT")}
    if _s.exists(project, 'guidelines'):
        g_data = _s.load_data(project, 'guidelines').get("guidelines", [])
        valid_scopes = {g["scope"] for g in g_data if g.get("scope") and g.get("status") == "ACTIVE"}
        valid_scopes.add("general")

    for t in entries:
        tid = t.get("id", "?")

        # Origin validation — HARD GATE (Contract C3)
        origin = t.get("origin", "")
        if origin:
            if origin.startswith("I-") and origin not in valid_idea_ids:
                errors.append(f"  {tid}: origin '{origin}' — idea not found")
            elif origin.startswith("O-") and origin not in valid_obj_ids:
                errors.append(f"  {tid}: origin '{origin}' — objective not found")

        # Scope validation — soft warning
        for scope in t.get("scopes", []):
            if valid_scopes and scope != "general" and scope not in valid_scopes:
                warnings.append(f"  {tid}: scope '{scope}' — no guidelines with this scope")

        # Knowledge validation — HARD GATE (Contract C3)
        for kid in t.get("knowledge_ids", []):
            if kid not in valid_k_ids:
                errors.append(f"  {tid}: knowledge '{kid}' — not found or not ACTIVE/DRAFT")

    return errors, warnings


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


def validate_ingestion_completeness(project: str) -> tuple:
    """Validate that ingestion produced all required artifacts (Contract C1).

    Returns (verdict: "PASS"|"WARN"|"FAIL"|"SKIP", details: dict).
    SKIP = no source documents registered (standalone project — ingestion not needed).
    FAIL = ingestion incomplete — hard gate should block.
    WARN = ingestion has minor gaps.
    PASS = ingestion contract satisfied.
    """
    _s = _get_storage()

    if not _s.exists(project, 'knowledge'):
        return "SKIP", {"reason": "no knowledge store"}

    k_data = _s.load_data(project, 'knowledge')
    # Include ACTIVE and DRAFT (DRAFT is valid after ingestion, before review)
    valid_statuses = {"ACTIVE", "DRAFT"}
    all_knowledge = [k for k in k_data.get("knowledge", [])
                     if k.get("status", "ACTIVE") in valid_statuses]

    source_docs = [k for k in all_knowledge if k.get("category") == "source-document"]
    if not source_docs:
        return "SKIP", {"reason": "no source documents registered"}

    errors = []
    warnings = []

    # 1. Check extraction ratio (≥2 facts per source document)
    fact_categories = {"requirement", "domain-rules", "technical-context", "architecture",
                       "api-reference", "business-context", "integration", "infrastructure"}
    extracted_facts = [k for k in all_knowledge if k.get("category") in fact_categories]
    ratio = len(extracted_facts) / len(source_docs) if source_docs else 0

    if len(extracted_facts) == 0:
        errors.append(f"Zero facts extracted from {len(source_docs)} source document(s). "
                      f"Run /ingest to extract requirements, rules, and context.")
    elif ratio < 2:
        warnings.append(f"Low extraction ratio: {len(extracted_facts)} facts from "
                        f"{len(source_docs)} documents (avg {ratio:.1f}/doc, expected ≥2).")

    # 2. Check ingestion records exist
    has_research = _s.exists(project, 'research')
    ingestion_records = []
    if has_research:
        r_data = _s.load_data(project, 'research')
        ingestion_records = [r for r in r_data.get("research", [])
                             if r.get("category") == "ingestion"]

    if not ingestion_records:
        warnings.append(f"No ingestion records (R-NNN category=ingestion). "
                        f"Ingestion may not have been tracked properly.")

    # 3. Check 9 critical categories coverage
    category_coverage = {}
    for cat_name, cat_def in CRITICAL_CATEGORIES.items():
        match = cat_def["knowledge_match"]
        found = False
        for k in all_knowledge:
            if k.get("category") in match["categories"]:
                found = True
                break
            k_tags = {t.lower() for t in k.get("tags", [])}
            if k_tags & match["tags"]:
                found = True
                break
            content_lower = (k.get("content", "") + " " + k.get("title", "")).lower()
            if any(kw in content_lower for kw in match["keywords"]):
                found = True
                break

        # Also check if decisions cover this category
        has_decision = False
        if _s.exists(project, 'decisions'):
            d_data = _s.load_data(project, 'decisions')
            for d in d_data.get("decisions", []):
                d_text = (d.get("issue", "") + " " + d.get("recommendation", "")).lower()
                if any(kw in d_text for kw in match["keywords"]):
                    has_decision = True
                    break

        if found:
            category_coverage[cat_name] = "KNOWN"
        elif has_decision:
            category_coverage[cat_name] = "ASSUMED"
        else:
            category_coverage[cat_name] = "MISSING"

    missing_categories = {k: v for k, v in category_coverage.items() if v == "MISSING"}
    if len(missing_categories) > 4:
        errors.append(f"{len(missing_categories)}/9 critical categories not covered: "
                      f"{', '.join(missing_categories.keys())}. "
                      f"Run /ingest to extract knowledge for these areas.")
    elif len(missing_categories) > 2:
        warnings.append(f"{len(missing_categories)}/9 critical categories not covered: "
                        f"{', '.join(missing_categories.keys())}.")

    # Determine verdict
    if errors:
        verdict = "FAIL"
    elif warnings:
        verdict = "WARN"
    else:
        verdict = "PASS"

    details = {
        "source_docs": len(source_docs),
        "extracted_facts": len(extracted_facts),
        "extraction_ratio": round(ratio, 1),
        "ingestion_records": len(ingestion_records),
        "category_coverage": category_coverage,
        "missing_categories": list(missing_categories.keys()),
        "errors": errors,
        "warnings": warnings,
    }

    return verdict, details


def cmd_validate_ingestion(args):
    """CLI command: validate ingestion completeness (Contract C1)."""
    project = args.project
    verdict, details = validate_ingestion_completeness(project)

    print(f"## Ingestion Validation: {project}")
    print(f"Verdict: {verdict}")
    print()

    if verdict == "SKIP":
        print(f"  No source documents registered — ingestion validation not applicable.")
        print(f"  (This is fine for standalone projects without source documentation.)")
        return

    print(f"  Source documents: {details['source_docs']}")
    print(f"  Extracted facts: {details['extracted_facts']} (ratio: {details['extraction_ratio']}/doc)")
    print(f"  Ingestion records: {details['ingestion_records']}")
    print()

    # Category coverage table
    print("  Category coverage (9 critical):")
    for cat, status in details['category_coverage'].items():
        icon = {"KNOWN": "[+]", "ASSUMED": "[~]", "MISSING": "[-]"}[status]
        print(f"    {icon} {cat}: {status}")
    print()

    if details['errors']:
        print("  ERRORS (must fix before /analyze):")
        for e in details['errors']:
            print(f"    ! {e}")
        print()

    if details['warnings']:
        print("  WARNINGS:")
        for w in details['warnings']:
            print(f"    ? {w}")
        print()

    if verdict == "PASS":
        print("  Ingestion complete. Ready for /analyze.")
    elif verdict == "WARN":
        print("  Ingestion has minor gaps. /analyze can proceed but review warnings.")
    else:
        print("  Ingestion INCOMPLETE. Fix errors before running /analyze.")
        sys.exit(1)

    trace_cmd(project, "pipeline", "validate_ingestion", verdict=verdict, **details)


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

    # Contract C1: Ingestion completeness gate
    ing_verdict, ing_details = validate_ingestion_completeness(args.project)
    if ing_verdict == "FAIL":
        error_lines = "\n".join(f"  ! {e}" for e in ing_details.get("errors", []))
        raise PreconditionError(
            f"Ingestion completeness gate FAILED (Contract C1).\n"
            f"{error_lines}\n\n"
            f"Fix: run /ingest to extract facts from source documents, "
            f"then /analyze to create objectives.\n"
            f"Check: python -m core.pipeline validate-ingestion {args.project}"
        )
    elif ing_verdict == "WARN":
        warn_lines = "\n".join(f"  ? {w}" for w in ing_details.get("warnings", []))
        print(f"\n**INGESTION WARNING** (Contract C1):\n{warn_lines}\n", file=sys.stderr)

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

    # Extraction completeness check (heuristic)
    _s = _get_storage()
    if _s.exists(args.project, 'knowledge') and _s.exists(args.project, 'research'):
        k_all = _s.load_data(args.project, 'knowledge')
        r_all = _s.load_data(args.project, 'research')
        source_docs = [k for k in k_all.get("knowledge", [])
                       if k.get("category") == "source-document"]
        ingestion_records = [r for r in r_all.get("research", [])
                             if r.get("category") == "ingestion"]
        extracted_facts = [k for k in k_all.get("knowledge", [])
                           if k.get("category") in ("requirement", "domain-rules", "technical-context",
                                                     "architecture", "api-reference", "integration",
                                                     "infrastructure", "business-context")
                           and k.get("source", {}).get("type") == "documentation"]

        if source_docs:
            unprocessed = []
            ingested_paths = {r.get("file_path", "") for r in ingestion_records}
            for doc in source_docs:
                doc_path = doc.get("source", {}).get("ref", "")
                if doc_path and doc_path not in ingested_paths:
                    unprocessed.append(doc)

            if unprocessed:
                print(f"\n**EXTRACTION WARNING**: {len(unprocessed)} registered document(s) not ingested:",
                      file=sys.stderr)
                for d in unprocessed[:5]:
                    print(f"  {d['id']}: {d.get('source', {}).get('ref', '?')}", file=sys.stderr)
                print(f"  Run ingestion before planning.\n", file=sys.stderr)

            if source_docs and not extracted_facts:
                print(f"\n**EXTRACTION WARNING**: {len(source_docs)} source document(s) registered "
                      f"but 0 facts extracted. Run ingestion.\n", file=sys.stderr)
            elif source_docs and extracted_facts:
                ratio = len(extracted_facts) / len(source_docs)
                if ratio < 2:
                    print(f"\n**EXTRACTION WARNING**: Low extraction ratio — {len(extracted_facts)} facts "
                          f"from {len(source_docs)} documents (avg {ratio:.1f}/doc). "
                          f"Typical: 5-20 facts per document. Review ingestion quality.\n",
                          file=sys.stderr)

            trace_cmd(args.project, "pipeline", "extraction_completeness",
                      source_docs=len(source_docs), ingestion_records=len(ingestion_records),
                      extracted_facts=len(extracted_facts),
                      unprocessed=len(unprocessed) if source_docs else 0)

    # OPEN decisions gate: block on unresolved clarifications and HIGH risks
    if _s.exists(args.project, 'decisions'):
        dec_data = _s.load_data(args.project, 'decisions')
        open_decisions = [d for d in dec_data.get("decisions", []) if d.get("status") == "OPEN"]
        blocking_clarifications = [d for d in open_decisions if d.get("type") == "clarification_needed"]
        blocking_risks = [d for d in open_decisions
                          if d.get("type") == "risk" and d.get("severity") == "HIGH"]
        # Unresolved assumptions: OPEN architecture/other decisions with LOW confidence
        # These are assumptions created during ingestion that haven't been confirmed
        open_assumptions = [d for d in open_decisions
                            if d.get("type") not in ("clarification_needed", "risk", "exploration")
                            and d.get("confidence") == "LOW"]
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

        # Unresolved assumptions: count as HIGH assumptions for the readiness gate
        if open_assumptions:
            # Merge with explicit --assumptions for unified counting
            assumption_count = high_count + len(open_assumptions)
            if assumption_count >= 5:
                details = "\n".join(f"  {d['id']}: {d.get('issue', '')[:80]}" for d in open_assumptions[:10])
                explicit_note = f" + {high_count} from --assumptions" if high_count else ""
                raise PreconditionError(
                    f"Readiness gate FAILED — {len(open_assumptions)} unresolved assumptions in decisions"
                    f"{explicit_note} = {assumption_count} total.\n"
                    f"OPEN assumptions (LOW confidence decisions):\n{details}\n\n"
                    f"Resolve by: close decisions (accept/reject) or provide --assumptions with basis."
                )
            elif len(open_assumptions) >= 3:
                print(f"\n**ASSUMPTION WARNING**: {len(open_assumptions)} OPEN low-confidence decisions "
                      f"(unresolved assumptions):", file=sys.stderr)
                for d in open_assumptions[:5]:
                    print(f"  {d['id']}: {d.get('issue', '')[:80]}", file=sys.stderr)
                print(f"  Confirm or close before starting execution.\n", file=sys.stderr)

        if warn_risks:
            print(f"\n**RISK WARNING**: {len(warn_risks)} OPEN risk(s) (MEDIUM/LOW):", file=sys.stderr)
            for d in warn_risks[:5]:
                print(f"  {d['id']}: {d.get('issue', '')[:80]}", file=sys.stderr)
            print(f"  Plan saved — review before starting execution.\n", file=sys.stderr)

        trace_cmd(args.project, "pipeline", "open_decisions_gate",
                  blocking_clarifications=len(blocking_clarifications),
                  blocking_risks=len(blocking_risks),
                  open_assumptions=len(open_assumptions),
                  warn_risks=len(warn_risks))

    # Contract C2: Analysis completeness gate
    from objectives import validate_analysis_completeness
    c2_verdict, c2_details = validate_analysis_completeness(args.project)
    if c2_verdict == "FAIL":
        error_lines = "\n".join(f"  ! {e}" for e in c2_details.get("errors", []))
        raise PreconditionError(
            f"Analysis completeness gate FAILED (Contract C2).\n"
            f"{error_lines}\n\n"
            f"Fix: run /analyze to create objectives with measurable KRs from ingested requirements.\n"
            f"Check: python -m core.objectives verify {args.project}"
        )
    elif c2_verdict == "WARN":
        warn_lines = "\n".join(f"  ? {w}" for w in c2_details.get("warnings", []))
        print(f"\n**ANALYSIS WARNING** (Contract C2):\n{warn_lines}\n", file=sys.stderr)
    trace_cmd(args.project, "pipeline", "analysis_completeness_gate",
              verdict=c2_verdict, **{k: v for k, v in c2_details.items()
                                     if k not in ("errors", "warnings")})

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
    elif _s.exists(args.project, 'knowledge'):
        # Auto-populate coverage from requirement knowledge objects
        k_data_cov = _s.load_data(args.project, 'knowledge')
        req_knowledge = [k for k in k_data_cov.get("knowledge", [])
                         if k.get("category") == "requirement" and k.get("status") == "ACTIVE"]
        if req_knowledge:
            # Check which requirements are covered by draft tasks via source_requirements
            task_req_ids = set()
            for t in draft_tasks:
                for sr in t.get("source_requirements", []):
                    if sr.get("knowledge_id"):
                        task_req_ids.add(sr["knowledge_id"])

            auto_coverage = []
            auto_missing = 0
            for req in req_knowledge:
                if req["id"] in task_req_ids:
                    auto_coverage.append({"requirement": req.get("title", req["id"]),
                                          "status": "COVERED", "covered_by": "task"})
                else:
                    auto_coverage.append({"requirement": req.get("title", req["id"]),
                                          "status": "MISSING", "knowledge_id": req["id"]})
                    auto_missing += 1

            if auto_missing > 0:
                missing_details = "\n".join(
                    f"  MISSING: {item['requirement']} ({item.get('knowledge_id', '')})"
                    for item in auto_coverage if item["status"] == "MISSING")
                raise PreconditionError(
                    f"Auto-coverage gate FAILED — {auto_missing} requirement(s) not covered by any task.\n"
                    f"Requirements without matching source_requirements on tasks:\n"
                    f"{missing_details}\n\n"
                    f"Fix by adding source_requirements to tasks, or pass --coverage with DEFERRED/OUT_OF_SCOPE."
                )
            else:
                coverage = auto_coverage
                print(f"  Auto-coverage: {len(req_knowledge)} requirements covered by tasks.",
                      file=sys.stderr)

    # Objective linkage gate: block or warn when no objective is specified
    _objective_arg = args.objective if hasattr(args, "objective") and args.objective else None
    _idea_arg = args.idea if hasattr(args, "idea") and args.idea else None
    if not _objective_arg and not _idea_arg:
        # Check if any tasks have origin set explicitly
        tasks_with_origin = [t for t in draft_tasks if t.get("origin")]
        if not tasks_with_origin:
            # Determine if source documents were ingested (implies /analyze should have run)
            has_source_docs = False
            if _s.exists(args.project, 'knowledge'):
                k_data_obj = _s.load_data(args.project, 'knowledge')
                has_source_docs = any(
                    k.get("category") == "source-document"
                    for k in k_data_obj.get("knowledge", [])
                )

            if _s.exists(args.project, 'objectives'):
                obj_data_link = _s.load_data(args.project, 'objectives')
                active_objs = [o for o in obj_data_link.get("objectives", [])
                               if o.get("status") == "ACTIVE"]
                if active_objs:
                    # HARD GATE: active objectives exist but plan doesn't reference them
                    obj_list = ", ".join(f"{o['id']}" for o in active_objs[:5])
                    more = f" (+{len(active_objs) - 5} more)" if len(active_objs) > 5 else ""
                    raise PreconditionError(
                        f"Objective linkage gate FAILED — no --objective specified and no tasks have origin set.\n"
                        f"  Active objectives exist: {obj_list}{more}\n"
                        f"  Every plan must be linked to an objective so KR auto-update works.\n\n"
                        f"  Fix: add --objective O-NNN to this command, or set origin on each task.\n"
                        f"  List objectives: python -m core.objectives show {{project}}"
                    )
                elif has_source_docs:
                    # HARD GATE: source docs ingested but no objectives created — /analyze was skipped
                    raise PreconditionError(
                        f"Objective linkage gate FAILED — source documents were ingested but no objectives exist.\n"
                        f"  This means /analyze was skipped. Run /analyze first to create objectives from\n"
                        f"  ingested requirements, then plan against those objectives.\n\n"
                        f"  Pipeline: /ingest → /analyze → /plan\n"
                        f"  Run: /analyze to create objectives with measurable KRs."
                    )
                # else: no active objectives and no source docs — standalone project, just warn
            elif has_source_docs:
                # HARD GATE: source docs but no objectives file at all
                raise PreconditionError(
                    f"Objective linkage gate FAILED — source documents were ingested but no objectives exist.\n"
                    f"  Run /analyze first to create objectives from ingested requirements.\n\n"
                    f"  Pipeline: /ingest → /analyze → /plan"
                )
            else:
                # No source docs, no objectives — simple standalone project, just warn
                print(f"\n**OBJECTIVE WARNING**: No objectives defined for this project.",
                      file=sys.stderr)
                print(f"  Plan will proceed without objective linkage. KR tracking unavailable.",
                      file=sys.stderr)
                print(f"  For structured projects, run /objective or /analyze first.\n",
                      file=sys.stderr)

            trace_cmd(args.project, "pipeline", "objective_linkage_gate",
                      has_objective=False, has_idea=False, has_source_docs=has_source_docs,
                      tasks_with_origin=0, total_tasks=len(draft_tasks))

    # Store draft (overwrite previous draft)
    tracker["draft_plan"] = {
        "source_idea_id": _idea_arg,
        "source_objective_id": _objective_arg,
        "created": now_iso(),
        "tasks": draft_tasks,
        "assumptions": assumptions,
        "coverage": coverage,
    }

    save_tracker(args.project, tracker)

    # AC quality warnings (non-blocking at draft time — shows errors for user to fix)
    _warn_ac_quality(draft_tasks)

    # Reference validation (Contract C3 — hard gate for origin/knowledge, soft for scopes)
    ref_errors, ref_warnings = _validate_plan_references(draft_tasks, args.project)
    if ref_errors:
        print()
        print(f"**REFERENCE ERRORS** ({len(ref_errors)}) — must fix before approving:")
        for e in ref_errors:
            print(e)
        print()
    if ref_warnings:
        print()
        print(f"**REFERENCE WARNINGS** ({len(ref_warnings)}):")
        for w in ref_warnings:
            print(w)
        print("Tip: fix invalid scopes before approving.")
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

        # Objective linkage check: warn when tasks have no origin
        tasks_without_origin = [e for e in entries if not e.get("origin")]
        if tasks_without_origin:
            _s_approve = _get_storage()
            has_active_objectives = False
            if _s_approve.exists(args.project, 'objectives'):
                obj_data_approve = _s_approve.load_data(args.project, 'objectives')
                has_active_objectives = any(
                    o.get("status") == "ACTIVE"
                    for o in obj_data_approve.get("objectives", [])
                )
            if has_active_objectives:
                no_origin_ids = ", ".join(e["id"] for e in tasks_without_origin[:5])
                more = f" (+{len(tasks_without_origin) - 5} more)" if len(tasks_without_origin) > 5 else ""
                print(f"\n**OBJECTIVE WARNING**: {len(tasks_without_origin)} task(s) have no origin objective: "
                      f"{no_origin_ids}{more}", file=sys.stderr)
                print(f"  KR auto-update will NOT work for these tasks.", file=sys.stderr)
                print(f"  Fix after approval: update-task --data '{{\"id\": \"T-NNN\", \"origin\": \"O-NNN\"}}'\n",
                      file=sys.stderr)

        # AC hard gate: feature/bug tasks must have acceptance criteria
        has_ac_errors = _warn_ac_quality(entries)
        if has_ac_errors:
            raise ValidationError("Cannot approve plan — feature/bug tasks without acceptance criteria.")

        # Reference validation (Contract C3/C4 — errors block, warnings don't)
        ref_errors, ref_warnings = _validate_plan_references(entries, args.project)
        if ref_errors:
            detail = "\n".join(ref_errors)
            raise ValidationError(
                f"Reference validation failed (Contract C3) — {len(ref_errors)} invalid reference(s):\n"
                f"{detail}\n\nFix origin and knowledge_ids to reference existing entities."
            )
        if ref_warnings:
            print(f"\n**REFERENCE WARNINGS** ({len(ref_warnings)}):", file=sys.stderr)
            for w in ref_warnings:
                print(w, file=sys.stderr)

        # Context validation (blocking: scope/guideline mismatches)
        ctx_errors, _ = _validate_plan_context(entries, args.project)
        if ctx_errors:
            detail = "\n".join(ctx_errors)
            raise ValidationError(
                f"Context validation failed ({len(ctx_errors)} issues):\n{detail}\n"
                f"Fix scope assignments before approving."
            )

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
