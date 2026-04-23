# Forge Platform — Onboarding

> **Status:** DRAFT per [`../decisions/ADR-003`](../decisions/ADR-003-human-reviewer-normative-transition.md). Time claims in this doc are `[ASSUMED]`; real first-contributor walkthrough will produce empirical time budget (tracked R-DOC-04).

**Audience:** new contributor joining Forge platform work. Developer or reviewer who needs to ship a first change.

**Estimated total time:** ~1 hour to "first meaningful contribution" (ASSUMED — validate on first real onboarding).

**Structure** (per Diátaxis + Hamel Husain error-analysis-first pattern):
1. Part 1 — **One-page system map** (15 min).
2. Part 2 — **Working tutorial** (30 min, produces a real artifact).
3. Part 3 — **Failure catalog** (15 min, what breaks and why — the most valuable content per Husain).

---

## Part 1: One-page system map

### What is Forge?

- A **governance platform** for AI-driven software delivery.
- Multi-tenant web app + MCP server.
- Runs as FastAPI process + Postgres + optional Redis.
- Contributors edit `platform/app/` + `platform/tests/` + `platform/docs/`.

### Where to look for X

| Question | Answer |
|---|---|
| "What should Forge do (spec)?" | [`../FORMAL_PROPERTIES_v2.md`](../FORMAL_PROPERTIES_v2.md) — 25 atomic properties. |
| "What's the gap between spec and code?" | [`../GAP_ANALYSIS_v2.md`](../GAP_ANALYSIS_v2.md). |
| "What phase is the work in?" | [`../ROADMAP.md`](../ROADMAP.md). |
| "What's the risk?" | [`../DEEP_RISK_REGISTER.md`](../DEEP_RISK_REGISTER.md). |
| "How is the platform built?" | [`ARCHITECTURE.md`](ARCHITECTURE.md). |
| "How does work flow through it?" | [`WORKFLOW.md`](WORKFLOW.md). |
| "What are the entities?" | [`DATA_MODEL.md`](DATA_MODEL.md). |
| "What was decided and why?" | [`../decisions/`](../decisions/). |
| "Who reviews what?" | [`../reviews/README.md`](../reviews/README.md). |

### Technology you'll touch

- **Python 3.11+** — primary language.
- **FastAPI** — HTTP routers (`app/api/`).
- **SQLAlchemy 2.0+** — ORM (`app/models/`).
- **Alembic** — DB migrations.
- **Pydantic 2.0+** — schemas (`app/schemas/`).
- **pytest** — tests.
- **Jinja2 + HTMX** — server-rendered UI (`app/templates/`).
- **Ruff** — lint (line length 120).

### The 7 most important folders

```
platform/
├── app/
│   ├── api/             ← HTTP endpoints (12 routers)
│   ├── services/        ← business logic (47 files)
│   ├── models/          ← SQLAlchemy entities (30 files)
│   ├── schemas/         ← Pydantic DTOs
│   ├── templates/       ← Jinja2 + HTMX UI
│   └── main.py          ← entry point, lifespan, middleware
├── tests/               ← pytest (~420 tests)
├── docs/                ← governance + tech docs (you are here)
├── mcp_server/          ← Model Context Protocol server
├── alembic/             ← migrations
└── seed/                ← seed data
```

### The 5 core entities (30-second mental model)

1. **Project** — a codebase Forge orchestrates work on.
2. **Objective** → **KeyResult** — measurable business goal + metrics.
3. **Task** → **AcceptanceCriterion** — atomic unit of work + mechanical success gates.
4. **Execution** → **ExecutionAttempt** — a run attempting the task, with assembled prompt + delivery + validation result.
5. **Decision** / **Change** / **Finding** — evidence artifacts produced during execution.

Full list: [`DATA_MODEL.md`](DATA_MODEL.md).

### The 3 hard rules you must not break

1. **No direct `Model.status = "X"` outside `VerdictEngine`** — tracked as 75 current violations, slated for Phase A cleanup. Don't add new ones.
2. **Feature/bug tasks MUST have ≥ 1 AC with `verification='test'|'command'`** — `contract_validator.py:188-194` rejects otherwise.
3. **Every non-trivial claim in reasoning MUST carry `[CONFIRMED]`/`[ASSUMED]`/`[UNKNOWN]` tag** — per CONTRACT §B.2, enforced by `contract_validator`.

---

## Part 2: Working tutorial — ship a first change

