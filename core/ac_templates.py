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
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from entity_base import EntityModule, make_cli
from models import AcTemplate
from storage import now_iso

from errors import EntityNotFound, PreconditionError, ValidationError

from _compat import configure_encoding
configure_encoding()


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
                      "verification_method", "status", "source_tasks",
                      "occurrences"],
        "enums": {
            "category": VALID_CATEGORIES,
            "status": {"ACTIVE", "PROPOSED"},
        },
        "types": {
            "parameters": list,
            "scopes": list,
            "tags": list,
            "source_tasks": list,
            "occurrences": int,
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
            "status: ACTIVE (default) or PROPOSED (candidate from /compound, not yet approved)",
            "source_tasks: list of task IDs where this pattern was observed (for PROPOSED templates)",
            "occurrences: how many times this pattern was detected (default 1, incremented on dedup match)",
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
                      "status", "occurrences", "source_tasks"],
        "enums": {
            "category": VALID_CATEGORIES,
            "status": {"ACTIVE", "PROPOSED", "DEPRECATED"},
        },
        "types": {
            "parameters": list,
            "scopes": list,
            "tags": list,
            "source_tasks": list,
            "occurrences": int,
        },
        "invariant_texts": [
            "id: existing template ID (AC-001, etc.)",
            "Only provided fields are updated — omitted fields stay unchanged",
            "status: ACTIVE, PROPOSED, or DEPRECATED",
            "occurrences: set to increment detection count (for PROPOSED templates matched by /compound)",
            "source_tasks: list of task IDs — appended to existing (not replaced)",
        ],
        "example": [
            {"id": "AC-001", "status": "DEPRECATED"},
            {"id": "AC-003", "status": "ACTIVE"},
            {"id": "AC-005", "occurrences": 3, "source_tasks": ["T-010"]},
        ],
    },
}


# -- Helpers --

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


# -- EntityModule subclass --

class AcTemplates(EntityModule):
    entity_type = "ac_templates"
    list_key = "ac_templates"
    id_prefix = "AC"
    contracts = CONTRACTS
    display_name = "AC Templates"
    dedup_keys = ("category", "title")
    model_class = AcTemplate

    def cmd_add(self, args):
        """Create AC templates with parameter validation."""
        items = self._parse_and_validate(args.data, "add")

        # Original requires a list (not single object)
        # _parse_and_validate wraps single in list, but original required array input
        # Keep consistent: _parse_and_validate handles this fine.

        data = self.load(args.project)
        timestamp = now_iso()
        existing = self.existing_dedup_keys(data)

        added = []
        skipped = []
        for item in items:
            category = item["category"].lower().strip()
            key = (category, item["title"].lower().strip())
            if key in existing:
                skipped.append(f"Duplicate: {item['title'][:50]}")
                continue

            # Validate parameters against template placeholders
            parameters = item.get("parameters", [])
            placeholders = _extract_placeholders(item["template"])
            param_errors = _validate_params_definition(parameters, placeholders)
            if param_errors:
                for pe in param_errors:
                    print(f"  WARNING: {pe}", file=sys.stderr)

            ac_id = self.make_id(self.next_num(data))
            status = item.get("status", "ACTIVE")
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
                "status": status,
                "usage_count": 0,
                "occurrences": item.get("occurrences", 1),
                "source_tasks": item.get("source_tasks", []),
                "created_at": timestamp,
                "updated_at": timestamp,
            }

            data[self.list_key].append(template)
            existing.add(key)
            added.append(ac_id)

        self.save(args.project, data)
        self.print_add_summary(args.project, data, added, skipped)

    def apply_filters(self, items: list, args) -> list:
        """Filter by category, scope, status."""
        if getattr(args, "category", None):
            items = [t for t in items if t.get("category") == args.category.lower().strip()]
        if getattr(args, "scope", None):
            scope = args.scope.lower().strip()
            items = [t for t in items if scope in t.get("scopes", [])]
        if getattr(args, "status", None):
            items = [t for t in items if t.get("status") == args.status]
        return items

    def render_list(self, items: list, args):
        """Render AC templates table with occurrences column."""
        print(f"## {self.display_name}: {args.project}")
        filters = []
        if getattr(args, "category", None):
            filters.append(f"category={args.category}")
        if getattr(args, "scope", None):
            filters.append(f"scope={args.scope}")
        if filters:
            print(f"Filter: {', '.join(filters)}")
        print(f"Count: {len(items)}")
        print()

        if not items:
            print("(none)")
            return

        print("| ID | Category | Status | Uses | Occ | Title |")
        print("|----|----------|--------|------|-----|-------|")
        for t in items:
            title = t.get("title", "")[:45]
            occ = t.get("occurrences", 1) if t.get("status") == "PROPOSED" else ""
            print(f"| {t['id']} | {t.get('category', '')} | {t.get('status', '')} "
                  f"| {t.get('usage_count', 0)} | {occ} | {title} |")

    def cmd_update(self, args):
        """Update AC templates with source_tasks append-merge and template validation."""
        updates = self._parse_and_validate(args.data, "update")
        data = self.load(args.project)
        timestamp = now_iso()

        updated = []
        for u in updates:
            t = self.find_by_id(data, u["id"])
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
                         "status", "occurrences"]
            for field in updatable:
                if field in u:
                    t[field] = u[field]

            # source_tasks: append-merge (not replace)
            if "source_tasks" in u:
                existing_st = t.get("source_tasks", [])
                for st in u["source_tasks"]:
                    if st not in existing_st:
                        existing_st.append(st)
                t["source_tasks"] = existing_st

            t["updated_at"] = timestamp
            updated.append(u["id"])

        self.save(args.project, data)

        if updated:
            print(f"Updated: {', '.join(updated)}")
        else:
            print("No templates were updated.")


