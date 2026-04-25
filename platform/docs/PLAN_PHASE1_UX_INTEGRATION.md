# PLAN_PHASE1_UX_INTEGRATION.md — Forge redesign integration

**Status:** RATIFIED 2026-04-25 (`[ASSUMED: accepted-by=user]` per CONTRACT §B.2). ADR-028 RATIFIED with revisions per long-term + AI-autonomy lens (Q-meta §A.1–§A.6). U.1, U.2, U.3, U.4, U.5 closed. U.6 (push) approved, MR deferred.
**Date:** 2026-04-25
**Theorem compliance:** AntiShortcutSound (user-supplied, 2026-04-25). Each §15 conjunct is mapped to a section below; gaps tagged `[UNKNOWN]` propagate to §6 STOP.
**Branch:** `docs/forge-plans-soundness-v1` (local-only).
**Depends on:** SESSION_STATE.md §1.8 (redesign analysis), UX_DESIGN.md (L4 spec), MVP_SCOPE.md, FORMAL_PROPERTIES_v2.md.
**Blocks (downstream):** task #25 (ADR-028), task #26 (schema migrations), task #27 (DashboardView impl).

---

## §0 How to read this plan

| Symbol | Meaning |
|---|---|
| `[CONFIRMED]` | Verified against running code or filesystem at the cited file/line. |
| `[ASSUMED]` | Inferred from spec or code-read; may be wrong; consequence stated. |
| `[UNKNOWN]` | Not known. Triggers §6 STOP for any step whose gate depends on it. |
| `Pred ⇒ Obs` | Prediction-vs-observation pair (per AntiShortcutSound §8). |
| `G_x = ⟨...⟩` | Gate predicate; must evaluate to true to advance. |
| `Closure(...)` | Impact closure per AntiShortcutSound §10 (deps ∪ consumers ∪ side_effects ∪ ordering). |

The plan owes 10 steps (§15). Each step has: artifact, evidence tags, exit gate. The whole plan composes into Phase 1 with one approval gate (§7) and one prediction cross-check (§8).

---

## §1 Pred — what the redesign promises (Step 1, §1 Pred)

Source: `platform/docs/forge_redesign_extracted/` (10 files, extracted 2026-04-25 from `docs/Forge redesign - standalone.html`). Cross-ref SESSION_STATE.md §1.8.

### §1.1 New surfaces (7 routes vs current 3)

**Current MVP web pages [CONFIRMED via filesystem `platform/app/templates/`]:** 3 pages (`/`, `/projects/{slug}`, `/objectives/{id}`, `/executions/{id}`). Stack: Jinja2 + HTMX + Tailwind. 27 templates, no React.

**Redesign target [CONFIRMED via `efcace3c_application-javascript.txt` + `795a3009_application-javascript.txt`]:** 7 surfaces:

| Route | Content | Owner persona | Status |
|---|---|---|---|
| `/dashboard` | Hero (active K6 halt count, trust-debt index), M1–M7 panel, K1–K6 panel, Objectives list with epistemic-tag pills | Tech-lead + Steward | NEW |
| `/objective/:id` | 9 tabs (Overview, **CGAID**, **SideEffects**, **DoD**, Decisions, AC, KR, Tasks, Sources) | Developer + Tech-lead | EXTENDS existing `objective_detail.html` |
| `/audit` | DRT-style filterable Decision/Finding ledger | Compliance | NEW |
| `/execution/:id/trace` | Step-by-step DRT with epistemic-tag annotations | Developer | EXTENDS existing |
| `/execution/:id/causal` | Causal-graph SVG (B.3 CausalGraph rendering) | Developer | NEW |
| `/settings/autonomy` | Per-objective `autonomy_pinned` switch ('L1'/'L2'/'L3') | Steward | NEW |
| `/billing` | LLM cost rollups, quotas | Executive | NEW |
| `/map` | Constellation DAG view (Objective→KR→AC→Task→TestRun→Source) — full feature set with two layouts, isolation focus, animated evidence flow, K-trip flash, mini-feed, 8 filters | Developer + Tech-lead | **NEW (Phase 2 deferred per UX_DESIGN.md §11.11)** — Phase 1 minimum subset (force layout, OBJ+Task only, "AI active now" filter, 5s poll) is **specified but not enacted** in Phase 1 scope; enactment requires explicit scope-expansion decision |