**Goal:** extend the `scenario_type` enum with one new value (`boundary`) per [ADR-001](../decisions/ADR-001-scenario-type-enum-extension.md). Start small.

**Prerequisites:**
- Repo cloned.
- Docker + docker-compose installed.
- Python 3.11+ + `uv` (or pip).
- Read **Part 1** above.

### Step 1 — Start the platform

```bash
cd platform
cp .env.example .env
docker compose up -d postgres redis
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

**Expected output:**
```
INFO:     Started server process [...]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

**Verify:**
```bash
curl http://localhost:8000/health
# {"status":"ok","version":"0.1.0"}

curl http://localhost:8000/ready
# {"ready":true,"checks":{"db":"ok","redis":"ok"},"version":"0.1.0"}
```

If `/ready` returns 503: check Postgres + Redis via `docker compose ps`. See **Part 3: Failure catalog** below.

### Step 2 — Explore existing tests

```bash
uv run pytest tests/test_contract_validator_gates.py -v
# ~14 checks pass
```

These are the deterministic gates you'll extend. Open [`platform/tests/test_contract_validator_gates.py`](../../tests/test_contract_validator_gates.py) to see the style.

### Step 3 — Locate the enum

Per `[CONFIRMED]` from [ADR-001](../decisions/ADR-001-scenario-type-enum-extension.md):

- Schema: [`platform/app/models/task.py:86-88`](../../app/models/task.py) — `CheckConstraint`.
- Pydantic patterns: `projects.py:24, 130`, `tier1.py:650`, `ui.py:1333, 1360`.
- Generator: [`platform/app/services/scenario_generator.py:30-35`](../../app/services/scenario_generator.py) — `NEGATIVE_EXPECTATIONS` dict.
- Validator: [`platform/app/services/contract_validator.py:188-194`](../../app/services/contract_validator.py) — AC composition check.

### Step 4 — Write a failing test first

```python
# tests/test_scenario_type_boundary.py (new file)
import pytest

def test_scenario_type_accepts_boundary():
    """ADR-001: scenario_type enum extended to 9 values."""
    from app.models import AcceptanceCriterion, Task, Project
    # ... minimal setup ...
    ac = AcceptanceCriterion(
        text="When n = 0, exactly boundary case; must not crash",
        scenario_type="boundary",   # ← not yet accepted
        verification="test",
    )
    # should not raise CheckConstraint violation
```

Run:
```bash
uv run pytest tests/test_scenario_type_boundary.py
# FAIL — CheckConstraint violation
```

Good. Red test.

### Step 5 — Write the migration

Per ADR-001 Consequences §:

```bash
uv run alembic revision -m "ADR-001 extend scenario_type enum to 9 values"
```

Edit the generated file to drop old constraint + add new one:

```python
# alembic/versions/<timestamp>_adr_001_extend_scenario_type_enum_to_9_values.py
from alembic import op

def upgrade():
    op.execute("ALTER TABLE acceptance_criteria DROP CONSTRAINT IF EXISTS valid_scenario_type")
    op.execute("""
        ALTER TABLE acceptance_criteria ADD CONSTRAINT valid_scenario_type
        CHECK (scenario_type IN (
          'positive', 'negative', 'edge_case', 'boundary',
          'concurrent', 'malformed', 'regression',
          'performance', 'security'
        ))
    """)

def downgrade():
    op.execute("ALTER TABLE acceptance_criteria DROP CONSTRAINT IF EXISTS valid_scenario_type")
    op.execute("""
        ALTER TABLE acceptance_criteria ADD CONSTRAINT valid_scenario_type
        CHECK (scenario_type IN ('positive', 'negative', 'edge_case', 'regression'))
    """)
```

Apply:
```bash
uv run alembic upgrade head
```

### Step 6 — Update the model

Edit [`platform/app/models/task.py:86-88`](../../app/models/task.py):

```python
CheckConstraint(
    "scenario_type IN ('positive', 'negative', 'edge_case', 'boundary', "
    "'concurrent', 'malformed', 'regression', 'performance', 'security')",
    name="valid_scenario_type",
),
```

### Step 7 — Update Pydantic patterns

Edit `projects.py:24, 130`, `tier1.py:650`, `ui.py:1333, 1360`:

```python
scenario_type: str = Field(
    "positive",
    pattern="^(positive|negative|edge_case|boundary|concurrent|malformed|regression|performance|security)$"
)
```

### Step 8 — Update the generator

Edit [`platform/app/services/scenario_generator.py:30-35`](../../app/services/scenario_generator.py):

