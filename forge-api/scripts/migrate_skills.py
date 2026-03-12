#!/usr/bin/env python3
"""Migrate skills from monolithic skills.json to per-skill directories.

Usage:
    python scripts/migrate_skills.py --base-dir forge_output/_global
    python scripts/migrate_skills.py --base-dir forge_output/_global --dry-run

Reads _global/skills.json, creates _global/skills/{name}/ directories with
_config.json, SKILL.md, and bundled files.  Backs up skills.json to
skills.json.bak before modifying anything.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def slugify(name: str) -> str:
    """Convert a skill name to a valid slug."""
    import re
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug or "unnamed-skill"


def migrate_skill(skill: dict, skills_dir: Path, dry_run: bool) -> str:
    """Migrate a single skill entry to a directory.  Returns the slug."""

    name = skill.get("name", "")
    slug = slugify(name)
    skill_dir = skills_dir / slug

    # Determine old category -> new categories[]
    old_category = skill.get("category", "")
    categories = [old_category] if old_category else []

    # Build _config.json
    config = {
        "categories": categories,
        "tags": skill.get("tags", []),
        "status": skill.get("status", "DRAFT"),
        "scopes": skill.get("scopes", []),
        "evals_json": skill.get("evals_json", []),
        "teslint_config": skill.get("teslint_config"),
        "sync": False,
        "promoted_with_warnings": skill.get("promoted_with_warnings", False),
        "promotion_history": skill.get("promotion_history", []),
        "usage_count": skill.get("usage_count", 0),
        "created_by": skill.get("created_by"),
        "created_at": skill.get("created_at", datetime.now(timezone.utc).isoformat()),
        "updated_at": skill.get("updated_at", datetime.now(timezone.utc).isoformat()),
    }

    # SKILL.md content
    skill_md = skill.get("skill_md_content") or ""

    # Bundled files from resources.files
    resources = skill.get("resources") or {}
    bundled_files = resources.get("files") or []

    if dry_run:
        print(f"  [DRY-RUN] Would create: {skill_dir}/")
        print(f"            _config.json: categories={categories}, status={config['status']}")
        print(f"            SKILL.md: {len(skill_md)} chars")
        for f in bundled_files:
            print(f"            {f['path']}: {len(f.get('content', ''))} chars")
        return slug

    # Create directory
    skill_dir.mkdir(parents=True, exist_ok=True)

    # Write _config.json
    config_path = skill_dir / "_config.json"
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")

    # Write SKILL.md
    md_path = skill_dir / "SKILL.md"
    md_path.write_text(skill_md, encoding="utf-8")

    # Write bundled files
    for f in bundled_files:
        fpath = skill_dir / f["path"]
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.write_text(f.get("content", ""), encoding="utf-8")

    return slug


def build_index(skills_dir: Path, entries: list[dict]) -> None:
    """Write _index.json from migrated entries."""
    index_path = skills_dir / "_index.json"
    index_data = {"entries": entries, "updated_at": datetime.now(timezone.utc).isoformat()}
    index_path.write_text(json.dumps(index_data, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate skills.json to per-skill directories")
    parser.add_argument("--base-dir", required=True, help="Path to _global directory (e.g. forge_output/_global)")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be done without writing")
    args = parser.parse_args()

    base_dir = Path(args.base_dir).resolve()
    skills_json_path = base_dir / "skills.json"

    if not skills_json_path.exists():
        print(f"ERROR: {skills_json_path} not found.")
        sys.exit(1)

    # Read source
    data = json.loads(skills_json_path.read_text(encoding="utf-8"))
    skills_list = data.get("skills", [])
    print(f"Found {len(skills_list)} skills in {skills_json_path}")

    if not skills_list:
        print("Nothing to migrate.")
        return

    # Backup
    backup_path = skills_json_path.with_suffix(".json.bak")
    if not args.dry_run:
        shutil.copy2(skills_json_path, backup_path)
        print(f"Backup created: {backup_path}")
    else:
        print(f"[DRY-RUN] Would backup to: {backup_path}")

    # Migrate
    skills_dir = base_dir / "skills"
    if not args.dry_run:
        skills_dir.mkdir(exist_ok=True)

    index_entries: list[dict] = []
    slugs_seen: set[str] = set()

    for i, skill in enumerate(skills_list):
        old_id = skill.get("id", f"?-{i}")
        name = skill.get("name", "unnamed")
        print(f"\n[{i+1}/{len(skills_list)}] {old_id} -> {name}")

        slug = migrate_skill(skill, skills_dir, dry_run=args.dry_run)

        # Handle duplicate slugs
        if slug in slugs_seen:
            dedup = f"{slug}-{i}"
            print(f"  WARNING: duplicate slug '{slug}', using '{dedup}'")
            if not args.dry_run:
                old_path = skills_dir / slug
                new_path = skills_dir / dedup
                if old_path != new_path:
                    # Re-migrate with dedup name
                    shutil.rmtree(skills_dir / slug, ignore_errors=True)
                slug = dedup
                migrate_skill(skill, skills_dir, dry_run=False)

        slugs_seen.add(slug)

        # Build index entry
        old_category = skill.get("category", "")
        categories = [old_category] if old_category else []
        index_entries.append({
            "name": slug,
            "description": skill.get("description", ""),
            "status": skill.get("status", "DRAFT"),
            "categories": categories,
            "tags": skill.get("tags", []),
            "sync": False,
            "updated_at": skill.get("updated_at", datetime.now(timezone.utc).isoformat()),
        })

    # Write _index.json
    if not args.dry_run:
        build_index(skills_dir, index_entries)
        print(f"\n_index.json written with {len(index_entries)} entries.")

    print(f"\nMigration {'preview' if args.dry_run else 'complete'}. {len(skills_list)} skills processed.")
    if not args.dry_run:
        print(f"Skills directory: {skills_dir}")
        print(f"Original backup: {backup_path}")


if __name__ == "__main__":
    main()
