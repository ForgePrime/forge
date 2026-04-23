---
name: migrate-bq
description: KIEDY: zmieniasz schemat BQ. ALTER TABLE, backfill, weryfikacja. Schema BEFORE code. Nigdy DELETE — soft-delete.
argument-hint: "[migration description]"
allowed-tools: Bash(docker *)
disable-model-invocation: true
---

# BQ Schema Migration — Safe Execution

## Pre-flight

1. What tables are affected? `grep "open_invoice_\|purchased_invoice_" backend/bq_schemas/tables.py`
2. Is this additive (ADD COLUMN) or destructive (DROP, RENAME, TYPE CHANGE)?
3. Additive = safe online. Destructive = needs planning.

## For ADD COLUMN

```python
# Per table:
client.query(f"ALTER TABLE `{ref}` ADD COLUMN {name} {type}").result()
```

BQ type names: `INTEGER` (not INT64), `BOOLEAN` (not BOOL), `STRING`, `DATETIME`, `TIMESTAMP`

## Backfill

```python
client.query(f"UPDATE `{ref}` SET {name} = {default} WHERE {name} IS NULL").result()
```

Cost: ~$5/TB scanned. Estimate table sizes first.

## Verify

```sql
SELECT COUNT(*) FROM table WHERE {column} IS NULL  -- must be 0
```

## Update code

1. `bq_schemas/tables.py` — add column definition (match BQ internal type name!)
2. `ensure_supplier_table()` — add to CREATE TABLE
3. `SUPPLIER_EXTRA_COLUMNS` — if pipeline column, extend + update ALL 4 usage sites
4. Queries — add filter if needed (use COALESCE for transitional)

## Deployment order

```
1. ALTER TABLE (BQ online, no downtime)
2. Backfill
3. Health check (0 NULL)
4. Deploy code with COALESCE
5. Later: switch to strict filter
```

## NEVER

- `DELETE FROM` to "clean up" — use `UPDATE SET is_active = FALSE`
- Deploy code referencing non-existent column — BQ will error
- Assume INT64 = INTEGER — BQ reports `INTEGER` after ALTER TABLE
