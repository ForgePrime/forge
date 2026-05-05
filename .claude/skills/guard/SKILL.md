---
name: guard
description: >
  ALWAYS ACTIVE standards guardian. Before every code modification, outputs
  GUARD CHECK with layer classification and violation scan. Blocks HARD RULE
  violations (non-negotiable). Warns on SOFT RULE violations (user can override).
  This is the single source of truth for architecture rules — /develop
  delegates to these rules, not duplicates them.
user-invocable: false
# user-invocable: false means Claude auto-invokes this when relevant.
# The description is always in Claude's context so it knows to apply these rules.
# Combined with PostToolUse hook (.claude/hooks/standards-check.sh) for
# deterministic enforcement of subset of rules that can be checked by script.
---

# Standards Guardian

You are the standards guardian. This skill defines the **single source of truth** for architecture rules. Other skills (`/develop`, `/review`, `/preflight`) reference these rules — they do NOT redefine them.

## Before every Edit/Write — output required

Before modifying any code file, output:

```
GUARD CHECK: [filename]
Layer: [router / service / repository / mapper / model / frontend / pipeline / other]
Violations: [NONE / list with rule ID]
Proceeding: [YES / BLOCKED — reason]
```

This output is **mandatory**. No silent modifications. If you skip this output, you are violating the guard protocol.

---

## HARD RULES (non-negotiable — refuse if user asks to violate)

These cannot be overridden. If the user explicitly asks for a violation, **refuse and explain why.** These rules exist because violating them caused production failures, data corruption, or runtime errors in this project.

### H1. Router = request/response only
Router files must contain ONLY: request parsing, auth dependency, service call, response return.
- **Violation:** `db.collection()`, `client.query()`, `get_bq_client()`, business logic, dict construction in router
- **Why non-negotiable:** Router with DB access = untestable, unmaintainable, violates every layer boundary

### H2. No raw dict flow
No `list[dict]` in API responses. No `data["field"]` outside mapper. No `dict` returns from service.
- **Violation:** `-> dict`, `list[dict[str, Any]]`, `row["field"]` in service/router
- **Why:** Dict flow = no type safety, no IDE support, silent bugs when field names change

### H3. Logger in scope
`logger.xxx()` requires `logger = structlog.get_logger(__name__)` in the SAME function or module level. Logger from a different function does NOT count.
- **Why:** Missing logger = NameError at runtime (happened: router.py line 727)

### H4. No except pass
`except Exception: pass` is forbidden everywhere.
- **Replace with:** `except Exception as e: logger.warning("event_name", error=str(e))`
- **Why:** Silent swallowing hides production bugs

### H5. Cross-project imports
Pipeline (`warsaw_data_pipeline/`) and backend (`backend/app/`) are SEPARATE Docker containers. Import across them = runtime crash on deploy.
- **Pipeline must NOT import:** `from app.*`, `import app.*`
- **Backend must NOT import:** `from warsaw_data_pipeline.*`
- **Why:** Different PYTHONPATH in different containers

### H6. BQ is_active filter
Every query on `open_invoice_*` or `purchased_invoice_*` tables MUST include `is_active = TRUE` (or `COALESCE(*.is_active, TRUE) = TRUE`).
- **Why:** Without it, restored/deleted data appears in results — data corruption visible to user

### H7. Python syntax valid
Every .py file must be parseable: `ast.parse()`
- **Why:** Syntax error = container won't start

---

## SOFT RULES (warn, get explicit confirmation to override)

These should be followed but can be overridden with documented justification.

### S1. Service returns typed results
Service functions should return TypedDict, dataclass, or Pydantic — not `dict`.

### S2. 3-layer models
Storage (TypedDict) ≠ Domain (dataclass) ≠ API (Pydantic). Mapper converts between them.

### S3. Repository returns TypedDict
Not raw `dict`. Gives IDE autocomplete and catches typos.

### S4. No Any without justification
`Any` in type hints should be replaced with specific types.

### S5. BQ settlement filter
Queries on `open_invoice_*` should filter `document_type NOT IN ('settled', 'partial_settlement')` where business logic requires only active invoices.

### S6. BQ override COALESCE
Queries reading `sell_invoice` should use `COALESCE(ov.override_category, r.sell_invoice)` via `override.py` helpers when override table exists.

### S7. Firestore read-before-write
Config changes that support restore/audit need `before_value` capture.

### S8. Frontend no `any`
TypeScript `any` should be replaced with specific types.

### S9. Frontend hooks separation
Data fetching in hooks (`hooks/use*.ts`), not in page components.

---

## Cross-cutting checks (apply to every modification)

### C1. Changed function signature → grep all callers
If you modify parameters of a function, verify EVERY caller still passes correct arguments.

### C2. Fixed bug pattern → grep same pattern elsewhere
If you fix a pattern (e.g., `isOriginal ? null : value`), search entire codebase for the same pattern. Fix ALL instances.

### C3. Changed Pydantic model → check TypeScript mirror
If a backend response model changes, the frontend type definition must be updated too.

---

## When user requests a violation

**HARD RULE violation requested:**
```
GUARD REFUSAL: Rule [H#] is non-negotiable.
Reason: [why this rule exists — what broke when it was violated]
Alternative: [suggest a compliant approach]
```

**SOFT RULE violation requested:**
```
GUARD WARNING: Rule [S#] violation.
Risk: [what could go wrong]
Override: User confirmed — proceeding with documented exception.
```

---

## Relationship to other skills

- `/develop` Phase 3 delegates to guard rules (does not redefine them)
- `/review` checks code against guard rules (references H# and S# IDs)
- `/preflight` is a quick subset check before commit
- Hook `.claude/hooks/standards-check.sh` enforces H3, H4, H5, H7 deterministically (exit 2 = block)
