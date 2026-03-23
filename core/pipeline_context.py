"""Pipeline context assembly — task execution context for LLM."""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_common import (
    _get_storage, _trace, load_tracker, save_tracker, find_task,
    find_task_model, print_task_detail, load_project_config, get_project_dir,
)
from errors import ForgeError, ValidationError, EntityNotFound, PreconditionError
from models import Task
from storage import JSONFileStorage, now_iso, load_json_data


def _objective_kr_pct(baseline, target, current) -> int:
    """Calculate KR progress percentage (0-100)."""
    try:
        baseline, target, current = float(baseline), float(target), float(current)
    except (TypeError, ValueError):
        return 0
    total_delta = target - baseline
    if total_delta == 0:
        return 100 if current == target else 0
    return max(0, min(100, int((current - baseline) / total_delta * 100)))


def _estimate_context_size(project: str, task_ids: set) -> int:
    """Estimate context size in characters for the given dependency tasks."""
    total = 0
    _s = _get_storage()
    for entity in ("changes", "decisions", "lessons"):
        if _s.exists(project, entity):
            data = _s.load_data(project, entity)
            for entry in data.get(entity, []):
                if entry.get("task_id") in task_ids:
                    total += len(json.dumps(entry))
    return total


def _check_plan_staleness(task, tracker):
    """Check if files mentioned in task instruction were modified since plan approval.

    Uses git log to detect external changes. Returns list of warning strings.
    """
    import subprocess as _sp

    if isinstance(task, dict):
        task = Task.from_dict(task)

    approved_at = tracker.get("plan_approved_at")
    if not approved_at:
        return []

    instruction = (task.instruction or "") + " " + (task.description or "")
    if not instruction.strip():
        return []

    # Extract file paths from instruction (patterns: backtick paths, quoted paths, common extensions)
    path_patterns = re.findall(
        r'`([^`]+\.[a-zA-Z]{1,5})`'           # `path/to/file.ext`
        r'|(?:^|\s)([\w/\-\.]+\.[a-zA-Z]{1,5})'  # bare path/to/file.ext
        r'|(?:^|\s)([\w/\-]+/[\w/\-]+)',            # directory/paths
        instruction
    )
    # Flatten and deduplicate
    candidates = set()
    for groups in path_patterns:
        for g in groups:
            if g and len(g) > 3 and '/' in g:
                candidates.add(g.strip())

    if not candidates:
        return []

    warnings = []
    for filepath in sorted(candidates):
        try:
            result = _sp.run(
                f'git log --oneline --since="{approved_at}" -- "{filepath}"',
                shell=True, capture_output=True, text=True,
                encoding="utf-8", timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                commits = result.stdout.strip().split("\n")
                warnings.append(
                    f"`{filepath}` modified since plan approval ({len(commits)} commit(s)): "
                    f"{commits[0][:60]}"
                )
        except Exception:
            pass

    return warnings


def _check_contract_alignment(task, tracker):
    """Check if task instruction references key terms from dependency produces contracts.

    Returns list of warning strings (empty if all aligned).
    """
    if isinstance(task, dict):
        task = Task.from_dict(task)

    warnings = []
    instruction = ((task.instruction or "") + " " + (task.description or "")).lower()

    stop_words = {"http", "https", "with", "from", "that", "this", "will", "must",
                  "should", "into", "when", "then", "each", "also", "used", "none"}

    for dep_id in task.depends_on:
        dep_raw = None
        for t in tracker["tasks"]:
            if t["id"] == dep_id:
                dep_raw = t
                break
        if not dep_raw:
            continue
        dep = Task.from_dict(dep_raw)
        if not dep.produces:
            continue

        for key, val in dep.produces.items():
            val_str = str(val).lower()
            terms = re.split(r'[\s/\->{},():\[\]]+', val_str)
            terms = [t for t in terms if len(t) > 3 and t not in stop_words]

            if terms and not any(term in instruction for term in terms):
                warnings.append(
                    f"Dependency {dep_id} produces `{key}: {val}` "
                    f"but task instruction does not reference it. Verify alignment."
                )

    # Warn when depends_on is non-empty but uses_from_dependencies is missing
    if task.depends_on and not task.uses_from_dependencies:
        warnings.append(
            f"Task has {len(task.depends_on)} dependencies but no `uses_from_dependencies`. "
            f"Specify what this task consumes from each dependency to prevent decorative arrows."
        )

    # Warn when uses_from_dependencies references a dep not in depends_on
    if task.uses_from_dependencies:
        for ref_id in task.uses_from_dependencies:
            if ref_id not in task.depends_on:
                warnings.append(
                    f"`uses_from_dependencies` references `{ref_id}` which is not in `depends_on`."
                )

    return warnings


def cmd_context(args):
    """Show aggregated context for a task: dependency outputs, decisions, changes."""
    tracker = load_tracker(args.project)
    task = find_task_model(tracker, args.task_id)
    lean = getattr(args, "lean", False)

    # Accumulate what we load for trace
    _ctx_trace = {"sections_shown": [], "lean": lean}

    # Project config
    project_config = load_project_config(args.project)
    project_dir = project_config.get("project_dir", "")

    print(f"## Context for {args.task_id}: {task.name}")
    if project_dir:
        print(f"**Project dir**: `{project_dir}`")
    if lean:
        print("*(lean mode — Knowledge, Research, Business Context, Lessons skipped)*")
    print()

    # Pre-load decisions (used in multiple sections below)
    _s = _get_storage()
    dec_data = _s.load_data(args.project, 'decisions')

    # Task details
    if task.description:
        print(f"**Description**: {task.description}")
    if task.instruction:
        print(f"**Instruction**: {task.instruction}")
    print()

    # Alignment contract (persisted from planning)
    alignment = task.alignment
    if alignment:
        print("### Alignment Contract")
        print()
        if alignment.get("goal"):
            print(f"**Goal**: {alignment['goal']}")
        bounds = alignment.get("boundaries", {})
        if bounds.get("must"):
            print("**Must**:")
            for m in bounds["must"]:
                print(f"  - {m}")
        if bounds.get("must_not"):
            print("**Must not**:")
            for m in bounds["must_not"]:
                print(f"  - {m}")
        if bounds.get("not_in_scope"):
            print("**Not in scope**:")
            for m in bounds["not_in_scope"]:
                print(f"  - {m}")
        if alignment.get("success"):
            print(f"**Success criteria**: {alignment['success']}")
        print()

    # Exclusions (task-specific DO NOT rules)
    excl = task.exclusions
    if excl:
        print("### Exclusions")
        print()
        for ex in excl:
            print(f"- **DO NOT**: {ex}")
        print()

    # Source requirements (traceability)
    if task.source_requirements:
        # Load knowledge to resolve linked objectives
        k_data_sr = _s.load_data(args.project, 'knowledge') if _s.exists(args.project, 'knowledge') else {}
        k_by_id = {k["id"]: k for k in k_data_sr.get("knowledge", [])}

        print("### Source Requirements")
        print()
        for sr in task.source_requirements:
            k_id = sr.get("knowledge_id", "?")
            text = sr.get("text", "")
            ref = sr.get("source_ref", "")
            ref_str = f" _(from {ref})_" if ref else ""
            # Show linked objective if exists
            k_obj = k_by_id.get(k_id)
            obj_link = ""
            if k_obj:
                for le in k_obj.get("linked_entities", []):
                    if le.get("entity_type") == "objective":
                        obj_link = f" → {le['entity_id']}"
                        break
            print(f"- **{k_id}**{obj_link}: {text}{ref_str}")
        print()

    # Objective context (if task has origin O-NNN)
    if task.origin and task.origin.startswith("O-") and _s.exists(args.project, 'objectives'):
        obj_data = _s.load_data(args.project, 'objectives')
        for obj in obj_data.get("objectives", []):
            if obj["id"] == task.origin:
                print(f"### Objective: {obj['id']} — {obj.get('title', '')}")
                print(f"**Status**: {obj.get('status', '')} | **Description**: {obj.get('description', '')[:150]}")
                krs = obj.get("key_results", [])
                if krs:
                    print(f"**Key Results** ({len(krs)}):")
                    for kr in krs:
                        if kr.get("target") is not None:
                            current = kr.get("current", kr.get("baseline", 0))
                            pct = _objective_kr_pct(kr.get("baseline", 0), kr["target"], current)
                            print(f"  - {kr['id']}: {kr.get('metric', '')} — {current}/{kr['target']} ({pct}%)")
                        else:
                            print(f"  - {kr['id']}: {kr.get('description', '')} [{kr.get('status', 'NOT_STARTED')}]")
                print()
                break

    # Project-level decisions (from INGESTION, PLANNING, etc. — not task-specific)
    if dec_data:
        special_task_ids = {"INGESTION", "PLANNING", "ONBOARDING", "DISCOVERY"}
        project_decisions = [d for d in dec_data.get("decisions", [])
                             if d.get("task_id") in special_task_ids
                             and d.get("status") == "CLOSED"]
        # Also include CLOSED architecture decisions regardless of task_id
        arch_decisions = [d for d in dec_data.get("decisions", [])
                          if d.get("type") == "architecture" and d.get("status") == "CLOSED"
                          and d.get("task_id") not in special_task_ids]
        all_project_decisions = project_decisions + arch_decisions
        if all_project_decisions:
            # Dedup by ID
            seen_ids = set()
            unique = [d for d in all_project_decisions if d["id"] not in seen_ids and not seen_ids.add(d["id"])]
            print(f"### Project Decisions ({len(unique)})")
            print()
            for d in unique[:15]:
                rec = d.get("recommendation", d.get("override_value", ""))
                if rec:
                    print(f"- **{d['id']}** [{d.get('type', '')}]: {d.get('issue', '')[:60]} → {rec[:80]}")
                else:
                    print(f"- **{d['id']}** [{d.get('type', '')}]: {d.get('issue', '')[:80]}")
            if len(unique) > 15:
                print(f"  _...and {len(unique) - 15} more_")
            print()
            _ctx_trace["sections_shown"].append("project_decisions")
            _ctx_trace["project_decisions_count"] = len(unique)

    # Plan staleness check: were files modified since plan approval?
    staleness_warnings = _check_plan_staleness(task, tracker)
    if staleness_warnings:
        print("### Plan Staleness Warnings")
        print()
        print("These files were modified **after** the plan was approved. Your task instruction may be outdated:")
        print()
        for w in staleness_warnings:
            print(f"- {w}")
        print()
        print("**Action**: Read the modified files before starting. If changes conflict with your instruction, create an OPEN decision.")
        print()

    # Dependency context
    deps = task.depends_on
    if deps:
        print(f"### Completed Dependencies")
        print()
        for dep_id in deps:
            dep = Task.from_dict(find_task(tracker, dep_id))
            print(f"**{dep_id}** — {dep.name} ({dep.status})")
            if dep.description:
                print(f"  {dep.description}")
            if dep.produces:
                print(f"  **Produces**:")
                for key, val in dep.produces.items():
                    print(f"    {key}: {val}")
            print()

        # Show what this task consumes from dependencies
        if task.uses_from_dependencies:
            print(f"### Uses from Dependencies")
            print()
            for dep_id, usage in task.uses_from_dependencies.items():
                print(f"  **{dep_id}**: {usage}")
            print()

        # Contract alignment check
        contract_warnings = _check_contract_alignment(task, tracker)
        if contract_warnings:
            print("### Contract Alignment Warnings")
            print()
            for w in contract_warnings:
                print(f"- {w}")
            print()

        # Show changes from dependency tasks
        changes_data = _s.load_data(args.project, 'changes')
        dep_changes = [c for c in changes_data.get("changes", [])
                       if c.get("task_id") in deps]
        if dep_changes:
            print(f"### Changes from Dependencies")
            print()
            print("| Task | File | Action | Summary |")
            print("|------|------|--------|---------|")
            for c in dep_changes:
                summary = c.get("summary", "")[:50]
                print(f"| {c['task_id']} | {c['file']} | {c['action']} | {summary} |")
            print()
            # Prominent instruction to read dependency files
            dep_files = sorted({c["file"] for c in dep_changes if c.get("file")})
            if dep_files:
                print("**READ THESE FILES before starting** (modified by dependencies):")
                for f in dep_files:
                    print(f"  - `{f}`")
                print()

        # Show decisions from dependency tasks
        if dec_data:
            dep_decisions = [d for d in dec_data.get("decisions", [])
                             if d.get("task_id") in deps]
            if dep_decisions:
                print(f"### Decisions from Dependencies")
                print()
                for d in dep_decisions:
                    status = d.get("status", "")
                    print(f"- **{d['id']}** ({status}): {d.get('issue', '')}")
                    if d.get("recommendation"):
                        print(f"  Recommendation: {d['recommendation']}")
                print()
    else:
        print("No dependencies — this is a root task.")
        print()

    if deps:
        _ctx_trace["sections_shown"].append("dependencies")
        _ctx_trace["dependency_count"] = len(deps)
        _ctx_trace["dependency_ids"] = deps

    # Show open decisions for this task
    if dec_data:
        task_decisions = [d for d in dec_data.get("decisions", [])
                          if d.get("task_id") == args.task_id]
        if task_decisions:
            print(f"### Existing Decisions for This Task")
            print()
            for d in task_decisions:
                print(f"- **{d['id']}** ({d.get('status', '')}): {d.get('issue', '')}")
            print()

        # Show decisions that AFFECT this task (from other tasks' --deferred)
        affecting = [d for d in dec_data.get("decisions", [])
                     if args.task_id in (d.get("affects") or [])
                     and d.get("task_id") != args.task_id]
        if affecting:
            print(f"### Decisions Affecting This Task")
            print()
            for d in affecting:
                print(f"- **{d['id']}** ({d.get('status', '')}): {d.get('issue', '')}")
                if d.get("recommendation"):
                    print(f"  → {d['recommendation']}")
            print()

    # Show relevant lessons (skip in lean mode)
    if not lean:
        lessons_data = _s.load_data(args.project, 'lessons')
        lessons = lessons_data.get("lessons", [])
        if lessons:
            print(f"### Relevant Lessons")
            print()
            for l in lessons:
                print(f"- **{l['id']}** [{l.get('severity', '')}]: {l['title']}")
            print()
            _ctx_trace["sections_shown"].append("lessons")
            _ctx_trace["lessons_count"] = len(lessons)

    # Compute task_scopes (shared by guidelines and knowledge scope matching)
    g_data = _s.load_data(args.project, 'guidelines')
    project_guidelines = [g for g in g_data.get("guidelines", []) if g.get("status") == "ACTIVE"]

    task_scopes = set(task.scopes)
    origin_for_scopes = task.origin
    if origin_for_scopes.startswith("O-") and _s.exists(args.project, 'objectives'):
        obj_data_scopes = _s.load_data(args.project, 'objectives')
        for obj in obj_data_scopes.get("objectives", []):
            if obj["id"] == origin_for_scopes:
                task_scopes.update(obj.get("scopes", []))
                derived_gl_ids = set(obj.get("derived_guidelines", []))
                if derived_gl_ids:
                    for g in project_guidelines:
                        if g["id"] in derived_gl_ids and g.get("scope"):
                            task_scopes.add(g["scope"])
                break
    elif origin_for_scopes.startswith("I-") and _s.exists(args.project, 'ideas'):
        ideas_data_sc = _s.load_data(args.project, 'ideas')
        for idea in ideas_data_sc.get("ideas", []):
            if idea["id"] == origin_for_scopes:
                task_scopes.update(idea.get("scopes", []))
                obj_ids_sc = {kr.split("/")[0] for kr in idea.get("advances_key_results", []) if "/" in kr}
                if obj_ids_sc and _s.exists(args.project, 'objectives'):
                    obj_data_sc = _s.load_data(args.project, 'objectives')
                    for obj in obj_data_sc.get("objectives", []):
                        if obj["id"] in obj_ids_sc:
                            derived_gl_ids = set(obj.get("derived_guidelines", []))
                            for g in project_guidelines:
                                if g["id"] in derived_gl_ids and g.get("scope"):
                                    task_scopes.add(g["scope"])
                break
    task_scopes.add("general")

    # Guidelines context (uses shared renderer from guidelines module)
    global_guidelines = []
    if args.project != "_global":
        g_global = _s.load_global('guidelines')
        global_guidelines = [g for g in g_global.get("guidelines", []) if g.get("status") == "ACTIVE"]

    # In lean mode, only show must-weight guidelines
    if lean:
        project_guidelines = [g for g in project_guidelines if g.get("weight") == "must"]
        global_guidelines = [g for g in global_guidelines if g.get("weight") == "must"]

    if global_guidelines or project_guidelines:
        from guidelines import render_guidelines_context
        lines = render_guidelines_context(project_guidelines, task_scopes, args.project,
                                           global_guidelines=global_guidelines)
        for line in lines:
            print(line)
        _ctx_trace["sections_shown"].append("guidelines")
        _ctx_trace["guidelines_project"] = len(project_guidelines)
        _ctx_trace["guidelines_global"] = len(global_guidelines)
        _ctx_trace["guidelines_scopes_matched"] = list(task_scopes)

    # Knowledge context (from task.knowledge_ids + origin chain + scope matching)
    k_ids = set(task.knowledge_ids)
    origin_k = task.origin
    if origin_k.startswith("I-"):
        if _s.exists(args.project, 'ideas'):
            ideas_data = _s.load_data(args.project, 'ideas')
            for idea in ideas_data.get("ideas", []):
                if idea["id"] == origin_k:
                    k_ids.update(idea.get("knowledge_ids", []))
                    obj_ids_k = {kr.split("/")[0] for kr in idea.get("advances_key_results", []) if "/" in kr}
                    if obj_ids_k and _s.exists(args.project, 'objectives'):
                        obj_data_k = _s.load_data(args.project, 'objectives')
                        for obj in obj_data_k.get("objectives", []):
                            if obj["id"] in obj_ids_k:
                                k_ids.update(obj.get("knowledge_ids", []))
                    break
    elif origin_k.startswith("O-"):
        if _s.exists(args.project, 'objectives'):
            obj_data_k = _s.load_data(args.project, 'objectives')
            for obj in obj_data_k.get("objectives", []):
                if obj["id"] == origin_k:
                    k_ids.update(obj.get("knowledge_ids", []))
                    break

    # Load knowledge data once (used for both explicit and scope matching; skip in lean mode)
    k_data = {}
    if not lean and _s.exists(args.project, 'knowledge'):
        k_data = _s.load_data(args.project, 'knowledge')

    # Scope-matched knowledge (additive to explicit IDs)
    scope_matched_k_ids = set()
    if task_scopes and k_data:
        for k_obj in k_data.get("knowledge", []):
            if k_obj.get("status") != "ACTIVE":
                continue
            k_scopes = set(k_obj.get("scopes", []))
            if k_scopes & task_scopes and k_obj["id"] not in k_ids:
                scope_matched_k_ids.add(k_obj["id"])

    all_k_ids = k_ids | scope_matched_k_ids
    if all_k_ids and k_data:
        k_objects = {k["id"]: k for k in k_data.get("knowledge", [])
                     if k.get("status") == "ACTIVE"}

        explicit_linked = [k_objects[kid] for kid in sorted(k_ids) if kid in k_objects]
        scope_linked = [k_objects[kid] for kid in sorted(scope_matched_k_ids) if kid in k_objects]

        # Cap scope-matched at 10 to prevent context bloat
        if len(scope_linked) > 10:
            scope_linked = scope_linked[:10]

        total = len(explicit_linked) + len(scope_linked)
        if total > 0:
            print(f"### Knowledge ({total})")
            print()
            for k in explicit_linked:
                print(f"**{k['id']}**: {k['title']} [{k['category']}]")
                content_preview = k.get("content", "")[:200]
                if content_preview:
                    print(f"  {content_preview}")
            if scope_linked:
                print()
                print(f"*Scope-matched ({len(scope_linked)}):*")
                for k in scope_linked:
                    print(f"**{k['id']}**: {k['title']} [{k['category']}]")
                    content_preview = k.get("content", "")[:200]
                    if content_preview:
                        print(f"  {content_preview}")
            _ctx_trace["sections_shown"].append("knowledge")
            _ctx_trace["knowledge_explicit"] = list(k_ids)
            _ctx_trace["knowledge_scope_matched"] = len(scope_linked) if 'scope_linked' in dir() else 0
            print()

    # Research context (from task origin -> idea/objective -> research; skip in lean mode)
    if not lean and _s.exists(args.project, 'research'):
        r_data = _s.load_data(args.project, 'research')
        active_research = [r for r in r_data.get("research", [])
                          if r.get("status") == "ACTIVE"]
        task_research = []
        origin = task.origin

        if origin.startswith("I-"):
            # Research linked to origin idea
            task_research = [r for r in active_research
                            if r.get("linked_entity_id") == origin
                            or r.get("linked_idea_id") == origin]
            # Also research linked to objective (via idea.advances_key_results)
            if _s.exists(args.project, 'ideas'):
                ideas_data_r = _s.load_data(args.project, 'ideas')
                for idea in ideas_data_r.get("ideas", []):
                    if idea["id"] == origin:
                        obj_ids_r = {kr.split("/")[0] for kr in idea.get("advances_key_results", []) if "/" in kr}
                        task_research.extend([r for r in active_research
                                             if r.get("linked_entity_id") in obj_ids_r
                                             and r["id"] not in {x["id"] for x in task_research}])
                        break
        elif origin.startswith("O-"):
            # Direct objective origin (from /plan O-001)
            task_research = [r for r in active_research
                            if r.get("linked_entity_id") == origin]

        if task_research:
            seen = set()
            unique = [r for r in task_research if r["id"] not in seen and not seen.add(r["id"])]
            print(f"### Research ({len(unique)})")
            print()
            for r in sorted(unique, key=lambda x: x["id"]):
                print(f"**{r['id']}**: {r['title']} [{r['category']}]")
                if r.get("summary"):
                    print(f"  {r['summary'][:200]}")
                for f in (r.get("key_findings") or [])[:5]:
                    print(f"  - {f}")
                if r.get("decision_ids"):
                    print(f"  Related decisions: {', '.join(r['decision_ids'])}")
            print()
            _ctx_trace["sections_shown"].append("research")
            _ctx_trace["research_count"] = len(unique)

    # Test requirements
    test_req = task.test_requirements
    if test_req:
        print(f"### Test Requirements")
        print()
        parts = []
        if test_req.get("unit"):
            parts.append("unit")
        if test_req.get("integration"):
            parts.append("integration")
        if test_req.get("e2e"):
            parts.append("e2e")
        if parts:
            print(f"Required: {', '.join(parts)}")
        if test_req.get("description"):
            print(f"{test_req['description']}")
        print()

    # Business context: trace task → origin → objective (skip in lean mode)
    origin = task.origin
    if not lean and origin.startswith("O-"):
        # Direct objective origin (from /plan O-001)
        if _s.exists(args.project, 'objectives'):
            obj_data = _s.load_data(args.project, 'objectives')
            for obj in obj_data.get("objectives", []):
                if obj["id"] == origin:
                    print("### Business Context")
                    print()
                    print(f"**{obj['id']}**: {obj['title']} [{obj['status']}]")
                    for kr in obj.get("key_results", []):
                        target = kr.get("target")
                        if target is not None:
                            baseline = kr.get("baseline", 0)
                            current = kr.get("current", baseline)
                            pct = _objective_kr_pct(baseline, target, current)
                            print(f"  {kr['id']}: {kr.get('metric', '')} — {current}/{target} ({pct}%)")
                        else:
                            desc = kr.get("description") or kr.get("metric", "")
                            status = kr.get("status", "")
                            print(f"  {kr['id']}: {desc} [{status}]")
                    print(f"  Origin: objective {origin}")
                    print()
                    break
    elif not lean and origin.startswith("I-"):
        if _s.exists(args.project, 'ideas') and _s.exists(args.project, 'objectives'):
            ideas_data = _s.load_data(args.project, 'ideas')
            obj_data = _s.load_data(args.project, 'objectives')
            # Find origin idea
            origin_idea = None
            for idea in ideas_data.get("ideas", []):
                if idea["id"] == task.origin:
                    origin_idea = idea
                    break
            if origin_idea and origin_idea.get("advances_key_results"):
                # Find linked objectives
                obj_ids = {kr_ref.split("/")[0] for kr_ref in origin_idea["advances_key_results"]
                           if "/" in kr_ref}
                linked_objs = [o for o in obj_data.get("objectives", []) if o["id"] in obj_ids]
                if linked_objs:
                    print("### Business Context")
                    print()
                    for obj in linked_objs:
                        print(f"**{obj['id']}**: {obj['title']} [{obj['status']}]")
                        # Show only relevant KRs
                        relevant_kr_ids = {kr_ref.split("/")[1] for kr_ref in origin_idea["advances_key_results"]
                                           if kr_ref.startswith(obj["id"] + "/")}
                        for kr in obj.get("key_results", []):
                            if kr["id"] in relevant_kr_ids:
                                target = kr.get("target")
                                if target is not None:
                                    baseline = kr.get("baseline", 0)
                                    current = kr.get("current", baseline)
                                    pct = _objective_kr_pct(baseline, target, current)
                                    print(f"  {kr['id']}: {kr.get('metric', '')} — {current}/{target} ({pct}%)")
                                else:
                                    desc = kr.get("description") or kr.get("metric", "")
                                    status = kr.get("status", "")
                                    print(f"  {kr['id']}: {desc} [{status}]")
                    print(f"  Via idea: {origin_idea['id']} \"{origin_idea['title']}\"")
                    print()
                    _ctx_trace["sections_shown"].append("business_context_via_idea")

    if origin.startswith("O-"):
        _ctx_trace["sections_shown"].append("business_context_via_objective")

    # Risks (type=risk decisions) linked to this task or origin idea
    if _s.exists(args.project, 'decisions'):
        risk_decisions = [d for d in dec_data.get("decisions", [])
                          if d.get("type") == "risk"
                          and d.get("status") not in ("CLOSED",)]
        task_risks = [d for d in risk_decisions
                      if d.get("linked_entity_type") == "task"
                      and d.get("linked_entity_id") == args.task_id]
        # Also show risks from origin idea
        if task.origin and task.origin.startswith("I-"):
            idea_risks = [d for d in risk_decisions
                          if d.get("linked_entity_type") == "idea"
                          and d.get("linked_entity_id") == task.origin]
            task_risks.extend(idea_risks)
        # Also show risks from origin objective
        if task.origin and task.origin.startswith("O-"):
            obj_risks = [d for d in risk_decisions
                         if d.get("linked_entity_type") == "objective"
                         and d.get("linked_entity_id") == task.origin]
            task_risks.extend(obj_risks)
        if task_risks:
            print(f"### Active Risks ({len(task_risks)})")
            print()
            for r in task_risks:
                print(f"- **{r['id']}** [{r.get('severity', '')}/{r.get('likelihood', '')}] "
                      f"({r.get('status', '')}): {r.get('issue', '')}")
                if r.get("mitigation_plan"):
                    print(f"  Mitigation: {r['mitigation_plan'][:80]}")
            print()
            _ctx_trace["sections_shown"].append("risks")
            _ctx_trace["risks_count"] = len(task_risks)

    # Context budget estimate
    all_task_ids = set(deps) | {args.task_id}
    ctx_chars = _estimate_context_size(args.project, all_task_ids)
    ctx_kb = ctx_chars / 1024
    print(f"### Context Budget")
    print(f"Estimated context from dependencies: {ctx_kb:.1f} KB ({ctx_chars} chars)")
    if ctx_kb > 50:
        print(f"**WARNING**: Large context. Consider summarizing older dependency outputs.")
    print()

    # Comprehensive trace of what context was delivered to LLM
    _ctx_trace["context_size_kb"] = round(ctx_kb, 1)
    _ctx_trace["task_id"] = args.task_id
    _ctx_trace["task_scopes"] = list(task_scopes) if 'task_scopes' in dir() else task.scopes
    _ctx_trace["dependencies"] = deps
    _ctx_trace["has_alignment"] = bool(task.alignment)
    _ctx_trace["has_exclusions"] = bool(task.exclusions)
    _ctx_trace["has_produces"] = bool(task.produces)
    _ctx_trace["has_uses_from_deps"] = bool(task.uses_from_dependencies)
    _ctx_trace["ac_count"] = len(task.acceptance_criteria)
    _trace(args.project, {"event": "context.delivered", **_ctx_trace})


def cmd_config(args):
    """Set or show project configuration."""
    from pipeline_tasks import CONTRACTS

    tracker = load_tracker(args.project)

    if args.data:
        try:
            config = load_json_data(args.data)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON: {e}")

        if not isinstance(config, dict):
            raise ValidationError("--data must be a JSON object")

        known_keys = set(CONTRACTS["config"]["optional"])
        unknown = set(config.keys()) - known_keys
        if unknown:
            print(f"WARNING: Unknown config keys: {', '.join(sorted(unknown))}", file=sys.stderr)

        existing = tracker.get("config", {})
        existing.update(config)
        tracker["config"] = existing
        save_tracker(args.project, tracker)

        print(f"Config updated for '{args.project}':")
        for k, v in existing.items():
            print(f"  {k}: {v}")
    else:
        config = tracker.get("config", {})
        if not config:
            print(f"No config set for '{args.project}'.")
            print()
            print("Set with:")
            print(f'  python -m core.pipeline config {args.project} --data \'{{"test_cmd": "pytest", "lint_cmd": "ruff check .", "branch_prefix": "forge/"}}\'')
            return
        print(f"## Config: {args.project}")
        print()
        for k, v in config.items():
            print(f"  {k}: {v}")