```python
NEGATIVE_EXPECTATIONS = {
    "positive": "Operation succeeds",
    "negative": "Operation is rejected with appropriate error code (400/409/422)",
    "edge_case": "Edge-case scenario handled without crash (distinct from boundary)",
    "boundary": "N-1/N/N+1 triplet all handled; boundary value explicit",
    "concurrent": "Behavior under concurrent invocation: state consistent, no race",
    "malformed": "Malformed input rejected; no injection / crash / undefined behavior",
    "regression": "Existing behavior preserved",
    "performance": "Latency / memory within stated bound",
    "security": "No unauthorized access, PII leak, injection vulnerability",
}
```

### Step 9 — Run tests

```bash
uv run pytest tests/test_scenario_type_boundary.py -v
# PASS

uv run pytest tests/ -v
# All existing tests still green
```

### Step 10 — Verify the full audit chain

Your change must obey the operational contract (CONTRACT §B):

**DID:**
- Alembic migration created + applied → `alembic current` shows new head.
- `task.py:86-88` CheckConstraint updated to 9 values.
- 5 Pydantic patterns updated.
- `scenario_generator.py` NEGATIVE_EXPECTATIONS extended.
- `tests/test_scenario_type_boundary.py` green.
- Existing 420 tests green.

**DID NOT:**
- Did not update `contract_validator.py:188` AC composition rule — still accepts only `{negative, edge_case}` for failure coverage. Extending that rule to accept the new categories is a separate change in Phase F.
- Did not update seed data `output_contracts` to require new categories per ceremony — separate ADR (Phase G.7).

**CONCLUSION:**
- Schema accepts 9 values as ADR-001 specifies.
- Existing workflows continue working.
- Full enforcement of new categories (risk-weighting, classifier heuristics) deferred to Phase F.

### Step 11 — Open PR

```bash
git checkout -b adr-001-scenario-type-enum-extension
git add platform/alembic/versions/ platform/app/models/task.py \
        platform/app/api/ platform/app/services/scenario_generator.py \
        platform/tests/test_scenario_type_boundary.py
git commit -m "ADR-001: extend scenario_type enum to 9 values

- Alembic migration adds boundary/concurrent/malformed/performance/security
- Pydantic patterns updated (5 locations)
- Generator heuristics per-category
- Test: test_scenario_type_boundary.py

Refs: docs/decisions/ADR-001-scenario-type-enum-extension.md"
```

PR description:
```
## Summary
- Implements ADR-001 scenario_type enum extension (9 values).

## Test plan
- [ ] Alembic migration up/down round-trips cleanly.
- [ ] New test passes.
- [ ] Existing 420 tests green.
- [ ] Manual UI check: scenario_type dropdown shows new options in objective_detail.html.
```

### Step 12 — Request review

Per ADR-003, ADR content (and by extension, PRs implementing ADRs) require distinct-actor review. Request review from user or separate actor. Record review per [`../reviews/_template.md`](../reviews/_template.md).

---

## Part 3: Failure catalog

Most valuable content per Hamel Husain's error-analysis-first approach. What breaks, why, how to recover.

### Setup failures

**Startup fails with `psycopg2 ImportError` or Python 3.13 crash.**
- **Cause:** SQLAlchemy < 2.0.35 doesn't support Python 3.13.
- **Fix:** `uv sync` pulls ≥ 2.0.35 per pyproject.toml. If still failing, `pip install sqlalchemy>=2.0.35 --upgrade`.
- **Evidence:** pyproject.toml comment on line 9.

**`/ready` returns 503 with `db: fail`.**
- **Cause:** Postgres not running or `DATABASE_URL` wrong.
- **Fix:** `docker compose ps` — verify postgres is Up. Check `.env` `DATABASE_URL`.

**`/ready` returns 503 with `redis: fail` but Redis not needed.**
- **Cause:** `REDIS_URL` set in `.env` but Redis not running.
- **Fix:** Either start Redis (`docker compose up -d redis`) or remove `REDIS_URL` from `.env`.

**Startup hangs on `Application startup complete`.**
- **Cause:** `schema_migrations.apply` runs idempotent ALTERs; large DB → slow.
- **Fix:** Wait. If > 5 min, inspect logs for specific ALTER.

**Tests fail with "database locked".**
- **Cause:** `conftest.py` uses SQLite in some fixtures; parallel tests collide.
- **Fix:** Run with `pytest -x` (stop on first fail) + `--workers 1`.