### §1.2 New domain concepts (9 — schema-impacting)

Listed in SESSION_STATE.md §1.8. Concrete shapes from mock:

1. **`epistemic_tag` enum** [CONFIRMED via grep of mock + revised under §A AI-autonomy lens]: 6 closed values — `INVENTED | SPEC_DERIVED | ADR_CITED | EMPIRICALLY_OBSERVED | TOOL_VERIFIED | STEWARD_AUTHORED`. 4 from mock + 2 added (`EMPIRICALLY_OBSERVED`, `TOOL_VERIFIED`) to distinguish AI-generated CONFIRMED claims by their basis (cited spec vs ran-tool vs observed-runtime). Mock `'DERIVED'` renamed to `'SPEC_DERIVED'` for disambiguation. **U.2 closed by ADR-028 D2 (revised).**
2. **`alternative` (CGAID)** — `alternatives: [{ text, src, blocks, task_ref, impact_deltas }]` per Decision row. Currently absent from `app/models/decision.py`.
3. **`side_effect_map`** — table of `(decision_id, side_effect_kind, owner, evidence_ref, blocking)`. C.2 SideEffectRegistry exists in code but is NOT persisted (in-memory registry only). U.3 disambiguates persisted vs ephemeral.
4. **`cascade_dod`** — Definition-of-Done checklist per Objective. Replaces today's `objective.success_criteria TEXT` blob. Schema needed.
5. **`kill_criteria` K1–K6** — 6 fixed predicates ('K1 owner-required', 'K2 evidence-link', 'K3 reversibility', 'K4 solo-verifier', 'K5 budget-cap', 'K6 contract-violation'). Surface only — these are gates over GateRegistry, not entities.
6. **`metrics` M1–M7** — 7 KPIs (latency, cost, BLOCKED rate, override rate, etc.). View-layer aggregation; no new entity.
7. **`trust_debt`** — composite index (formula in mock; needs ratification). View-layer; no entity.
8. **`stage`** — Objective lifecycle phase (Kickoff → Plan → Exec → Verify). Currently `objective.status ∈ ('ACTIVE','ACHIEVED','ABANDONED')`. **U.4 closed by ADR-028 D4 (revised): `VARCHAR(8)` + CHECK IN ('KICKOFF','PLAN','EXEC','VERIFY')** — consistent with existing `objectives.status VARCHAR(20) CHECK IN (...)` pattern. NOT SMALLINT (rejected: opaque codes; AI sees `WHERE stage=2` requires Python-side enum lookup = halucination vector).
9. **`autonomy_pinned`** — string enum on Objective: `'L0' | 'L1' | 'L2' | 'L3' | NULL`. Currently `objective.autonomy_optout BOOLEAN` exists; needs replacement or extension.

### §1.3 Pred summary

- **5 new tables** (alternatives, side_effect_map, cascade_dod_item, kill_criteria_event_log, trust_debt_snapshot)
- **4 new columns** (objectives.stage, objectives.autonomy_pinned, decisions.epistemic_tag, acceptance_criteria.epistemic_tag)
- **1 new enum** (epistemic_tag)
- **4 new SSR routes** + extension of 2 existing

[ASSUMED] this list is exhaustive against the redesign mocks. **Consequence if wrong:** missed migration → frontend renders with NULL columns → P21 evidence-link checks pass on empty data → silent quality regression.

**Verification of assumption (deferred to Step 2):** complete grep of all 10 extracted files for `${field}` references yielding a closed set; cross-check vs `app/models/*.py`.

---

## §2 Schema audit — what already exists (Step 2, §1 Existing context)

Goal: minimise migration delta. Reuse before adding.

