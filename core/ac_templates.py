"""
AC Templates — reusable, parameterized acceptance criteria (AC-NNN).

Provides consistent quality standards across tasks. Templates contain
{placeholder} parameters that are filled during instantiation to produce
concrete acceptance criteria text.

Usage:
    python -m core.ac_templates <command> <project> [options]

Commands:
    add          {project} --data '{json}'                      Create templates
    read         {project} [--category X] [--scope X]           List/filter
    show         {project} {template_id}                        Full details
    update       {project} --data '{json}'                      Update template
    instantiate  {project} {template_id} --params '{json}'      Fill params → AC text
    contract     {name}                                         Print contract spec
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from contracts import render_contract, validate_contract
from storage import JSONFileStorage, now_iso

if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


# -- Storage --

def load_or_create(project: str, storage=None) -> dict:
    if storage is None:
        storage = JSONFileStorage()
    return storage.load_data(project, 'ac_templates')


def save_json(project: str, data: dict, storage=None):
    if storage is None:
        storage = JSONFileStorage()
    storage.save_data(project, 'ac_templates', data)


# -- Constants --

VALID_CATEGORIES = {
    "performance", "security", "quality", "functionality",
    "accessibility", "reliability", "data-integrity", "ux",
}

VALID_PARAM_TYPES = {"string", "number", "boolean", "enum", "array"}


# -- Contracts --

CONTRACTS = {
    "add": {
        "required": ["title", "template", "category"],
        "optional": ["description", "parameters", "scopes", "tags",
                      "verification_method"],
        "enums": {
            "category": VALID_CATEGORIES,
        },
        "types": {
            "parameters": list,
            "scopes": list,
            "tags": list,
        },
        "invariant_texts": [
            "title: concise name for the AC template",
            "template: template string with {placeholder} params (e.g., "
            "'API endpoint {endpoint} responds within {max_ms}ms at p{percentile}')",
            "category: one of performance, security, quality, functionality, "
            "accessibility, reliability, data-integrity, ux",
            "description: detailed explanation of what this AC validates",
            "parameters: [{name, type, default (optional), description}] — "
            "each {placeholder} in template should have a matching parameter",
            "scopes: project scopes where this template applies (e.g., ['backend', 'api'])",
            "tags: searchable keywords",
            "verification_method: how to verify/test this criterion",
        ],
        "example": [
            {
                "title": "API Response Time",
                "template": "API endpoint {endpoint} responds within {max_ms}ms at p{percentile}",
                "category": "performance",
                "description": "Ensures API endpoint responds within target latency",
                "parameters": [
                    {"name": "endpoint", "type": "string",
                     "description": "API endpoint path"},
                    {"name": "max_ms", "type": "number", "default": 200,
                     "description": "Max response time in ms"},
                    {"name": "percentile", "type": "number", "default": 95,
                     "description": "Percentile (p95, p99)"},
                ],
                "scopes": ["backend", "api"],
                "tags": ["performance", "latency"],
                "verification_method": "Load test with k6 or equivalent",
            },
        ],
    },
    "update": {
        "required": ["id"],
        "optional": ["title", "template", "description", "category",
                      "parameters", "scopes", "tags", "verification_method",
                      "status"],
        "enums": {
            "category": VALID_CATEGORIES,
            "status": {"ACTIVE", "DEPRECATED"},
        },
        "types": {
            "parameters": list,
            "scopes": list,
            "tags": list,
        },
        "invariant_texts": [
            "id: existing template ID (AC-001, etc.)",
            "Only provided fields are updated — omitted fields stay unchanged",
            "status: ACTIVE or DEPRECATED",
        ],
        "example": [
            {"id": "AC-001", "status": "DEPRECATED"},
            {"id": "AC-003", "template": "Updated template {param}..."},
        ],
    },
}


# -- Helpers --

def find_template(data: dict, template_id: str) -> dict | None:
    """Find AC template by ID."""
    for t in data.get("ac_templates", []):
        if t["id"] == template_id:
            return t
    return None


def _next_id(data: dict) -> str:
    """Generate next AC-NNN ID."""
    existing = [
        int(t["id"].split("-")[1]) for t in data.get("ac_templates", [])
        if t.get("id", "").startswith("AC-")
    ]
    num = max(existing, default=0) + 1
    return f"AC-{num:03d}"


def _extract_placeholders(template: str) -> set[str]:
    """Extract {placeholder} names from a template string."""
    return set(re.findall(r"\{(\w+)\}", template))


def _validate_params_definition(parameters: list, placeholders: set) -> list[str]:
    """Validate parameter definitions against template placeholders."""
    errors = []
    param_names = {p["name"] for p in parameters if "name" in p}

    # Check all placeholders have parameter definitions
    for ph in placeholders:
        if ph not in param_names:
            errors.append(f"Template placeholder '{{{ph}}}' has no matching parameter definition")

    # Validate parameter types
    for p in parameters:
        if "name" not in p:
            errors.append("Parameter missing 'name' field")
            continue
        if p.get("type") and p["type"] not in VALID_PARAM_TYPES:
            errors.append(f"Parameter '{p['name']}' has invalid type '{p['type']}'. "
                          f"Valid: {', '.join(sorted(VALID_PARAM_TYPES))}")

    return errors


# -- Commands --

def cmd_add(args):
    """Create AC templates."""
    try:
        new_items = json.loads(args.data)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(new_items, list):
        print("ERROR: --data must be a JSON array", file=sys.stderr)
        sys.exit(1)

    errors = validate_contract(CONTRACTS["add"], new_items)
    if errors:
        print(f"ERROR: {len(errors)} validation issues:", file=sys.stderr)
        for e in errors[:10]:
            print(f"  {e}", file=sys.stderr)
        sys.exit(1)

    data = load_or_create(args.project)
    timestamp = now_iso()

    # Dedup by (category, title) — normalized
    existing_keys = {
        (t.get("category", "").lower().strip(), t.get("title", "").lower().strip())
        for t in data.get("ac_templates", [])
    }

    added = []
    skipped = []
    for item in new_items:
        category = item["category"].lower().strip()
        key = (category, item["title"].lower().strip())
        if key in existing_keys:
            skipped.append(f"Duplicate: {item['title'][:50]}")
            continue

        # Validate parameters against template placeholders
        parameters = item.get("parameters", [])
        placeholders = _extract_placeholders(item["template"])
        param_errors = _validate_params_definition(parameters, placeholders)
        if param_errors:
            for pe in param_errors:
                print(f"  WARNING: {pe}", file=sys.stderr)

        ac_id = _next_id(data)
        template = {
            "id": ac_id,
            "title": item["title"],
            "description": item.get("description", ""),
            "template": item["template"],
            "category": category,
            "parameters": parameters,
            "scopes": item.get("scopes", []),
            "tags": item.get("tags", []),
            "verification_method": item.get("verification_method", ""),
            "status": "ACTIVE",
            "usage_count": 0,
            "created_at": timestamp,
            "updated_at": timestamp,
        }

        data["ac_templates"].append(template)
        existing_keys.add(key)
        added.append(ac_id)

    save_json(args.project, data)

    print(f"AC Templates saved: {args.project}")
    if added:
        print(f"  Added: {len(added)} ({', '.join(added)})")
    if skipped:
        print(f"  Skipped (duplicate): {len(skipped)}")
    print(f"  Total: {len(data['ac_templates'])}")


def cmd_read(args):
    """List/filter AC templates."""
    storage = JSONFileStorage()
    if not storage.exists(args.project, 'ac_templates'):
        print(f"No AC templates for '{args.project}' yet.")
        return

    data = storage.load_data(args.project, 'ac_templates')
    items = data.get("ac_templates", [])

    # Filter
    if args.category:
        items = [t for t in items if t.get("category") == args.category.lower().strip()]
    if args.scope:
        scope = args.scope.lower().strip()
        items = [t for t in items if scope in t.get("scopes", [])]
    if args.status:
        items = [t for t in items if t.get("status") == args.status]

    # Sort by ID
    items.sort(key=lambda t: t.get("id", ""))

    # Render
    print(f"## AC Templates: {args.project}")
    filters = []
    if args.category:
        filters.append(f"category={args.category}")
    if args.scope:
        filters.append(f"scope={args.scope}")
    if filters:
        print(f"Filter: {', '.join(filters)}")
    print(f"Count: {len(items)}")
    print()

    if not items:
        print("(none)")
        return

    print("| ID | Category | Status | Uses | Title |")
    print("|----|----------|--------|------|-------|")
    for t in items:
        title = t.get("title", "")[:45]
        print(f"| {t['id']} | {t.get('category', '')} | {t.get('status', '')} "
              f"| {t.get('usage_count', 0)} | {title} |")


def cmd_show(args):
    """Show full details of an AC template."""
    data = load_or_create(args.project)
    t = find_template(data, args.template_id)
    if not t:
        print(f"ERROR: Template '{args.template_id}' not found.", file=sys.stderr)
        sys.exit(1)

    print(f"## {t['id']}: {t['title']}")
    print(f"**Category**: {t['category']} | **Status**: {t.get('status', 'ACTIVE')} "
          f"| **Uses**: {t.get('usage_count', 0)}")
    if t.get("scopes"):
        print(f"**Scopes**: {', '.join(t['scopes'])}")
    if t.get("tags"):
        print(f"**Tags**: {', '.join(t['tags'])}")
    print()

    # Description
    if t.get("description"):
        print(f"**Description**: {t['description']}")
        print()

    # Template
    print("### Template")
    print(f"```")
    print(t.get("template", ""))
    print(f"```")
    print()

    # Parameters
    params = t.get("parameters", [])
    if params:
        print("### Parameters")
        print()
        print("| Name | Type | Default | Description |")
        print("|------|------|---------|-------------|")
        for p in params:
            default = p.get("default", "—")
            if default is None:
                default = "—"
            print(f"| `{p['name']}` | {p.get('type', 'string')} | {default} "
                  f"| {p.get('description', '')} |")
        print()

    # Verification
    if t.get("verification_method"):
        print(f"**Verification**: {t['verification_method']}")
        print()

    print(f"Created: {t.get('created_at', '')}")
    print(f"Updated: {t.get('updated_at', '')}")


def cmd_update(args):
    """Update AC templates."""
    try:
        updates = json.loads(args.data)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(updates, list):
        updates = [updates]

    errors = validate_contract(CONTRACTS["update"], updates)
    if errors:
        print(f"ERROR: {len(errors)} validation issues:", file=sys.stderr)
        for e in errors[:10]:
            print(f"  {e}", file=sys.stderr)
        sys.exit(1)

    data = load_or_create(args.project)
    timestamp = now_iso()

    updated = []
    for u in updates:
        t = find_template(data, u["id"])
        if not t:
            print(f"  WARNING: Template {u['id']} not found, skipping", file=sys.stderr)
            continue

        # Validate template + params consistency if template is changed
        if "template" in u:
            params = u.get("parameters", t.get("parameters", []))
            placeholders = _extract_placeholders(u["template"])
            param_errors = _validate_params_definition(params, placeholders)
            if param_errors:
                for pe in param_errors:
                    print(f"  WARNING: {pe}", file=sys.stderr)

        updatable = ["title", "template", "description", "category",
                     "parameters", "scopes", "tags", "verification_method",
                     "status"]
        for field in updatable:
            if field in u:
                t[field] = u[field]

        t["updated_at"] = timestamp
        updated.append(u["id"])

    save_json(args.project, data)

    if updated:
        print(f"Updated: {', '.join(updated)}")
    else:
        print("No templates were updated.")


def cmd_instantiate(args):
    """Instantiate a template with concrete parameters."""
    data = load_or_create(args.project)
    t = find_template(data, args.template_id)
    if not t:
        print(f"ERROR: Template '{args.template_id}' not found.", file=sys.stderr)
        sys.exit(1)

    if t.get("status") == "DEPRECATED":
        print(f"WARNING: Template '{args.template_id}' is DEPRECATED.", file=sys.stderr)

    # Parse params
    try:
        params = json.loads(args.params) if args.params else {}
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON params: {e}", file=sys.stderr)
        sys.exit(1)

    # Build complete params: provided values + defaults
    template_params = t.get("parameters", [])
    resolved = {}
    missing = []

    for p in template_params:
        name = p["name"]
        if name in params:
            resolved[name] = params[name]
        elif "default" in p:
            resolved[name] = p["default"]
        else:
            missing.append(name)

    if missing:
        print(f"ERROR: Missing required parameters: {', '.join(missing)}", file=sys.stderr)
        print(f"Provide via --params '{{\"{'\" : \"...\", \"'.join(missing)}\": \"...\"}}'",
              file=sys.stderr)
        sys.exit(1)

    # Render template (SafeDict leaves unresolved {placeholders} as-is)
    template_str = t.get("template", "")

    class _SafeDict(dict):
        def __missing__(self, key):
            return "{" + key + "}"

    try:
        text = template_str.format_map(_SafeDict({k: str(v) for k, v in resolved.items()}))
    except (ValueError, IndexError) as e:
        print(f"ERROR: Template rendering failed: {e}", file=sys.stderr)
        sys.exit(1)

    # Increment usage count
    t["usage_count"] = t.get("usage_count", 0) + 1
    t["updated_at"] = now_iso()
    save_json(args.project, data)

    # Output structured AC
    result = {
        "text": text,
        "from_template": args.template_id,
        "params": resolved,
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_contract(args):
    """Print contract spec."""
    if args.name not in CONTRACTS:
        print(f"ERROR: Unknown contract '{args.name}'. "
              f"Available: {', '.join(sorted(CONTRACTS.keys()))}",
              file=sys.stderr)
        sys.exit(1)
    print(render_contract(args.name, CONTRACTS[args.name]))


# -- CLI --

def main():
    parser = argparse.ArgumentParser(
        description="Forge AC Templates — reusable acceptance criteria")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("add", help="Create AC templates")
    p.add_argument("project")
    p.add_argument("--data", required=True)

    p = sub.add_parser("read", help="List/filter templates")
    p.add_argument("project")
    p.add_argument("--category", choices=sorted(VALID_CATEGORIES))
    p.add_argument("--scope")
    p.add_argument("--status", choices=["ACTIVE", "DEPRECATED"])

    p = sub.add_parser("show", help="Show template details")
    p.add_argument("project")
    p.add_argument("template_id")

    p = sub.add_parser("update", help="Update templates")
    p.add_argument("project")
    p.add_argument("--data", required=True)

    p = sub.add_parser("instantiate", help="Instantiate template with params")
    p.add_argument("project")
    p.add_argument("template_id")
    p.add_argument("--params", default="{}")

    p = sub.add_parser("contract", help="Print contract spec")
    p.add_argument("name", choices=sorted(CONTRACTS.keys()))

    args = parser.parse_args()

    commands = {
        "add": cmd_add,
        "read": cmd_read,
        "show": cmd_show,
        "update": cmd_update,
        "instantiate": cmd_instantiate,
        "contract": cmd_contract,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
