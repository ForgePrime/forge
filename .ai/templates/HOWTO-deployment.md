---
name: plan-deploy
description: >
  Deployment planning with hard gates. Pre-conditions check, phased execution
  (schema→backend→pipeline→frontend), backfill strategy by table size,
  Go/No-Go with blocking criteria, partial rollback scenarios, health
  verification via /health skill. Schema BEFORE code — never reverse.
argument-hint: "[what changes are being deployed]"
disable-model-invocation: true
user-invocable: true
---

# Plan Deployment — Standard-Compliant

Per `.ai/standards.md` §4.2 (BQ tables), §8 (consistency and reversibility).

**RULE: Schema BEFORE code. Never the other way around.**

## Changes

$ARGUMENTS

---

## Step 0: Pre-conditions

Before starting ANY deployment:

| Check | How | Blocking? |
|-------|-----|-----------|
| Branch merged to deploy branch? | `git log --oneline main..HEAD` | YES |
| Tests green? | CI/CD pipeline status or `docker compose exec backend pytest` | YES |
| No other deployment in progress? | Check with team / lock status | YES |
| Changes inventoried? | Proceed to Krok 1 | YES |

**Any NO → do NOT start deployment.**

---

## Step 1: Inventory changes

```!
git diff --stat main...HEAD 2>/dev/null || git diff --stat
```

Classify changes:

| Category | Files changed? | Deployment impact |
|----------|---------------|-------------------|
| BQ schema (bq_schemas/, ALTER TABLE) | YES/NO | Phase 1 required |
| Firestore (new collections, indexes) | YES/NO | Phase 1 required |
| Backend Python (modules/, schemas/) | YES/NO | Phase 2 required |
| Pipeline (warsaw_data_pipeline/) | YES/NO | Phase 3 required |
| Frontend (frontend/src/) | YES/NO | Phase 4 required |

---

## Step 2: Deployment phases

### Phase 1: INFRASTRUCTURE (no code deploy yet)

```
□ ALTER TABLE ADD COLUMN (per table)
□ Backfill defaults
□ Health check: NULL count = 0
□ Firestore composite indexes (create + verify READY)
```

**Backfill strategy by table size:**

| Table size | Strategy | Cost estimate |
|-----------|----------|---------------|
| < 1M rows | `UPDATE SET column = default WHERE column IS NULL` directly | < $1 |
| 1M-100M rows | Batch UPDATE with LIMIT + loop, or `INSERT INTO new_table SELECT` + swap | $1-50 |
| > 100M rows | Create new table with schema, INSERT-SELECT, swap reference | Dry-run first: `bq query --dry_run` |

Always verify after backfill: `SELECT COUNT(*) WHERE column IS NULL` = 0.

### Phase 2: BACKEND DEPLOY

```
□ Build Docker image
□ Deploy backend container
□ Verify: curl /health → {"status": "ok"}
□ Verify: docker compose logs backend --tail 20 → zero ERROR
□ Verify: schema drift → zero warnings (grep bq_schema_drift in logs)
```

### Phase 3: PIPELINE (if changed)

Pipeline is a SEPARATE container — highest cross-project import risk.

```
□ Restart pipeline container
□ Verify: startup logs → no ImportError, no ModuleNotFoundError
□ Verify: cross-project imports → run /check-imports
□ Test: trigger manual pipeline run for one supplier
□ Verify: BQ table updated correctly (row count, is_active values)
```

### Phase 4: FRONTEND (if changed)

```
□ Build frontend
□ Deploy frontend container
□ Verify: page loads at localhost:3000
□ Verify: browser console → zero errors
□ Verify: critical pages render data (manual spot check)
```

### Phase 5: VERIFICATION

```
□ Run: /health {country} → all PASS (links to health skill for systematic checks)
□ Test business flow: LOAD → BUY → manual-buy UI displays correctly
□ Monitor logs for 15 minutes → no new errors
□ Notify team (see format below)
```

---

## Step 3: Rollback plan

**Per change type:**

| Change | Rollback | Notes |
|--------|----------|-------|
| BQ ADD COLUMN | `ALTER TABLE DROP COLUMN` (safe if no data depends on it) | |
| BQ backfill | No rollback needed — column had NULLs before, now has defaults | |
| Backend code | `git revert {commit}` + rebuild + redeploy | |
| Pipeline code | `git revert {commit}` + restart container | |
| Frontend code | `git revert {commit}` + rebuild | |
| Firestore index | Delete index (safe, may slow queries temporarily) | |

**HARD RULE: NEVER `DELETE FROM` BQ — soft-delete only (`UPDATE SET is_active = FALSE`).**

### Partial rollback scenarios

| Scenario | Action |
|----------|--------|
| Phase 1 OK, Phase 2 FAIL | Revert code only, keep schema (with COALESCE NULL tolerance in code). Schema change is forward-compatible. |
| Phase 1-2 OK, Phase 3 FAIL | Rollback pipeline only. Backend stays — it doesn't depend on pipeline. |
| Phase 1-3 OK, Phase 4 FAIL | Rollback frontend only. Backend API still serves old data shape (if backward-compatible). |

---

## Step 4: Go/No-Go criteria

| Check | Required | Status |
|-------|----------|--------|
| Schema migration completed | YES | □ |
| Backfill verified (0 NULL) | YES | □ |
| Firestore indexes READY | YES | □ |
| Backend health OK | YES | □ |
| Zero ERROR in logs | YES | □ |
| Schema drift zero | YES | □ |
| Critical endpoints respond | YES | □ |
| Cross-project imports clean (if pipeline) | YES | □ |
| Rollback plan defined per phase | YES | □ |

**If ANY = NO → do NOT deploy. Fix first.**

---

## Step 5: Post-deployment notification

```
Deploy completed: {changes summary}
Time: {timestamp UTC}
Environment: {local / sandbox / production}
Status: {HEALTHY — all /health checks PASS / ISSUES: {list}}
Rollback: {ready / partial — {details}}
```

---

## Output

```
DEPLOYMENT PLAN: {changes}
PHASES: {N active of 5}
PRE-CONDITIONS: {all met / BLOCKED by: ...}
ROLLBACK: {defined per phase / UNDEFINED — BLOCKING}
GO/NO-GO: {all checks pass / BLOCKED by: ...}
```