| Redesign concept | Existing entity / column | Verdict |
|---|---|---|
| epistemic_tag enum | none | ADD enum + 2 cols |
| alternative (CGAID) | `decisions.alternatives_considered TEXT` (free-form) [CONFIRMED via app/models/decision.py:55] | UPGRADE to typed table |
| side_effect_map | `c.2 SideEffectRegistry` in-memory only [CONFIRMED] | ADD persisted table |
| cascade_dod | `objectives.success_criteria TEXT` [CONFIRMED via objective.py] | UPGRADE to checklist table |
| kill_criteria K1–K6 | none — gates over GateRegistry | NO new entity; new view-layer rendering only |
| metrics M1–M7 | aggregations over `executions` + `llm_calls` [CONFIRMED] | NO new entity; view-only |
| trust_debt | derived | NO new entity; view-only |
| stage_0_3 | `objectives.status` (3-state) | EXTEND or new col |
| autonomy_pinned | `objectives.autonomy_optout BOOLEAN` [CONFIRMED] | REPLACE BOOLEAN with enum |

**Migration count:** 5 new tables + 4 column changes + 1 enum + 1 boolean→enum migration.

Cross-ref §14: this audit is the input to Step 3 (Stack decision) and Step 5 (Schema migration plan).

---

## §3 Stack decision — React SPA vs HTMX-SSR continuation (Step 3, §1 Architecture decision)

**Status: U.1 — UNKNOWN (blocks Step 9 per §6).**

The redesign ships as a React SPA (Babel in-browser, ~3.5MB). The current platform is HTMX-SSR with Jinja2 + Tailwind. Three options:

| Option | Pros | Cons | Cost ($D) |
|---|---|---|---|
| **A. Port redesign to SSR** (Jinja2 templates mirroring React components) | Stays on existing stack; no build pipeline; works on day 1 | Loses some interactivity (causal-graph drag, live trace updates); manual port labour | **5-7 person-days** |
| **B. Adopt React SPA wholesale** | Pixel-faithful; uses redesign as-is | Requires Vite build, npm tooling, FastAPI as JSON-API only, auth re-plumb, CDN/static config | **15-25 person-days** + ongoing |
| **C. Hybrid** (SSR shell + React islands for causal-graph + live trace only) | Cheap interactivity where it matters; SSR everywhere else | Two stacks to maintain; cognitive overhead | **8-12 person-days** |

**Decision drivers (rank-ordered):**

1. **MVP scope** [CONFIRMED via MVP_SCOPE.md §L4]: developer-only persona; the high-interactivity views (`/audit`, `/dashboard`, `/billing`) are Phase 2-3. → SPA value is back-loaded.
2. **CONTRACT.md change discipline:** "Reuse what exists. Extend, do not duplicate." HTMX-SSR is the existing stack.
3. **Existing investment:** 27 templates already use Tailwind + HTMX patterns. Discarding = lost work.
4. **Cost($skip) vs Cost($step) per AntiShortcutSound §3:** A SPA migration with no plan runs through Cost(verify-cost) ≈ 0 → Cost(skip) > Cost(step). Doing the ADR is mandatory.

[ASSUMED] Option A (SSR port) is the recommended path. **Consequence if wrong:** if a Phase 2 persona (Tech-lead) needs the live-update affordances of SPA, we re-do this decision with a more expensive context-switch.