# -- Module instance and compatibility aliases --

_mod = AcTemplates()

load_or_create = _mod.load
save_json = _mod.save
find_template = _mod.find_by_id
cmd_add = _mod.cmd_add
cmd_read = _mod.cmd_read
cmd_update = _mod.cmd_update


# -- Custom commands (standalone functions) --

def cmd_show(args):
    """Show full details of an AC template."""
    data = _mod.load(args.project)
    t = _mod.find_by_id(data, args.template_id)
    if not t:
        raise EntityNotFound(f"Template '{args.template_id}' not found.")

    print(f"## {t['id']}: {t['title']}")
    status = t.get('status', 'ACTIVE')
    print(f"**Category**: {t['category']} | **Status**: {status} "
          f"| **Uses**: {t.get('usage_count', 0)}")
    if status == "PROPOSED":
        print(f"**Occurrences**: {t.get('occurrences', 1)}")
        if t.get("source_tasks"):
            print(f"**Source Tasks**: {', '.join(t['source_tasks'])}")
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


def cmd_instantiate(args):
    """Instantiate a template with concrete parameters."""
    data = _mod.load(args.project)
    t = _mod.find_by_id(data, args.template_id)
    if not t:
        raise EntityNotFound(f"Template '{args.template_id}' not found.")

    if t.get("status") == "PROPOSED":
        raise PreconditionError(f"Template '{args.template_id}' is PROPOSED — approve it first "
              f"(update status to ACTIVE).")

    if t.get("status") == "DEPRECATED":
        print(f"WARNING: Template '{args.template_id}' is DEPRECATED.", file=sys.stderr)

    # Parse params
    try:
        params = json.loads(args.params) if args.params else {}
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON params: {e}")

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
        raise ValidationError(f"Missing required parameters: {', '.join(missing)}")

    # Render template (SafeDict leaves unresolved {placeholders} as-is)
    template_str = t.get("template", "")

    class _SafeDict(dict):
        def __missing__(self, key):
            return "{" + key + "}"

    try:
        text = template_str.format_map(_SafeDict({k: str(v) for k, v in resolved.items()}))
    except (ValueError, IndexError) as e:
        raise ValidationError(f"Template rendering failed: {e}")

    # Increment usage count
    t["usage_count"] = t.get("usage_count", 0) + 1
    t["updated_at"] = now_iso()
    _mod.save(args.project, data)

    # Output structured AC
    result = {
        "text": text,
        "from_template": args.template_id,
        "params": resolved,
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))


# -- CLI --

def _setup_extra_parsers(sub):
    """Add filter args to read parser and custom subparsers for show/instantiate."""
    # Add filter args to the read parser created by make_cli
    read_parser = sub.choices["read"]
    if read_parser:
        read_parser.add_argument("--category", choices=sorted(VALID_CATEGORIES))
        read_parser.add_argument("--scope")
        read_parser.add_argument("--status", choices=["ACTIVE", "PROPOSED", "DEPRECATED"])

    p = sub.add_parser("show", help="Show template details")
    p.add_argument("project")
    p.add_argument("template_id")

    p = sub.add_parser("instantiate", help="Instantiate template with params")
    p.add_argument("project")
    p.add_argument("template_id")
    p.add_argument("--params", default="{}")


def main():
    make_cli(
        _mod,
        extra_commands={
            "show": cmd_show,
            "instantiate": cmd_instantiate,
        },
        setup_extra_parsers=_setup_extra_parsers,
        description="Forge AC Templates — reusable acceptance criteria",
    )


if __name__ == "__main__":
    main()
