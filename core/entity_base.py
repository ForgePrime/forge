"""Base infrastructure for Forge entity modules.

Eliminates duplicated boilerplate across entity modules by providing:
- Common storage operations (load/save with auto-storage)
- ID generation (PREFIX-NNN pattern)
- Deduplication
- Standard CRUD command implementations
- CLI dispatch helper

Subclasses override only what differs: build_entity(), apply_filters(),
render_list(), render_detail(), apply_update().
"""

import argparse
import json
import sys

from _compat import configure_encoding
from contracts import render_contract, validate_contract
from errors import ForgeError, ValidationError, EntityNotFound
from storage import JSONFileStorage, load_json_data, now_iso

configure_encoding()


class EntityModule:
    """Base class providing standard CRUD operations for entity modules.

    Subclass contract:
        entity_type (str):   Storage key, e.g. "guidelines"
        list_key (str):      JSON wrapper key, e.g. "guidelines"
        id_prefix (str):     ID prefix, e.g. "G"
        contracts (dict):    CONTRACTS dict with "add", "update", etc.
        display_name (str):  Human name, e.g. "Guidelines"
        dedup_keys (tuple):  Fields for dedup, e.g. ("scope", "title"), or ()
    """

    entity_type: str = ""
    list_key: str = ""
    id_prefix: str = ""
    contracts: dict = {}
    display_name: str = ""
    dedup_keys: tuple = ()
    model_class = None  # Set to dataclass (e.g. Guideline) for typed find_model()

    def __init__(self, storage=None):
        self._storage = storage
        if not self.display_name:
            self.display_name = self.entity_type.replace("_", " ").title()

    @property
    def storage(self) -> JSONFileStorage:
        if self._storage is None:
            self._storage = JSONFileStorage()
        return self._storage

    # -- Storage helpers --

    def load(self, project: str) -> dict:
        return self.storage.load_data(project, self.entity_type)

    def save(self, project: str, data: dict):
        self.storage.save_data(project, self.entity_type, data)

    def items(self, data: dict) -> list:
        return data.get(self.list_key, [])

    def find_by_id(self, data: dict, entity_id: str):
        for item in self.items(data):
            if item.get("id") == entity_id:
                return item
        return None

    def find_model(self, data: dict, entity_id: str):
        """Find by ID and return as model instance (read-only). Requires model_class."""
        item = self.find_by_id(data, entity_id)
        if item is not None and self.model_class is not None:
            return self.model_class.from_dict(item)
        return item

    # -- ID generation --

    def next_num(self, data: dict) -> int:
        prefix = self.id_prefix + "-"
        nums = [
            int(item["id"].split("-")[1])
            for item in self.items(data)
            if item.get("id", "").startswith(prefix)
        ]
        return max(nums, default=0) + 1

    def make_id(self, n: int) -> str:
        return f"{self.id_prefix}-{n:03d}"

    # -- Dedup --

    def dedup_key(self, item: dict):
        if not self.dedup_keys:
            return None
        return tuple(
            item.get(k, "").lower().strip() for k in self.dedup_keys
        )

    def existing_dedup_keys(self, data: dict) -> set:
        if not self.dedup_keys:
            return set()
        return {self.dedup_key(item) for item in self.items(data)}

    # -- Standard commands --

    def cmd_add(self, args):
        """Parse, validate, dedup, build entities, save."""
        items = self._parse_and_validate(args.data, "add")
        data = self.load(args.project)
        timestamp = now_iso()
        next_n = self.next_num(data)
        existing = self.existing_dedup_keys(data)

        added, skipped = [], []
        for item in items:
            dk = self.dedup_key(item)
            if dk and dk in existing:
                skipped.append(item.get("title", item.get("name", "?"))[:50])
                continue

            entity = self.build_entity(item, self.make_id(next_n), timestamp, args)
            data[self.list_key].append(entity)
            if dk:
                existing.add(dk)
            added.append(entity["id"])
            next_n += 1

        self.save(args.project, data)
        self.print_add_summary(args.project, data, added, skipped)

    def build_entity(self, input_item: dict, entity_id: str,
                     timestamp: str, args) -> dict:
        """Override to construct entity dict from input. MUST be implemented."""
        raise NotImplementedError

    def print_add_summary(self, project: str, data: dict,
                          added: list, skipped: list):
        """Print standard add summary. Override for custom output."""
        print(f"{self.display_name} saved: {project}")
        if added:
            print(f"  Added: {len(added)} ({', '.join(added)})")
        if skipped:
            print(f"  Skipped (duplicate): {len(skipped)}")
        print(f"  Total: {len(self.items(data))}")

    def cmd_read(self, args):
        """Load, filter, sort, render."""
        if not self.storage.exists(args.project, self.entity_type):
            print(f"No {self.display_name.lower()} for '{args.project}' yet.")
            return

        data = self.load(args.project)
        items = self.items(data)
        items = self.apply_filters(items, args)
        items.sort(key=lambda x: x.get("id", ""))

        self.render_list(items, args)

    def apply_filters(self, items: list, args) -> list:
        """Override to add entity-specific filters."""
        return items

    def render_list(self, items: list, args):
        """Override to customize list rendering."""
        project = args.project
        print(f"## {self.display_name}: {project}")
        print(f"Count: {len(items)}")
        print()
        if not items:
            print("(none)")

    def cmd_update(self, args):
        """Parse, validate, find by ID, apply updates, save."""
        updates = self._parse_and_validate(args.data, "update")
        data = self.load(args.project)
        timestamp = now_iso()

        updated = []
        for u in updates:
            item = self.find_by_id(data, u["id"])
            if not item:
                print(f"  WARNING: {u['id']} not found, skipping", file=sys.stderr)
                continue

            if self.apply_update(item, u, timestamp) is not False:
                updated.append(u["id"])

        self.save(args.project, data)

        if updated:
            print(f"Updated: {', '.join(updated)}")
        else:
            print(f"No {self.display_name.lower()} were updated.")

    def apply_update(self, item: dict, update: dict, timestamp: str):
        """Apply update fields to item. Override for custom logic.
        Return False to skip this update (e.g. invalid transition)."""
        for key, value in update.items():
            if key != "id":
                item[key] = value
        item["updated"] = timestamp

    def cmd_contract(self, args):
        """Print contract spec."""
        name = getattr(args, "name", None)
        if name is None:
            name = "add"
        if name not in self.contracts:
            raise ValidationError(
                f"Unknown contract '{name}'. "
                f"Available: {', '.join(sorted(self.contracts.keys()))}")
        print(render_contract(name, self.contracts[name]))

    # -- Internal helpers --

    def _parse_and_validate(self, data_str: str, contract_name: str) -> list:
        """Parse JSON string and validate against named contract."""
        try:
            items = load_json_data(data_str)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON: {e}")

        if not isinstance(items, list):
            items = [items]

        contract = self.contracts.get(contract_name)
        if contract:
            errors = validate_contract(contract, items)
            if errors:
                detail = "\n  ".join(errors[:10])
                raise ValidationError(f"{len(errors)} validation issues:\n  {detail}")

        return items


