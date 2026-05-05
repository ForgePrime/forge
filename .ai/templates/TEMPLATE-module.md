---
name: new-module
description: WHEN: creating a new backend module. Scaffolds 8+ files per standard.
argument-hint: "[module name]"
disable-model-invocation: true
---

# Implement Module — Reference Architecture

Read `.ai/standards.md` §2 (Backend) and §6 (Data Models) before starting.

Work like an architect who designs the solution before writing the first line of code — every component has a clearly defined responsibility and boundary.

## Scaffold Structure

```
backend/app/modules/{module_name}/
├── __init__.py          # Empty
├── router.py            # THIN: request/response ONLY. Max 30-40 LOC per endpoint. NO DB, NO logic, NO mapping.
├── service.py           # Business logic. Calls repository. Returns TYPED results (not dict).
├── repository.py        # Firestore access ONLY. Returns TypedDict.
├── bq_repository.py     # BigQuery access ONLY. asyncio.gather for parallel.
├── models.py            # Pydantic: API request/response schemas (3rd model layer).
├── types.py             # TypedDict: Storage model + internal contracts (1st model layer).
├── constants.py         # Enums, collection names. Zero magic strings.
├── helpers.py           # Pure functions. No DB access.
└── mappers.py           # RAW → Domain → API transformation (CRITICAL — no mapping in router/service).
```

## 3 model layers (standards.md §6)

```python
# types.py — Storage model (1:1 with BQ/Firestore)
class InvoiceRow(TypedDict):
    invoice_id: str
    amount: float
    ...

# Domain model (business logic operates on this)
# Can be dataclass in types.py or Pydantic in models.py
@dataclass
class Invoice:
    invoice_id: str
    amount: float
    is_eligible: bool  # computed/derived

# models.py — API model (what client sees)
class InvoiceResponse(BaseModel):
    invoice_id: str
    amount: float
    eligible: bool
```

Mapper converts between them. **No `data["field"]` outside the mapper.**

## Rules per layer

- `router.py` → imports ONLY: `service`, `models`, `mappers`, auth dependencies
- `service.py` → imports: `repository`, `bq_repository`, `types`, `constants`, `helpers`. Returns typed results, NOT dict.
- `repository.py` → imports ONLY: `types`, `constants`, Firestore SDK. Returns TypedDict.
- `bq_repository.py` → imports ONLY: `types`, `constants`, BigQuery SDK. All queries have `is_active = TRUE`.
- `mappers.py` → imports: `types`, `models`. Converts RAW → Domain → API.
- **NO file** imports directly from another module — if needed, through service injection

## Every file MUST have

```python
import structlog
logger = structlog.get_logger(__name__)
```

## Register in main.py

```python
from app.modules.{module_name}.router import router as {module_name}_router
app.include_router({module_name}_router)
```

## Implementation order

1. `types.py` — Storage TypedDict + Domain model (contracts FIRST)
2. `constants.py` — enums, collection names
3. `models.py` — Pydantic request/response (API contract)
4. `mappers.py` — RAW → Domain → API conversions
5. `repository.py` — Firestore CRUD (returns TypedDict from types.py)
6. `bq_repository.py` — BQ queries (is_active, settlement filter, override COALESCE)
7. `service.py` — business logic (operates on Domain models)
8. `router.py` — thin endpoints (parse → service → mapper → response)

## Verification

- `python -c "import ast; ast.parse(open('file').read())"` per file
- `docker compose up --build -d backend`
- `curl /health` → OK
- Zero `except Exception: pass`
- Zero `dict` returns from service
- Zero DB access in router
- Zero `Any` without justification
