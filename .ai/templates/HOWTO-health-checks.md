---
name: health
description: >
  Data consistency and infrastructure health checks per standards.md §11.
  Checks BQ invariants (duplicate versions, NULL is_active), schema drift,
  Firestore indexes, API endpoints, Docker logs. Clear PASS/FAIL thresholds
  with remediation actions. Run after deploy or on schedule.
argument-hint: "[country code, or omit for ALL countries]"
allowed-tools: Bash(docker *) Bash(curl *)
disable-model-invocation: true
user-invocable: true
---

# Health Checks — Data Consistency

Per `.ai/standards.md` §11: health check queries, invariant checks, migration verification.

## Variables

- `{country}` — 2-letter country code from argument (e.g., "PL", "DE", "AU")
- `{sc}` — supplier code prefix used in BQ table names (e.g., "SE_002"). Derived per country from `dataload_schedules` collection.

If no country code provided, run checks for ALL countries sequentially (query `GET /api/buying/countries` for the list).

---

## Checks

### 1. Duplicate active versions — PASS threshold: 0

One supplier+date must have at most 1 active load_version. Duplicates = data corruption.

```sql
SELECT date, COUNT(DISTINCT load_version) as versions
FROM `{project}.{dataset}.open_invoice_{sc}`
WHERE is_active = TRUE AND document_type = 'invoice'
GROUP BY 1 HAVING COUNT(DISTINCT load_version) > 1
```

Run for each supplier table in the country.

**On FAIL:** Data loaded twice without deactivating previous version. Run `/fix "duplicate active versions for {sc}"`. Do NOT deploy until resolved — user will see doubled amounts.

### 2. NULL is_active — PASS threshold: 0

After migration, every row must have `is_active` set. NULLs mean migration is incomplete.

```sql
SELECT COUNT(*) as null_count
FROM `{project}.{dataset}.open_invoice_{sc}`
WHERE is_active IS NULL
```

**On FAIL:** Migration incomplete. Run backfill: `UPDATE ... SET is_active = TRUE WHERE is_active IS NULL`. Do NOT switch from `COALESCE(is_active, TRUE)` to strict `is_active = TRUE` filter until this is 0.

### 3. Schema drift — PASS threshold: 0 warnings

Compare `backend/bq_schemas/tables.py` definitions against actual BQ table schema.

```bash
docker compose exec backend python -c "
from app.modules.maintenance.service import check_schema_drift
import asyncio
result = asyncio.run(check_schema_drift('${country}'))
print(result)
"
```

If `check_schema_drift` does not exist, fall back to manual comparison:
```bash
docker compose exec backend python -c "
from app.bigquery import get_bq_client
client = get_bq_client()
table = client.get_table('${table_ref}')
for f in table.schema: print(f'{f.name}: {f.field_type} ({f.mode})')
"
```

Compare output against `bq_schemas/tables.py` field definitions. Watch for: `INT64` vs `INTEGER`, missing columns, extra columns.

**On FAIL (>0 drift):** Do NOT deploy code that references drifted columns. Fix schema first with `/migrate-bq`.

### 4. Firestore composite indexes — PASS threshold: all READY

Compound queries (WHERE field_a + ORDER BY field_b) require composite indexes. CREATING status = query will fail with FailedPrecondition.

```bash
docker compose exec backend python -c "
from google.cloud.firestore_admin_v1 import FirestoreAdminClient
client = FirestoreAdminClient()
parent = 'projects/${project_id}/databases/(default)/collectionGroups/entries'
for idx in client.list_indexes(request={'parent': parent}):
    state = idx.state.name
    fields = ', '.join(f.field_path for f in idx.fields)
    print(f'{state}: {fields}')
"
```

**On FAIL (CREATING):** Wait 2-5 minutes and recheck. If stuck CREATING >10 min, delete and recreate. Do NOT deploy code that uses compound queries without READY index.

### 5. Timeline sequence gaps — PASS threshold: 0 gaps (WARN if >0)

Gaps in `sequence_number` indicate lost timeline entries. Informational — does not block deploy but indicates data inconsistency.

```bash
docker compose exec backend python -c "
from app.firestore import get_db_sync
db = get_db_sync()
entries = db.collection('operation_timeline').document('${country}').collection('entries').order_by('sequence_number').stream()
prev = 0
gaps = []
for e in entries:
    seq = e.to_dict().get('sequence_number', 0)
    if seq != prev + 1 and prev > 0: gaps.append(f'{prev}→{seq}')
    prev = seq
print(f'Gaps: {len(gaps)}' + (f' — {gaps[:5]}' if gaps else ''))
"
```

**On WARN:** Investigate missing operations. Not a deploy blocker but timeline restore may be incomplete.

### 6. API health endpoint

```bash
curl -s http://localhost:8000/health | jq .
```

**PASS:** `{"status": "ok"}` with HTTP 200.
**On FAIL:** Backend container not running or crashed. Check Docker logs (check #9).

### 7. Timeline endpoint

```bash
curl -s "http://localhost:8000/api/maintenance/timeline?country=${country}&page_size=1" -H "Authorization: Bearer ${token}" | jq '.total_count'
```

**PASS:** HTTP 200 with valid response.
**On FAIL:** Timeline module broken. Check logs for FailedPrecondition (missing index → check #4) or import errors.

### 8. Timeline health-check endpoint

```bash
curl -s "http://localhost:8000/api/maintenance/timeline/health-check/${country}" -H "Authorization: Bearer ${token}" | jq .
```

**PASS:** All sub-checks healthy.
**On FAIL:** Check specific sub-check failures in response.

### 9. Backend Docker logs — PASS threshold: 0 ERROR lines

```bash
docker compose logs backend --tail 30 --no-color 2>/dev/null | grep -i "error\|exception\|traceback" | grep -v "INFO"
```

**PASS:** No ERROR/exception lines.
**On FAIL (new errors):** Investigate stack trace. Common causes: missing import (guard rule H3), missing column (check #3), missing index (check #4).

### 10. Schema drift in startup logs — PASS threshold: 0 warnings

```bash
docker compose logs backend --no-color 2>/dev/null | grep -i "bq_schema_drift\|schema.*warning\|column.*missing"
```

**PASS:** No drift warnings.
**On FAIL:** Same remediation as check #3.

---

## Output

```
HEALTH CHECK: {country} — {timestamp UTC}

[PASS/FAIL] #1 Duplicate active versions: {count} (threshold: 0)
[PASS/FAIL] #2 NULL is_active: {count} (threshold: 0)
[PASS/FAIL] #3 Schema drift: {count} warnings (threshold: 0)
[PASS/FAIL] #4 Firestore indexes: {all READY / N CREATING}
[PASS/WARN] #5 Timeline sequence gaps: {count} (informational)
[PASS/FAIL] #6 API health: {status code}
[PASS/FAIL] #7 Timeline endpoint: {status code}
[PASS/FAIL] #8 Timeline health-check: {status}
[PASS/FAIL] #9 Docker logs: {error count}
[PASS/FAIL] #10 Startup schema drift: {warning count}

VERDICT: HEALTHY / ISSUES FOUND ({N fails, M warns})

{If ISSUES FOUND — list remediation actions per failed check}
```