### Orchestration failures

**Task stuck in `IN_PROGRESS` state after Forge restart.**
- **Cause:** Previous session crashed; lease didn't release.
- **Fix:** Next uvicorn startup triggers orphan recovery (`main.py:59-72`) — Task auto-released to TODO.
- **Evidence:** `orphan_recovery.py:113` `t.status = "TODO"`.

**Delivery rejected with "resubmit.padding + resubmit.identical_reasoning".**
- **Cause:** `ExecutionAttempt.reasoning_hash` detects agent submitted same reasoning twice with minor diff.
- **Fix:** Actually address the validator feedback; don't just pad the reasoning.
- **Evidence:** `contract_validator.py` resubmit detection logic.

**`contract_validator` rejects delivery with "no negative/edge_case scenario with PASS".**
- **Cause:** Feature/bug task without ≥ 1 failing-path AC.
- **Fix:** Add AC with `scenario_type in {negative, edge_case}` — per Phase F/ADR-001 also accepts `{boundary, concurrent, malformed}` once that rule is extended.
- **Evidence:** `contract_validator.py:188-194`.

**Delivery rejected with "no file/test reference".**
- **Cause:** AC evidence doesn't cite a file path or test node id.
- **Fix:** Evidence must match `FILE_PATTERN` (`\w+\.(py|ts|...)`) or `TEST_PATTERN` (`tests/<path>::test_name`).

**Pytest runs within test_runner don't see new code.**
- **Cause:** test_runner uses a subprocess; SQLAlchemy session not shared.
- **Fix:** Ensure migrations applied in test DB before pytest; see `conftest_populated.py`.

### Multi-tenancy failures

**"Project not found" when project exists.**
- **Cause:** Project in different `Organization` than current user.
- **Fix:** Check `Membership` — user must have role in the project's org.
- **Evidence:** `tenant.py` isolation logic.

### Audit / trust failures

**PR merged without `[CONFIRMED]`/`[ASSUMED]`/`[UNKNOWN]` tags in reasoning.**
- **Cause:** `contract_validator` currently emits WARNING, not FAIL, for missing tags. Phase F (P19 Assumption Control) promotes to REJECT.
- **Fix:** Add tags manually until Phase F ships.

**Decision approved without alternatives considered.**
- **Cause:** `Decision.alternatives_considered` JSONB allows empty. Phase F (P21 Root Cause Uniqueness) adds validator rule requiring ≥ 2 for `type='root_cause'`.
- **Fix:** Populate manually; track as R-SPEC-04 residual.

### Known gaps that will bite you

- **No `VerdictEngine` yet** — state transitions are scattered across 75 sites in 9 files. Easy to add a new one without realizing it. **Don't.** Reference [`../GAP_ANALYSIS_v2.md §P7`](../GAP_ANALYSIS_v2.md) for the file list.
- **`MINIMAL` ceremony_level** mentioned in outer `forge/.claude/CLAUDE.md:86` does NOT exist in platform. Platform has only `{LIGHT, STANDARD, FULL}`. Per [ADR-002](../decisions/ADR-002-ceremony-level-cgaid-mapping.md).
- **Stage 0 Data Classification** is NOT implemented. **Do not adopt Forge for Confidential+ client material without DLP** (R-FW-02 CRITICAL).
- **Self-authored spec** — all `platform/docs/` is DRAFT until peer-reviewed per [ADR-003](../decisions/ADR-003-human-reviewer-normative-transition.md). **Do not treat as binding yet.**

### Where to ask for help

1. Before coding: read [`../FORMAL_PROPERTIES_v2.md`](../FORMAL_PROPERTIES_v2.md) for applicable property.
2. If stuck on design: check [`../decisions/`](../decisions/) for prior ADR.
3. If risk concern: [`../DEEP_RISK_REGISTER.md`](../DEEP_RISK_REGISTER.md) — 29 known risks.
4. If code unclear: `app/services/<name>.py` usually has module docstring.
5. If test failing mysteriously: `tests/conftest.py` + `conftest_populated.py` for fixtures.

---

## After onboarding

- Pick a Phase A sub-stage from [`../ROADMAP.md §4`](../ROADMAP.md).
- Create an ADR if your change involves a decision per [`../decisions/README.md`](../decisions/README.md).
- Request review per [`../reviews/README.md`](../reviews/README.md).
- Update `IMPLEMENTATION_TRACKER.md` with `[EXECUTED]` evidence when landed.
