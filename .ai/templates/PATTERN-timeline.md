---
name: add-timeline
description: WHEN: adding an endpoint that modifies data. Adds a timeline write point (LOAD/BUY/OVERRIDE/CONFIG).
argument-hint: "[endpoint path and operation type]"
disable-model-invocation: true
---

# Instrument Timeline Write Point

Per `.ai/standards.md` §8: every data-modifying operation MUST have: operation_id, sequence_number, before/after value, idempotency, retry strategy.

## For DATA operations (LOAD, BUY, OVERRIDE)

### BUY
```python
from app.modules.timeline.service import record_buy
from app.modules.timeline.types import BuyDetailsDict

await record_buy(db, country, user, details=BuyDetailsDict(
    execution_id=..., sales_type=..., currency=...,
    rows_per_supplier={...}, depends_on_loads=[],
))
```

### OVERRIDE (with snapshot)
1. BEFORE save: query current state from override table (batch query)
2. Write before-snapshot to `override_snapshot_{country}` BQ table
3. Execute save_overrides
4. Write after-snapshot
5. Record timeline entry with change_id

### LOAD (pipeline — SYNC Firestore, no `app.*` imports!)
- Use hardcoded collection names ("operation_timeline", "entries")
- Use `@firestore.transactional` for sequence counter
- Set `user: "SCHEDULER"` (not supplier_code)

## For CONFIG operations

Pattern (same for all 14 types):
```python
from app.modules.timeline.service import capture_config_before, record_config_change_simple

# 1. BEFORE change
before_value, existed = await capture_config_before(db, collection, doc_id)

# 2. Execute change
await original_operation(...)

# 3. Record timeline
await record_config_change_simple(
    db, country, user.email,
    config_type="CREDIT_LIMIT",  # or START_DATE, CUSTOMER_EXCLUSION, etc.
    collection=collection, document_id=doc_id,
    before_value=before_value, after_value=after_value,
    document_existed_before=existed,
    entity_label=f"Credit limit {country}/{currency}: {old} → {new}",
)
```

## CRITICAL: Non-blocking

ALL timeline writes MUST be in try/except with `logger.warning` (NOT `pass`):
```python
try:
    await record_...()
except Exception as tl_exc:
    logger.warning("timeline_write_failed", error=str(tl_exc))
```

**Note:** This pattern is COMPLIANT with guard rule H4 ("no except pass"). The difference: `logger.warning(...)` logs the failure for debugging. `pass` silently swallows it — which H4 forbids.

Timeline failure NEVER blocks the main operation — but it MUST be logged.
