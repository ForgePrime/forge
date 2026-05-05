# `migrations_drafts/` — pre-ratification migration sketches

**Status:** authoring zone for SQL migration deltas that depend on a
PROPOSED but not yet RATIFIED ADR. Files here are **inert documentation**
until their gating ADR ratifies.

## Why this directory exists

`platform/alembic/versions/` is the executable migration chain — files
landing there are auto-discovered by `alembic upgrade`. Authoring a Python
revision file there before the corresponding ADR ratifies risks:

- accidental execution by a developer running `alembic upgrade head`,
- a CI hook that auto-applies migrations on a fresh DB,
- code reviewers assuming the migration is approved because it lives in
  the canonical path.

This directory is **outside that path**. Files here are `.sql` (or `.md`),
not `.py` revision modules. Alembic does not see them.

## Lifecycle

```
DRAFT (here)
   │
   │  ADR ratifies
   ▼
PORTED to alembic/versions/<rev>.py
   │
   │  alembic upgrade head
   ▼
APPLIED on production
```

When the gating ADR ratifies:

1. Author the proper Alembic revision file in `platform/alembic/versions/`
   that runs the SQL from the draft (either inline as `op.execute(...)`
   or as `op.create_table(...)` calls).
2. Add the verification queries (§101 of each draft) to a
   `tests/migrations/` test that asserts the post-up state.
3. Move (don't copy) the draft into a sibling `migrations_drafts/applied/`
   directory or delete it after the Alembic revision lands.
4. Reference the Alembic revision hash in the gating ADR's "Decision
   applied via" field.

## Pre-flight checklist (before porting any draft to versions/)

- [ ] Gating ADR status = RATIFIED.
- [ ] Distinct-actor reviewer named (CONTRACT §B.8).
- [ ] Database backup taken: `pg_dump forge_platform > backup_pre_<name>.sql`.
- [ ] Verification queries (§101 of the draft) pass on a clean clone.
- [ ] `down()` equivalent (§99 of the draft) runs to completion on a
      copy of the up-applied DB.
- [ ] `tests/migrations/test_<name>.py` exists and asserts post-state.

## Current drafts

| File | Gating ADR | Status |
|---|---|---|
| `2026_04_26_phase1_redesign.sql` | ADR-028 | DRAFT — ADR-028 PROPOSED |

## Naming convention

`YYYY_MM_DD_<short_name>.sql` — date is **authoring** date, not application
date (application date may be days/weeks later after ratification).