def make_cli(module: EntityModule, extra_commands: dict = None,
             setup_extra_parsers=None, description: str = ""):
    """Create standard argparse CLI for an entity module.

    Args:
        module: EntityModule instance
        extra_commands: dict of {name: handler_fn} for module-specific commands
        setup_extra_parsers: fn(subparsers) to add custom subparser arguments
        description: argparse description
    """
    parser = argparse.ArgumentParser(
        description=description or f"Forge {module.display_name}"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # Standard commands — only add if contract exists
    if "add" in module.contracts:
        p = sub.add_parser("add", help=f"Add {module.display_name.lower()}")
        p.add_argument("project")
        p.add_argument("--data", required=True)

    if "update" in module.contracts:
        p = sub.add_parser("update", help=f"Update {module.display_name.lower()}")
        p.add_argument("project")
        p.add_argument("--data", required=True)

    # read is always available
    p = sub.add_parser("read", help=f"Read {module.display_name.lower()}")
    p.add_argument("project")

    # contract is always available
    if len(module.contracts) > 1:
        p = sub.add_parser("contract", help="Print contract spec")
        p.add_argument("name", choices=sorted(module.contracts.keys()))
        p.add_argument("_extra", nargs="*", help=argparse.SUPPRESS)
    else:
        p = sub.add_parser("contract", help="Print contract spec")
        p.add_argument("_extra", nargs="*", help=argparse.SUPPRESS)

    # Let the module add custom parsers
    if setup_extra_parsers:
        setup_extra_parsers(sub)

    args = parser.parse_args()

    # Build command map
    commands = {
        "add": module.cmd_add,
        "read": module.cmd_read,
        "update": module.cmd_update,
        "contract": module.cmd_contract,
    }
    if extra_commands:
        commands.update(extra_commands)

    handler = commands.get(args.command)
    if handler:
        try:
            handler(args)
        except ForgeError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(e.exit_code)
    else:
        parser.print_help()
