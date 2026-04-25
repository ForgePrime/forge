# ADR-028 — Frontend stack + 3 sibling redesign decisions

**Status:** RATIFIED — `[ASSUMED: accepted-by=user, date=2026-04-25]` per CONTRACT §B.2. Distinct-actor reviewer is the user pending the Deterministic ADR Gate Pipeline (task #28) which will substitute deterministic CI gates for human review on schema/correctness portions of future ADRs. Acceptance does not transmute the rationale tags below from ASSUMED to CONFIRMED — they remain as labelled.
**Date:** 2026-04-25
**Authored by:** Claude (Opus 4.7, 1M context)
**Decided by:** user (2026-04-25), via blanket acceptance of long-term + AI-autonomy recommendations including Q-meta §A.1–§A.6 cross-cutting principles
**Related:** PLAN_PHASE1_UX_INTEGRATION §3 + §6 (this ADR is the unblocking node for U.1, U.2, U.3, U.4); UX_DESIGN.md §2 (current 3-page IA); MVP_SCOPE.md §L4 (developer-only persona); CONTRACT.md change discipline ("Reuse what exists. Extend, do not duplicate.").

> **Why this ADR exists:** PLAN_PHASE1_UX_INTEGRATION enumerates 4 UNKNOWN slots (U.1–U.4) that gate the entire schema migration + frontend work for the Forge redesign. They are tightly coupled — decided alone, each yields a worse local optimum than decided together. This ADR closes all four atomically.
>
> Decision-quality risk: silently picking shapes during implementation = silent fills = §13 Self-check failure. ADR-028 is the visible alternative.

---

## Context

### What the redesign asks for

Source: `platform/docs/forge_redesign_extracted/` (10 files, extracted 2026-04-25 from `docs/Forge redesign - standalone.html`). Per SESSION_STATE.md §1.8:

- 7 routes (4 NEW: `/dashboard`, `/audit`, `/settings/autonomy`, `/billing` + `/execution/:id/causal`; 2 EXTEND: `/objective/:id`, `/execution/:id/trace`)
- 9 new domain concepts (epistemic_tags, CGAID alternatives, side_effect_map, cascade_dod, kill_criteria K1–K6, metrics M1–M7, trust-debt, stage 0–3, autonomy_pinned)
- React SPA shipped with Inter Tight + IBM Plex Mono fonts

### What the platform has today

- **Frontend [CONFIRMED via filesystem]:** Jinja2 templates (27 files in `platform/app/templates/`) + HTMX + Tailwind, served from `app/api/ui.py` route handlers.
- **Schema [CONFIRMED via grep `app/models/`]:** `objectives.status` 3-state, `objectives.autonomy_optout BOOLEAN`, `decisions.alternatives_considered TEXT` free-form, no epistemic_tag column anywhere.
- **In-memory only [CONFIRMED via SideEffectRegistry code-read]:** C.2 SideEffectRegistry has Python registry; no DB persistence.
- **Production:** docker compose (postgres + uvicorn), 430 pytest passing, 2140 CausalEdges materialised, 33-of-33 .status= sites wrapped via VerdictEngine.

### Forces

| Force | Direction |
|---|---|
| MVP scope = developer-only [CONFIRMED via MVP_SCOPE.md §L4] | favours minimal stack change |
| Redesign assumes interactivity (live trace, drag causal-graph) | favours SPA |
| 27 existing Jinja templates | favours SSR continuation |
| Time-to-Phase-2 ≥ 4 weeks [ASSUMED — based on commit cadence] | tolerates revisit |
| CONTRACT §change-discipline: "extend, do not duplicate" | strongly favours SSR continuation |
| Schema decisions are write-once at Phase 1 boundary | forces sibling decisions into one ADR |

---

## Decision 1 — Frontend stack: **SSR-only (Option A)**

**Adopt:** continue Jinja2 + HTMX + Tailwind for all 7 redesign routes. Port the redesign's React component tree to Jinja templates 1:1 in component shape, not in implementation.

### Rationale

1. **Reversibility cost ≤ 10 PD [ASSUMED].** If Phase 2 design-partner runs prove that two distinct interactivity affordances are blockers (causal-graph drag-pan + live-trace step-by-step animation), the per-route Jinja partial can be replaced by a React island without touching API/data. Jinja → React-island swap touches ≤ 2 files per route. Hybrid (Option C) becomes the back-door.
2. **HTMX covers 80% of the interactivity.** `hx-trigger="every 30s"` for trust-debt panel; `hx-swap` partials for tab switching; SSE for live trace updates (`htmx-sse` extension already vendor-able). Drag-pan is the only genuine SPA-class interaction in the redesign — and it's on a Phase-2 view (`/execution/:id/causal`).
3. **Cost asymmetry.** SSR port = 5–7 PD [ASSUMED, based on 27 templates × ~1.5h each]. SPA migration = 15–25 PD + new build pipeline (Vite + npm + CDN) + auth re-plumb (currently cookie-based session). Cost($skip ADR) > Cost(this ADR) per AntiShortcutSound §3.
4. **No new ops surface.** SPA needs static-asset CDN, build-step in CI, rollback story for JS bundles. SSR needs none — Jinja autoreloads, deploy = git push.
5. **Existing investment.** 27 templates already use Tailwind + HTMX patterns. Discarding them = lost work + retrain cost.

### Reversal trigger (Phase 2 entry)

Hybrid (Option C) is adopted iff **any of the following** is observed in Phase 2 design-partner runs:

- Two or more partners report blocked-by-interactivity on causal-graph or live-trace.
- Time-to-render of a SSR-partial exceeds 200ms p95 on 10k-edge causal graphs.
- Maintenance cost of HTMX-vs-React workarounds for a single feature exceeds 1 PD.

Reversal scope: replace 1–3 Jinja partials with React islands; keep SSR shell. Documented as ADR-NNN at that time.

### Companion artefact: `platform/docs/design_canonical/`

Per long-term + AI-autonomy lens (§A.1, §A.5): keep the redesign React SPA as the **canonical UX truth** at `platform/docs/design_canonical/` (the existing `docs/Forge redesign - standalone.html` + extracted modules in `platform/docs/forge_redesign_extracted/`). The Jinja templates implement against that reference; snapshot tests assert ±10% structural parity (component name + tab order + field set, not pixel positioning).

**Why this matters for AI-autonomy:** when AI in 6 months changes a Jinja partial, it has a *deterministic check* against the canonical reference, instead of self-judging "does this look right?" The snapshot test substitutes for human design review on most changes; designer review is reserved for the next *canonical update*.

### Consequences

| Aspect | Effect |
|---|---|
| Build pipeline | Unchanged (no Vite/npm) |
| Auth | Unchanged (session cookies via FastAPI middleware) |
| Static assets | Unchanged (`app/static/`) |
| Component model | Jinja `include` partials mirror redesign React components 1:1 in name |
| Causal-graph rendering | Server-side SVG or HTMX-fetched fragment. Drag-pan deferred to Hybrid trigger above. |
| Live trace | SSE via `htmx-sse` extension (or polling fallback) |

### Alternatives considered

- **Option B — React SPA wholesale.** Pixel-faithful but +10–18 PD vs SSR; new ops surface; auth re-plumb. Rejected: cost > demonstrated value at MVP scope.
- **Option C — Hybrid SSR shell + React islands now.** Best long-term but pays the SPA tooling cost upfront. Rejected for now: islands are a Phase-2 reaction to validated need, not an a-priori architecture.

---

## Decision 2 — `epistemic_tag` enum: **closed at 6 values, with explicit extension protocol**

**Adopt:** PostgreSQL ENUM `epistemic_tag` with exactly 6 values — 4 from the redesign mock + 2 needed for AI-autonomy distinguishability:

```sql
CREATE TYPE epistemic_tag AS ENUM (
  'INVENTED',              -- author originated the claim, no upstream source (maps to runtime ASSUMED with no source)
  'SPEC_DERIVED',          -- claim follows from a cited spec / contract / SLA
  'ADR_CITED',             -- claim appeals to a specific ADR ID
  'EMPIRICALLY_OBSERVED',  -- claim grounded in runtime observation (test pass, log query, SELECT count)
  'TOOL_VERIFIED',         -- claim verified by deterministic tool (grep, type-check, schema validator with observable output)
  'STEWARD_AUTHORED'       -- claim is held by a Steward; sign-off recorded
);
```

(Note: hyphens in mock `'ADR-CITED'` / `'STEWARD-AUTHORED'` are normalised to underscores for ENUM identifier compatibility. Display layer renders with hyphens. Mock `'DERIVED'` is renamed to `'SPEC_DERIVED'` here to disambiguate from `EMPIRICALLY_OBSERVED` and `TOOL_VERIFIED` — all three are sub-flavours of the redesign's "DERIVED" but with sharply different epistemic strength.)

### Rationale

- **Closed enum gives DB-level integrity check** (CONTRACT §A.1, §A.6); typos fail at write time. AI agents' ad-hoc tags cannot leak into prod.
- **4 values from mock are insufficient for AI-driven content.** CONTRACT §B.2 has 3 runtime tags (CONFIRMED/ASSUMED/UNKNOWN). The persisted enum captures *the basis for CONFIRMED* — and AI generates CONFIRMED claims via 4 fundamentally different mechanisms:
  - Cite an ADR → `ADR_CITED`
  - Cite a spec/contract → `SPEC_DERIVED`
  - Run a deterministic tool (grep/mypy/test) → `TOOL_VERIFIED`
  - Observe runtime data (log query, SELECT count) → `EMPIRICALLY_OBSERVED`
- **Without the distinction**, in scale we cannot tell "AI read the code" from "AI ran the test" — exactly the §A.6 false-completeness vector that CONTRACT exists to prevent.
- **Trust-debt computation** (`trust_debt_snapshot`) can weight categories: `INVENTED` is highest debt; `TOOL_VERIFIED` is lowest. With 4 mock values this metric is degenerate.
- Extension protocol: a 7th value requires (a) an ADR documenting why the existing 6 are insufficient, (b) an Alembic migration `ALTER TYPE epistemic_tag ADD VALUE`. Extension friction is intentional (per §A.3).

### Where applied

- `acceptance_criteria.epistemic_tag epistemic_tag NULL`
- `decisions.epistemic_tag epistemic_tag NULL`

NULL means "untagged legacy row." Backfill is best-effort: rows authored before 2026-04-26 stay NULL; the rendering layer shows "untagged" pill for those.

### Alternatives considered

- **TEXT with CHECK constraint.** Same correctness as ENUM but worse: indexable lookup is slower; no IDE autocomplete via SQLAlchemy. Rejected.
- **Open vocabulary (free TEXT).** Lets ad-hoc tags emerge. Rejected: defeats the entire point of typed epistemic state.
- **Extended set (8–12 values) up-front.** Speculative — no demonstrated need for values beyond the 4. Rejected per CONTRACT minimal-changes discipline.

### Consequences

- Adding a new tag requires an ADR + migration. This is intentional friction.
- Rendering layer must handle NULL (legacy) explicitly with neutral pill.

---

## Decision 3 — `side_effect_map.impact_deltas` JSONB shape: **free-form JSONB with documented expected schema, validator-checked, not DB-enforced**

**Adopt:**

```sql
CREATE TABLE side_effect_map (
  id           BIGSERIAL PRIMARY KEY,
  decision_id  BIGINT NOT NULL REFERENCES decisions(id) ON DELETE CASCADE,
  kind         TEXT NOT NULL,
  owner        TEXT NULL,
  evidence_set_id BIGINT NULL REFERENCES evidence_sets(id),
  blocking     BOOLEAN NOT NULL DEFAULT false,
  impact_deltas JSONB NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

`impact_deltas` is **free-form JSONB** at the DB level. The expected shape is documented in code (`app/schemas/side_effect_map.py` Pydantic model) and validated at the write boundary, not at the DB.

### Expected shape (Pydantic discriminated union — per-dimension type safety)

Per §A.4 self-adjointness + §A.1 DB-level integrity: each dimension has its own typed variant. AI cannot quietly write `"$1.50"` (string) into a numeric latency field.

```python
# app/schemas/side_effect_map.py (proposed)

from typing import Annotated, Literal, Union
from decimal import Decimal
from pydantic import BaseModel, Field

class LatencyDelta(BaseModel):
    dimension: Literal["latency_ms"]
    before: float
    after: float
    confidence: Literal["measured", "estimated", "guess"]

class CostDelta(BaseModel):
    dimension: Literal["cost_usd"]
    before: Decimal
    after: Decimal
    confidence: Literal["measured", "estimated", "guess"]

class BlastRadiusFilesDelta(BaseModel):
    dimension: Literal["blast_radius_files"]
    before: int
    after: int
    confidence: Literal["measured", "estimated", "guess"]

class BlastRadiusUsersDelta(BaseModel):
    dimension: Literal["blast_radius_users"]
    before: int
    after: int
    confidence: Literal["measured", "estimated", "guess"]

class ReversibilityClassDelta(BaseModel):
    dimension: Literal["reversibility_class"]
    before: Literal["A", "B", "C", "D", "E"]   # A = trivially reversible … E = irreversible
    after:  Literal["A", "B", "C", "D", "E"]
    confidence: Literal["measured", "estimated", "guess"]

ImpactDelta = Annotated[
    Union[LatencyDelta, CostDelta, BlastRadiusFilesDelta,
          BlastRadiusUsersDelta, ReversibilityClassDelta],
    Field(discriminator="dimension"),
]
```

`impact_deltas: list[ImpactDelta]` per row (typically 1–5 entries).

**Required deterministic check (per §A.5):** `tests/schemas/test_impact_delta_round_trip.py` — Hypothesis property test asserting Pydantic encode → JSONB → decode = identity. This test is part of G_5.1 ExitGate evidence.

### Rationale

- **Why JSONB and not a separate `impact_delta` table:** the cardinality is low (≤5 deltas per side_effect, ≤7 side_effects per decision). A separate table = 4-way join for one Decision render. JSONB is read-once on Decision detail.
- **Why not enforce shape at DB:** PostgreSQL JSON Schema validators (jsonb_path_match etc.) are slow and clumsy. Pydantic at write boundary catches typos cheaper.
- **Why not free-form forever:** mirrors FORMAL §11.2 typed-spec pattern (P25). Free-form JSONB without a documented contract = silent quality regression.
- **Self-adjointness with rendering (FORMAL P12):** the same Pydantic model produces `render_for_dashboard()` and `validator_rules()`. Drift test catches divergence.

### Alternatives considered

- **DB-enforced JSON schema via `CHECK (jsonb_path_match(impact_deltas, ...))`** — too brittle; schema migration becomes 2-step (relax CHECK → apply DDL → re-tighten).
- **Normalised `impact_delta_row` table** — N+1 join cost on hot read path. Rejected.

### Consequences

- All writes to `side_effect_map.impact_deltas` MUST go through `app/schemas/side_effect_map.py` validator. Direct SQL writes (debug, fixtures) bypass validation — call out in CONTRIBUTING.
- Schema evolution: add new `dimension` enum values → bump Pydantic + retro-tag old rows.

---

## Decision 4 — `objective.stage`: **phase enum {KICKOFF, PLAN, EXEC, VERIFY} as `VARCHAR(8)` + CHECK constraint**

**Adopt:**

```sql
ALTER TABLE objectives ADD COLUMN stage VARCHAR(8) NULL;
ALTER TABLE objectives ADD CONSTRAINT valid_objective_stage
  CHECK (stage IS NULL OR stage IN ('KICKOFF','PLAN','EXEC','VERIFY'));
```

The Python layer uses a string enum (no number↔name mapping):

```python
class ObjectiveStage(str, Enum):
    KICKOFF = "KICKOFF"
    PLAN    = "PLAN"
    EXEC    = "EXEC"
    VERIFY  = "VERIFY"
```

### Rationale (revised under §A AI-autonomy lens)

- **Why VARCHAR + CHECK, not SMALLINT (changed from earlier draft):**
  - Self-documenting in raw SQL: `WHERE stage = 'EXEC'` is unambiguous to AI/human/log reader; `WHERE stage = 2` requires an enum-mapping lookup that lives in Python only — a halucination vector for AI generating SQL.
  - **Consistency with existing codebase pattern** [CONFIRMED via `objective.py:33`]: `objectives.status VARCHAR(20) CHECK IN (...)` is the established pattern. Every other entity (`task.status`, `decision.type`, `finding.status`) follows the same shape. AI has *one* pattern to learn.
  - The "implicit ordering" advantage of SMALLINT (`stage > 1`) was a false positive: stage is categorical, not continuous. `AVG(stage)` and `stage > 1` are not meaningful operations on lifecycle phases. `ORDER BY stage` requires explicit `CASE` either way.
- **Why VARCHAR + CHECK, not PostgreSQL ENUM TYPE:**
  - ENUM TYPE evolution is heavier (`ALTER TYPE ADD VALUE` has transactional limits across PG versions).
  - Adding ENUM TYPE here only would create one column inconsistent with the rest of the codebase — AI must memorise the exception.
- **Why 4 phases not free integer:** redesign mock shows a fixed 4-step Stage indicator [CONFIRMED via grep `forge_redesign_extracted/`]. Open integer = no integrity check + UI variability.
- **Relationship to existing `objective.status`:** independent. `status` ∈ ('ACTIVE','ACHIEVED','ABANDONED') describes lifecycle outcome; `stage` describes current phase within ACTIVE. An ABANDONED objective freezes whatever stage it was in.

### Backfill

Existing objectives: NULL stage. Backfill heuristic (one-shot, string literals):

```sql
UPDATE objectives SET stage = 'EXEC'
WHERE id IN (SELECT objective_id FROM tasks WHERE status IN ('IN_PROGRESS','DONE'))
  AND stage IS NULL;

UPDATE objectives SET stage = 'KICKOFF'
WHERE id NOT IN (SELECT objective_id FROM tasks)
  AND stage IS NULL;
```

Anything ambiguous → stays NULL → renders "stage unknown" in UI.

### Alternatives considered

- **Free integer 0..N.** Rejected: speculative; no UI affordance for stage > 3.
- **TEXT with CHECK constraint.** Heavier; same outcome.
- **PostgreSQL ENUM type.** Heavier ALTER cost than SMALLINT. Same correctness.
- **Reuse `objective.status`.** Rejected: status is lifecycle outcome, stage is intra-lifecycle phase. Conflating them = lossy.

---

## Composite consequence — what changes in the codebase

After ratification of all 4 decisions:

| File | Change |
|---|---|
| `platform/migrations/versions/2026_04_26_phase1_redesign.py` | New Alembic revision: 5 tables + 4 cols + 1 enum |
| `app/models/decision.py` | Add `epistemic_tag`, relationship to `alternatives` and `side_effect_map` |
| `app/models/acceptance_criteria.py` | Add `epistemic_tag` |
| `app/models/objective.py` | Add `stage` SMALLINT, `autonomy_pinned` VARCHAR(8) |
| `app/models/alternative.py` (new) | Typed model for CGAID alternatives |
| `app/models/side_effect_map.py` (new) | Typed model + Pydantic validator |
| `app/models/cascade_dod_item.py` (new) | DoD checklist item |
| `app/models/kill_criteria_event_log.py` (new) | K1–K6 firing log |
| `app/models/trust_debt_snapshot.py` (new) | Snapshot rows |
| `app/schemas/side_effect_map.py` (new) | Pydantic ImpactDelta schema |
| `app/templates/dashboard.html` (new) | Phase 1 main view |
| `app/templates/objective_detail.html` (extend) | 4 → 9 tabs |
| `app/templates/_*.html` (new ×N) | Tab partials for CGAID, SideEffects, DoD |
| `app/api/ui.py` | Routes for `/dashboard`, `/audit`, `/settings/autonomy`, `/billing`, `/execution/:id/causal` |
| `app/middleware/rbac.py` (new) | Role check for Steward-only mutations |

[ASSUMED] no other entity is impacted. **Verification:** grep `\.status\s*=\s*['"]` and `epistemic_tag` after migration to assert no new direct-status-assignment or untagged-write paths emerged.

---

## Failure scenarios (CONTRACT §B.5)

| # | Scenario | Mitigation |
|---|---|---|
| 1 | Migration partially applied (DDL succeeds, backfill fails) | Each `up()` is one transaction; if any step fails the whole revision rolls back. Backfill is in a separate revision. |
| 2 | Old code reads new column before deploy | Migration deployed BEFORE code referencing new columns is released — standard Alembic ordering. |
| 3 | Pydantic shape changes for `impact_deltas` after rows exist | Versioned validator: `ImpactDelta_v1`, `ImpactDelta_v2`; reader accepts both, writer emits latest. |
| 4 | A 5th `epistemic_tag` value is needed urgently | Documented protocol: ADR + ALTER TYPE migration. Friction is intentional. |
| 5 | Stage backfill heuristic misclassifies | NULL is the safe default; the heuristic only fills clear-cut cases. UI shows "stage unknown" gracefully. |

---

## Steel-man — strongest counter to this ADR

**Counter:** "Bundling 4 decisions into one ADR makes it hard to reverse any single one. If Decision 2 (epistemic_tag at 4) is wrong, we have to revisit a wider blast radius than necessary."

**Counter-counter:** the 4 decisions are coupled by Phase 1 schema migration ordering. If we split:
- Stack ADR alone — fine.
- 3 schema ADRs each — each schema ADR locks 1 column shape but not the others. Migration deploy can't proceed until all 3 ratify. Splitting just adds ratification serialisation cost without reducing reversal cost.

Reversal of Decision 2: ALTER TYPE migration. Cost is identical whether the original decision lived in this ADR or its own.

**If the steel-man holds:** decisions 2/3/4 could be split into ADR-029/030/031 at user request. The cost is +3 documents to maintain.

---

## Disclosure (CONTRACT §A)

- **§A.1 Assumption.** Reversal cost of stack ≤ 10 PD is ASSUMED; if Phase-2 partners report blocked-by-interactivity beyond causal-graph drag-pan, the cost may escalate. Verification: 2 design-partner runs in Phase 2.
- **§A.2 Partial implementation.** This ADR defines schema + stack but does not author the migration code or template ports. Tasks #26 + #27 remain pending until ratification.
- **§A.6 False completeness.** [UNKNOWN] who is the distinct-actor reviewer (SESSION_STATE.md U.5). Until that is named, ratification cannot complete.

---

## Approval

**Ratified 2026-04-25** with `[ASSUMED: accepted-by=user]` per CONTRACT §B.2. The user reviewed long-term + AI-autonomy recommendations (Q-meta §A.1–§A.6 cross-cutting principles) and elected the recommended path on Q1, Q2 (rev. to 6 values), Q3 (rev. to discriminated union), Q4 (rev. to VARCHAR), Q5 (user-now + task #28), Q6 (push branch, defer MR).

**Distinct-actor disposition:** until task #28 (Deterministic ADR Gate Pipeline) lands, distinct-actor on schema/migration ADRs is the user. Task #28 substitutes deterministic CI gates (`psql --dry-run`, reversal test, Pydantic round-trip, mypy strict) for the human verification of *correctness portions*; human review remains for *judgment portions* (option A vs B, vocabulary scope).

**Conditions for downstream (G_approve in PLAN_PHASE1_UX_INTEGRATION §7):**

- ✓ User ratified ADR-028.
- ✓ U.1, U.2, U.3, U.4 closed by this ADR.
- ✓ U.5 closed (accepted-by=user, ASSUMED-tagged).
- ✓ U.6 closure pending: branch push approved (deferred MR).

Tasks #26, #27 unblock per PLAN_PHASE1_UX_INTEGRATION §6 once schema migration is run on dev DB.
