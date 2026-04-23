---
name: new-contract
description: >
  Define data contracts for a new entity — Storage (TypedDict), Domain, API
  (Pydantic). Step-by-step: check existing contracts, align on source of truth,
  define each layer, add invariants+validators, generate files, verify with
  /check-types. Contract-first — schema before implementation.
argument-hint: "[entity or feature name]"
disable-model-invocation: true
user-invocable: true
---

# Define Data Contracts — Contract-First

Per `.ai/standards.md` §6: Storage ≠ Domain ≠ API. One definition per business entity. Computed fields instead of duplication.

Define contracts BEFORE implementation — schema, types, nullability, edge cases defined before code.

## Entity

$ARGUMENTS

---

## Step 1 — Check if similar contract exists

Before defining anything new, search:

```bash
# Existing TypedDicts
grep -rn "class.*TypedDict" backend/app/modules/ backend/app/schemas/

# Existing Pydantic response models
grep -rn "class.*Response(BaseModel)\|class.*Request(BaseModel)" backend/app/

# Existing types with similar name
grep -rn "{entity_name}" backend/app/modules/ --include="*.py" -l
```

If a similar contract already exists (e.g., `InvoiceDetailResponse` when you need `InvoiceResponse`): **extend or reuse it** — don't create a duplicate.

---

## Step 2 — Align on source and consumers

Before defining layers, answer:

| Question | Answer |
|----------|--------|
| What is the source of truth? | BQ table / Firestore collection / external API / user input |
| Read/write ratio? | Read-heavy (optimize for query) / Write-heavy (optimize for insert) |
| Who consumes this contract? | Internal service only / API response to frontend / Both |
| Existing pattern to follow? | Which module's contract is closest in shape? |

If any answer is UNKNOWN → ask user before proceeding.

---

## Step 3 — Define Storage Model

This is 1:1 with what's in the database. Only repository touches this layer.

### For BQ tables:

```python
# types.py — Storage model
class {Entity}Row(TypedDict):
    # Map BQ columns exactly. Use this type mapping:
    # BQ STRING  → str
    # BQ INTEGER → int
    # BQ FLOAT   → float
    # BQ BOOLEAN → bool
    # BQ TIMESTAMP/DATETIME → str (ISO format from BQ)
    # BQ NULLABLE → field: str | None
    invoice_id: str
    amount: float
    sell_invoice: str
    is_active: bool  # technical column — always include for versioned tables
    load_version: int  # technical column
```

Check actual BQ schema if unsure:
```bash
docker compose exec backend python -c "
from app.bigquery import get_bq_client
t = get_bq_client().get_table('{table_ref}')
for f in t.schema: print(f'{f.name}: {f.field_type} ({f.mode})')
"
```

### For Firestore documents:

```python
class {Entity}Doc(TypedDict):
    # Document fields — match Firestore document shape
    # Document ID pattern: deterministic (sha256[:24]) or semantic (country_code)
    # Index requirements: list compound queries this doc participates in
    field: str
```

State: document ID strategy (auto-generated / deterministic / semantic), index requirements, TTL policy if applicable.

---

## Step 4 — Define API Model (Pydantic)

What the frontend receives. This is NOT the storage model — it may rename fields, compute derived values, hide internal fields.

```python
# models.py — API model
class {Entity}Response(BaseModel):
    # Only fields the frontend needs
    # Rename if business term differs from storage (e.g., sell_invoice → category)
    invoice_id: str
    amount: float
    category: str  # mapped from sell_invoice by mapper

    # Fields with defaults are ALWAYS present (not optional in TypeScript)
    is_eligible: bool = True

    # Optional fields may be absent from response
    reason: str | None = None

    @computed_field
    @property
    def formatted_amount(self) -> str:
        return f"{self.amount:,.2f}"

    @model_validator(mode="after")
    def validate_consistency(self) -> Self:
        # Cross-field validation — enforced in code, not comments
        if self.amount < 0 and self.is_eligible:
            raise ValueError("Negative amount cannot be eligible")
        return self
```

---

## Step 5 — Define invariants

For this entity, what MUST be true at all times?

| Invariant | Enforcement mechanism |
|-----------|----------------------|
| Example: MAX 1 active version per (supplier, date) | BQ query check in health skill + deactivate-before-insert in pipeline |
| Example: amount >= 0 for invoices | `@field_validator` in Pydantic + WHERE clause in BQ |
| Example: invoice_id + legal_entity_code is unique | Deterministic doc ID: `sha256(invoice_id:legal_entity_code)[:24]` |

**Where to enforce in ITRP** (BQ has no UNIQUE constraints):
- **Pydantic validators** — request validation at API boundary
- **Deterministic document IDs** — Firestore idempotency (prevents duplicates)
- **Application-level checks** — in service.py before write
- **Health checks** — post-hoc verification (see `/health` skill)

---

## Step 6 — Generate output files

Create/update these files:

```
backend/app/modules/{module}/
├── types.py    ← Step 3: {Entity}Row(TypedDict)
├── models.py   ← Step 4: {Entity}Response(BaseModel) + validators
├── mappers.py  ← Conversion: {Entity}Row → {Entity}Response
```

**Mapper example:**

```python
# mappers.py
def to_{entity}_response(row: {Entity}Row) -> {Entity}Response:
    return {Entity}Response(
        invoice_id=row["invoice_id"],
        amount=row["amount"],
        category=row["sell_invoice"].lower().strip(),  # normalize here
    )
```

The mapper is the ONLY place where `row["field"]` access is allowed. Service and router use typed objects only.

---

## Step 7 — Verify

After implementation:

1. **Run `/check-types {module}`** to verify TypeScript frontend type matches the new Pydantic model
2. **Check guard compliance** — new contract must pass guard rules:
   - H2: no dict flow (TypedDict and Pydantic, not raw dict)
   - S1: service returns typed results
   - S2: 3-layer models
   - S3: repository returns TypedDict
3. **Check invariants** — can they be tested? Add to `/health` checks if applicable.

---

## Completion

```
## Contract defined: {Entity}

**Files created/updated:** types.py, models.py, mappers.py
**Source of truth:** [BQ table / Firestore collection]
**Invariants:** [N] defined, enforced by [mechanism]
**TypeScript sync:** [verified with /check-types / TODO]
**Existing contracts reused:** [which, or "none — new entity"]
```