Cross-ref §14: ADR-028 (task #25) ratifies this; until then, U.1 is open. **Step 9 implementation gate G_7 = (U.1 = closed)** ⇒ task #27 STOPs.

---

## §4 Failure-scenario inventory (Step 4, §11 completeness)

The 9 §11 scenarios applied to Phase 1 work:

| # | Scenario | Mitigation |
|---|---|---|
| F1 | **null_or_empty_input** — user lands on `/dashboard` with zero objectives | Empty-state copy in DashboardView; trust-debt panel reads "no data yet" |
| F2 | **timeout_or_dependency_failure** — `causal_edges` query times out at 10k+ rows | Add LIMIT + paginate cursor in B.3 CausalGraph.window(); SSR partial render with HTMX fragment swap |
| F3 | **repeated_execution** — user double-submits autonomy switch | Idempotency-key on `/settings/autonomy/objective/:id`; A.5 store dedups |
| F4 | **missing_permissions** — non-Steward toggles `autonomy_pinned` | RBAC middleware (currently absent for `autonomy_optout`!); scope: ADD permission check in this phase |
| F5 | **migration_or_old_data_shape** — existing `decisions.alternatives_considered TEXT` blobs at upgrade | Backfill is no-op (read both old TEXT blob + new typed table; deprecate TEXT after 1 release) |
| F6 | **frontend_not_updated** — old browser cache shows pre-redesign UI | Cache-bust via `?v={version}` on static assets; SSR has no SW issue |
| F7 | **rollback_or_restore** — schema migration partially applied | Each migration in own Alembic revision; reversible `down()` for every `up()` |
| F8 | **monday_morning_user_state** — long weekend + cron drift | Migrations idempotent; data still readable in old views during transition |
| F9 | **warsaw_missing_data** | JustifiedNotApplicable — Forge has no Warsaw dependency |

**Empty FAILURE SCENARIOS = explanation needed:** none here; all 8 applicable scenarios mitigated, F9 justified.

Cross-ref §14: F2 binds to B.3 (already implemented); F4 introduces a new dependency (RBAC scaffold) flagged in Step 6.

---

## §5 Step-by-step phases (Step 5, §1 Implementation order)

Each step below: artifact + evidence + ExitGate (§12).

### §5.1 Step 1 — Schema migrations (task #26)

**Artifact:** `platform/migrations/versions/2026_04_26_phase1_redesign.py` (Alembic revision).

**Contents (after ADR-028 ratification + revisions; see `migrations_drafts/2026_04_26_phase1_redesign.sql`):**
- `CREATE TYPE epistemic_tag AS ENUM (6 closed values per ADR-028 D2 revised)`
- `ALTER TABLE acceptance_criteria ADD COLUMN epistemic_tag epistemic_tag NULL`
- `ALTER TABLE decisions ADD COLUMN epistemic_tag epistemic_tag NULL`
- `CREATE TABLE alternatives (decision_id FK, position SMALLINT, text TEXT, src TEXT NULL, blocks_count INT, task_ref FK NULL, impact_deltas JSONB, rejected_because TEXT NULL)` — JSONB validated by Pydantic discriminated union per ADR-028 D3 revised
- `CREATE TABLE side_effect_map (id, decision_id FK, kind TEXT, owner TEXT NULL, evidence_set_id FK NULL, blocking BOOLEAN, impact_deltas JSONB NULL)`
- `CREATE TABLE cascade_dod_item (id, objective_id FK, position SMALLINT, text TEXT, signed_by TEXT NULL, signed_at TIMESTAMPTZ NULL)` — composite signed_by/signed_at NULL ↔ NOT NULL CHECK
- `CREATE TABLE kill_criteria_event_log (id, objective_id FK NULL, decision_id FK NULL, task_id FK NULL, kc_code VARCHAR(8) CHECK IN K1..K6, fired_at TIMESTAMPTZ, reason TEXT, evidence_set_id FK NULL)` — at-least-one-ref CHECK
- `CREATE TABLE trust_debt_snapshot (id, project_id FK, computed_at TIMESTAMPTZ, value NUMERIC(10,4), decomposition JSONB NULL)`
- `ALTER TABLE objectives ADD COLUMN stage VARCHAR(8) NULL CHECK (stage IS NULL OR stage IN ('KICKOFF','PLAN','EXEC','VERIFY'))` — REVISED from SMALLINT per ADR-028 D4
- `ALTER TABLE objectives ADD COLUMN autonomy_pinned VARCHAR(8) NULL CHECK (autonomy_pinned IS NULL OR autonomy_pinned IN ('L0','L1','L2','L3'))` — `autonomy_optout BOOLEAN` retained (synthesised view-layer)

**Evidence:** [ASSUMED] this delta covers redesign mocks — verified by closing-set grep in §1.

**ExitGate G_5.1:** `psql --dry-run -f migrations_drafts/2026_04_26_phase1_redesign.sql` runs without error on a clean DB; `down()` (§99) reverses it; `pytest tests/migrations/` passes including the Pydantic discriminated-union round-trip property test (`test_impact_delta_round_trip.py`); §101 verification queries return expected counts. **All four sub-gates are deterministic** — they constitute the §A.5 distinct-actor check pending task #28's full pipeline.

**Status:** UNBLOCKED — U.2, U.3, U.4 closed via ADR-028 (revised). Migration runs on dev DB after `alembic` baseline is taken (separate concern; out of Phase 1 scope; tracked in task #28 deterministic gate pipeline).

### §5.2 Step 2 — ADR-028 stack decision (task #25)

**Artifact:** `platform/docs/decisions/ADR-028-frontend-stack.md`.

**Status field options:** PROPOSED → RATIFIED.

**Required content:** §3 above + alternatives + decision + consequences + reversal cost.

**ExitGate G_5.2:** ADR-028 RATIFIED 2026-04-25. Distinct-actor: user, `[ASSUMED: accepted-by=user]` per CONTRACT §B.2. **U.5 closed**. Long-term substitute (deterministic CI gates) is task #28.

### §5.3 Step 3 — DashboardView SSR (task #27)

**Artifact:** `platform/app/templates/dashboard.html` + `platform/app/api/ui.py` route handler.

**Contents (per `efcace3c_application-javascript.txt`):**
- HERO panel: trust-debt + active-K6 count + open-Decisions badge
- M1–M7 KPI grid (read from view-layer aggregations over `llm_calls`, `executions`, `decisions`)
- K1–K6 panel: GateRegistry-rule-fired counts (last 7d)
- Objectives list with epistemic-tag pills, autonomy_pinned badge, stage marker

**ExitGate G_5.3:** GET `/dashboard` returns HTTP 200 on live platform, all 4 panels render with real data (not stubs), HTMX partial refresh (`hx-trigger="every 30s"`) updates trust-debt without full reload.

**Status:** BLOCKED until G_5.2 RATIFIED (G_5.2 is approval gate per §7).

### §5.4 Step 4 — ObjectiveView 9-tab extension

**Artifact:** Extension of `platform/app/templates/objective_detail.html` from current 4 tabs to 9 tabs (Overview, CGAID, SideEffects, DoD, Decisions, AC, KR, Tasks, Sources).

**ExitGate G_5.4:** Each tab renders with non-stub data; CGAID tab reads from `alternatives` table; SideEffects tab reads from `side_effect_map`; DoD tab reads from `cascade_dod_item`.

### §5.5 Step 5 — Audit + Causal + Settings + Billing routes

**Artifact:** 4 new route handlers + 4 new templates.

**ExitGate G_5.5:** All 4 routes return 200; pixel-fidelity to redesign mocks within ±10% (visual diff acceptable).

### §5.6 Step 6 — RBAC scaffold for `autonomy_pinned`

**Artifact:** `app/middleware/rbac.py` + `@require_role('steward')` decorator on autonomy mutation endpoints.

**ExitGate G_5.6:** Non-Steward POST to `/settings/autonomy/...` returns 403 in integration test.

**Triggered by F4 (§4).** Without this, mitigation of F4 is fictional.

---

## §6 UNKNOWN list — STOP table (§6 STOP rule)

Per AntiShortcutSound §6: `U ≠ ∅ ⇒ G_8 = false` for any phase whose gate depends on U.

**Status as of 2026-04-25 ratification:**

| ID | UNKNOWN | Resolution | Closed? |
|---|---|---|---|
| U.1 | Stack: SSR-only / SPA / Hybrid | ADR-028 D1 (SSR-only + design_canonical companion) | **CLOSED** |
| U.2 | epistemic_tag enum exact values + extensibility | ADR-028 D2 revised: 6 closed values (4 mock + EMPIRICALLY_OBSERVED + TOOL_VERIFIED) | **CLOSED** |
| U.3 | side_effect_map.impact_deltas JSONB schema | ADR-028 D3 revised: Pydantic discriminated union per dimension | **CLOSED** |
| U.4 | objective.stage enum shape | ADR-028 D4 revised: VARCHAR(8) + CHECK IN ('KICKOFF','PLAN','EXEC','VERIFY') | **CLOSED** |
| U.5 | Distinct-actor reviewer for ADR-028 | `[ASSUMED: accepted-by=user]` + task #28 long-term substitute | **CLOSED** (ASSUMED, not CONFIRMED) |
| U.6 | Push branch backup | Approved; MR creation deferred to next batch | **CLOSED** |

All §6 STOP conditions cleared. Tasks #26 (DRAFT migration done), #27 (DashboardView) UNBLOCKED for downstream execution gated only by §A.5 deterministic checks (alembic baseline + migration apply on dev DB).

---

## §7 Approval gate (§7) — between Plan and Implementation

**Pre-implementation predicate G_approve:**

```
G_approve =
  (this plan reviewed by user)
  ∧ (ADR-028 RATIFIED by distinct actor)
  ∧ (U.1 ∪ U.2 ∪ U.3 ∪ U.4 = ∅)
  ∧ (visible-Skip set V_S documented in §0)
```

Until `G_approve = true`, no code lands for tasks #26 / #27. Tasks #24 (this doc) and #25 (ADR-028) produce only DRAFT artefacts — they advance the plan, they do not implement it.

[ASSUMED] User-as-reviewer satisfies "distinct actor" provided U.5 explicitly identifies them in writing. **Consequence if wrong:** if a separate reviewer is required, ratification stalls.

---

## §8 Pred-vs-Obs cross-check (§8) — to be run at Phase-1 EXIT

The plan claims:
- **5 new tables** ⇒ verified by counting `CREATE TABLE` in the merged Alembic revision.
- **4 new columns** ⇒ verified by `ALTER TABLE ... ADD COLUMN` count.
- **1 new enum** ⇒ verified by `CREATE TYPE` count.
- **4 SSR routes** ⇒ verified by counting new entries in `app/api/ui.py`.

**Tolerance:** `|Δ| / Pred ≤ 0.5`. If, e.g., we end up with 7 tables instead of 5 (`|Δ|/Pred = 0.4`), that is within tolerance. If we end up with 2 tables (`|Δ|/Pred = 0.6`), §8 EXPLANATION REQUIRED — same path used in SESSION_STATE.md §3 for the 75-vs-33 .status= prediction error.

**Where this lives:** appended to SESSION_STATE.md §3 at Phase 1 EXIT.

---

## §9 Self-check honesty (§13)

Run this checklist at every phase boundary:

- [ ] All 4 visible-Skip slots U.1–U.4 either CLOSED or §6-STOPped (no silent fills)?
- [ ] Every CONFIRMED claim above re-verified by a fresh grep / curl / pytest run?
- [ ] No CONFIRMED was promoted from ASSUMED without an explicit re-verification step?
- [ ] No "completed" task without DID/DID NOT/CONCLUSION block?
- [ ] No new entities introduced that bypass GateRegistry?

**Anti-self-bias:** when a sub-step is "almost done", treat it as IN_PROGRESS. The §3 75-vs-33 prediction error in this session shows what happens when prediction error of 0.5+ goes unflagged.

---

## §10 Impact closure (§10)

`Closure(redesign_integration) = deps ∪ consumers ∪ side_effects ∪ ordering`

- **deps:** GateRegistry (P7), CausalGraph (B.3), ContractSchema (E.1) — none modified, all consumed read-only.
- **consumers:** 27 existing Jinja templates — `objective_detail.html` extended; all others unchanged. CLI surface (5 commands) unchanged.
- **side_effects:** Database — 5 new tables (additive, no DROP); existing column `objectives.autonomy_optout` retained for transition (deprecation in next phase).
- **ordering:** migrations apply BEFORE app starts (Alembic head) → BEFORE template rendering reads new columns → BEFORE user navigates to redesign routes.

**Forbidden short-circuits:** no template reads `objectives.stage` before migration head; CI-style smoke test verifies (`select stage from objectives` succeeds before any `/dashboard` request).

---

## §11 Cross-references (§14 traceability)

```
This plan
├── reads SESSION_STATE.md §1.8 (redesign analysis) ──> §1 Pred
├── reads UX_DESIGN.md §2 (current 3-page IA) ─────── > §1.1 surfaces table
├── reads MVP_SCOPE.md §L4 (developer-only) ───────── > §3 Decision drivers
├── reads FORMAL_PROPERTIES_v2.md (P7, P16, P21) ──── > §10 Impact closure deps
├── reads CONTRACT.md change discipline ─────────────> §3 Decision drivers
└── triggers
    ├── ADR-028 (task #25) ─────────────────────────> resolves U.1, U.2, U.3, U.4
    ├── Migration 2026_04_26_phase1 (task #26) ─────> implements §5.1 G_5.1
    ├── DashboardView (task #27) ───────────────────> implements §5.3 G_5.3
    ├── ObjectiveView extension ────────────────────> implements §5.4 G_5.4
    ├── 4 new routes ──────────────────────────────> implements §5.5 G_5.5
    └── RBAC scaffold ─────────────────────────────> implements §5.6 G_5.6
```

**Causal chain integrity:** every step has at least one upstream and one downstream cross-ref. No orphan steps.

---

## §12 ExitGate per phase (§12)

| Phase | ExitGate predicate | Test |
|---|---|---|
| Plan ratification | `G_approve` (§7) | manual review trail |
| Schema | `G_5.1` | alembic up + down + tests/migrations green |
| ADR | `G_5.2` | distinct-actor sign-off recorded |
| Dashboard | `G_5.3` | 4 panels render real data on live |
| Objective tabs | `G_5.4` | each of 9 tabs returns 200 |
| Other routes | `G_5.5` | 4 routes return 200 |
| RBAC | `G_5.6` | 403 in integration test |
| Phase 1 EXIT | all of above ∧ §8 cross-check tolerance met | composite |

---

## §13 Visible-Skip slots (§16)

The plan deliberately defers the following — these are visible Skips, not silent omissions:

| Skip | Why deferred | Re-entry condition |
|---|---|---|
| Compliance dashboard polish | MVP scope is developer-only | Phase 2 entry |
| Executive billing analytics | Phase 3 scope | Phase 3 entry |
| Pixel-perfect SPA causal-graph drag | High effort, low MVP value | If user complains in 2 design-partner runs |
| Trust-debt formula ratification | Formula is invented in mock; needs Steward review | Steward sign-off captured in `cascade_dod` |

Each Skip's re-entry condition is testable. No Skip is "we'll get to it" without a trigger.

---

## §14 Steel-man — what if this plan is wrong?

**Strongest counter:** "Picking SSR-only locks Forge into a stack that can't deliver the live-update / drag interactions the redesign was designed for. By Phase 2 we'll be re-porting under pressure — that's the worst time to swap stacks."

**Counter-counter:** Phase 2 is at least 4 weeks out [ASSUMED — based on commit cadence]. ADR-028 explicitly enumerates the reversal cost and a re-entry trigger ("if 2 design-partner runs report blocked-by-interactivity, escalate to Hybrid"). Reversal is documented; cost is bounded.

**If the steel-man holds:** the cost of the wrong stack call is +10 person-days re-port, not a project halt. Compared to upfront SPA cost of 15-25 PD with no validated need, the bet is asymmetric in favour of SSR-first.

[ASSUMED] reversal cost ≤ 10 PD. **If wrong:** plan may need a hybrid approach earlier than Phase 2.

---

## §15 Approval block

This document does not become NORMATIVE until:

1. User signs §7 G_approve.
2. ADR-028 is RATIFIED.
3. U.1–U.4 closed.

Until then: status = **DRAFT**. Tasks #26, #27 STOP per §6.
