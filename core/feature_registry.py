"""Feature Registry — tracks what features exist in the codebase.

Built automatically from completed tasks. Queried before planning to detect
conflicts with existing implementations.

Data lives in forge_output/{project}/features.json.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_common import _get_storage, _trace, get_project_dir
from pipeline_context import _extract_key_terms


def _extract_routes_from_diff(diff_text: str) -> list[str]:
    """Extract route paths from git diff (e.g., /api/priorities, /itrp/settings)."""
    routes = set()
    # Backend routes: @router.get("/...", prefix="/api/..."
    for match in re.findall(r'["\'](/api/[a-z0-9/_\-{}]+)["\']', diff_text):
        routes.add(match.split("{")[0].rstrip("/"))
    # Frontend routes: app/xxx/page.tsx → /xxx
    for match in re.findall(r'app/([a-z0-9\-/]+)/page\.tsx', diff_text):
        routes.add(f"/{match}")
    # Next.js router.push("/...")
    for match in re.findall(r'router\.push\(["\'](/[a-z0-9/\-]+)["\']', diff_text):
        routes.add(match)
    return sorted(routes)


def _extract_components_from_diff(diff_text: str) -> list[str]:
    """Extract component/function names from git diff."""
    components = set()
    # React components: export default function XxxPage
    for match in re.findall(r'export default function (\w+)', diff_text):
        components.add(match)
    # Named exports: export function Xxx
    for match in re.findall(r'export function (\w+)', diff_text):
        components.add(match)
    # FastAPI routers: router = APIRouter(prefix="...")
    for match in re.findall(r'APIRouter\(prefix=["\']([^"\']+)["\']', diff_text):
        components.add(f"router:{match}")
    return sorted(components)


def register_feature(project: str, task: dict, diff_text: str = ""):
    """Register what a completed task produced in the Feature Registry.

    Called automatically by cmd_complete after recording changes.
    """
    _s = _get_storage()
    features_data = _s.load_data(project, "features") if _s.exists(project, "features") else {"features": []}
    features = features_data.get("features", [])

    task_id = task.get("id", "?")
    origin = task.get("origin", "")
    name = task.get("name", "")

    # Extract what was built
    routes = _extract_routes_from_diff(diff_text)
    components = _extract_components_from_diff(diff_text)
    key_terms = sorted(_extract_key_terms(
        " ".join(filter(None, [task.get("instruction", ""), task.get("description", "")]))
    ))[:15]

    # Build produces summary from task or from diff
    produces = task.get("produces", {})

    entry = {
        "task_id": task_id,
        "task_name": name,
        "origin": origin,
        "routes": routes,
        "components": components,
        "produces": produces,
        "key_terms": key_terms,
        "scope": task.get("scopes", []),
    }

    # Deduplicate: replace if same task_id exists
    features = [f for f in features if f.get("task_id") != task_id]
    features.append(entry)

    features_data["features"] = features
    _s.save_data(project, "features", features_data)

    _trace(project, {
        "event": "feature_registry.register",
        "task": task_id,
        "routes": routes,
        "components": components,
        "terms_count": len(key_terms),
    })

    if routes or components:
        print(f"  Feature registered: {len(routes)} routes, {len(components)} components",
              file=sys.stderr)


def check_conflicts(project: str, new_tasks: list) -> list[str]:
    """Check if new tasks conflict with registered features.

    Returns list of FEATURE_CONFLICT warning strings.
    Called by draft-plan before materializing tasks.
    """
    _s = _get_storage()
    if not _s.exists(project, "features"):
        return []

    features_data = _s.load_data(project, "features")
    features = features_data.get("features", [])
    if not features:
        return []

    # Build index: route → feature, terms → feature
    route_index: dict[str, list[dict]] = {}
    for f in features:
        for route in f.get("routes", []):
            route_index.setdefault(route, []).append(f)

    warnings = []
    for task in new_tasks:
        task_text = " ".join(filter(None, [
            task.get("instruction", ""),
            task.get("description", ""),
        ]))
        task_origin = task.get("origin", "")

        # Check 1: Route conflicts
        # Look for route patterns in task instruction
        task_routes = set()
        for match in re.findall(r'(/api/[a-z0-9/_\-{}]+|/[a-z0-9\-]+/[a-z0-9\-]+)', task_text.lower()):
            clean = match.split("{")[0].rstrip("/")
            if len(clean) > 4:
                task_routes.add(clean)
        # Also check for app/xxx/page.tsx patterns
        for match in re.findall(r'app/([a-z0-9\-/]+)/page', task_text.lower()):
            task_routes.add(f"/{match}")

        for route in task_routes:
            if route in route_index:
                for existing in route_index[route]:
                    if existing.get("origin") != task_origin:
                        warnings.append(
                            f"FEATURE_CONFLICT: task '{task.get('name', task.get('id', '?'))}' "
                            f"references route '{route}' which was created by "
                            f"{existing['task_id']} ({existing['task_name']}, {existing['origin']}). "
                            f"Extend existing or justify new implementation."
                        )

        # Check 2: Key term overlap with existing features from other objectives
        task_terms = _extract_key_terms(task_text)
        for f in features:
            if f.get("origin") == task_origin:
                continue
            f_terms = set(f.get("key_terms", []))
            if not f_terms:
                continue
            overlap = task_terms & f_terms
            ratio = len(overlap) / max(len(f_terms), 1)
            if ratio > 0.4 and len(overlap) >= 4:
                warnings.append(
                    f"FEATURE_OVERLAP: task '{task.get('name', task.get('id', '?'))}' "
                    f"shares {len(overlap)} terms ({ratio:.0%}) with registered feature "
                    f"from {f['task_id']} ({f['task_name']}, {f['origin']}). "
                    f"Terms: {', '.join(sorted(overlap)[:5])}"
                )

    return warnings


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_show(args):
    """Show registered features for a project."""
    _s = _get_storage()
    if not _s.exists(args.project, "features"):
        print(f"No features registered for '{args.project}'.")
        return

    data = _s.load_data(args.project, "features")
    features = data.get("features", [])

    print(f"## Feature Registry: {args.project}")
    print(f"Registered features: {len(features)}")
    print()

    for f in features:
        print(f"**{f['task_id']}** ({f.get('task_name', '?')}) — origin: {f.get('origin', '?')}")
        if f.get("routes"):
            print(f"  Routes: {', '.join(f['routes'])}")
        if f.get("components"):
            print(f"  Components: {', '.join(f['components'])}")
        if f.get("produces"):
            for k, v in f["produces"].items():
                print(f"  Produces {k}: {v}")
        if f.get("key_terms"):
            print(f"  Terms: {', '.join(f['key_terms'][:8])}")
        print()


def cmd_check(args):
    """Check draft tasks against feature registry."""
    import json as _json
    tasks = _json.loads(args.data)
    if not isinstance(tasks, list):
        tasks = [tasks]
    warnings = check_conflicts(args.project, tasks)
    if warnings:
        print(f"**FEATURE CONFLICTS** ({len(warnings)}):")
        for w in warnings:
            print(f"  {w}")
    else:
        print("No feature conflicts detected.")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")

    show_p = sub.add_parser("show")
    show_p.add_argument("project")

    check_p = sub.add_parser("check")
    check_p.add_argument("project")
    check_p.add_argument("--data", required=True)

    args = parser.parse_args()
    if args.command == "show":
        cmd_show(args)
    elif args.command == "check":
        cmd_check(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
