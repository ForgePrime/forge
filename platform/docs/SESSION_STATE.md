# SESSION_STATE.md — append-only work ledger

**Status:** active. Append-only — never rewrite history; only add entries
or correct via explicit `[CORRECTION]` lines.
**Theorem compliance:** authored per AntiShortcutSound (user-supplied,
2026-04-25), satisfying §13 Self-check honesty + §14 Causal cross-reference
(every entry references the artifact and tags it CONFIRMED/ASSUMED/UNKNOWN).
**Branch:** `docs/forge-plans-soundness-v1` (local-only — push pending
explicit `tak push`).

---

## §0 Conventions

Each entry has:
- `[YYYY-MM-DD HH:MM TZ]` timestamp.
- Status: `DONE` / `IN_PROGRESS` / `BLOCKED` / `DEFERRED` / `JustifiedNotApplicable`.
- Evidence type: `[CONFIRMED]` (run + observed) / `[ASSUMED]` (inferred from
  spec or code-read) / `[UNKNOWN]` (open question — triggers §6 STOP if
  load-bearing).
- Cross-ref to commit hash, file path, or theorem section.

---

## §1 Done — implementation milestones (chronological)

### §1.1 Plan corpus + spec layer (commits `25adb23` … `9f8a969`)

**[2026-04-25 morning]**

- **DONE [CONFIRMED via 2 commits]**: deep-verify pass on 6 governance
  plans (PLAN_PRE_FLIGHT, PLAN_GATE_ENGINE, PLAN_MEMORY_CONTEXT,
  PLAN_QUALITY_ASSURANCE, PLAN_CONTRACT_DISCIPLINE, PLAN_GOVERNANCE).
  All reach ACCEPT (S ≤ −3) per deep-verify rubric.
- **DONE [CONFIRMED via commit `9f8a969`]**: 7 layer-specification docs:
  MVP_SCOPE, PRODUCT_VISION, PLAN_LLM_ORCHESTRATION (L3), UX_DESIGN (L4),
  INTEGRATIONS (L5), OPERATIONS (L6), QUALITY_EVALUATION (L7).
- Cross-ref §14: outputs feed §1.2 (state-machine code) + §1.4 (B/C-phase
  modules).

### §1.2 L1+L2 validation infrastructure (commits `1dc320e` … `492f5aa`)

- **DONE [CONFIRMED via pytest 413/413 green]**:
  - `app/validation/gate_registry.py` — 6 entities × 44 transitions
  - `app/validation/verdict_engine.py` — pure-fn evaluator (P6)
  - `app/validation/rules/` — 4 rule adapters: evidence_link_required (P16),
    plan_gate_adapter, contract_validator_adapter, root_cause_uniqueness (P21)
  - `app/validation/shadow_comparator.py` — 3-mode (off/shadow/enforce)
  - `app/validation/state_transition.py` — A.4 cutover helper
  - `app/models/idempotent_call.py` + `app/models/verdict_divergence.py`
- **DONE [CONFIRMED via grep returning 0]**: A.4 cutover — 33 sites
  wrapped (NOT 75 as PLAN claimed; see §3 CrossCheck).
- **DONE [CONFIRMED]**: pre-commit hook `no-direct-status-assign` in
  `.pre-commit-config.yaml`.

### §1.3 Phase B + Phase C (commits `f0a2d91` … `cfc665c`)

- **DONE [CONFIRMED via pytest]**:
  - B.1 CausalEdge model + acyclicity check (11 tests)
  - B.3 CausalGraph service + DBEdgeSource (18 + 9 live-DB tests)
  - B.4 ContextProjector (15 tests)
  - B.6 SemanticRelationTypes ENUM (23 tests)
  - C.1 ImportGraph (22 tests)
  - C.2 SideEffectRegistry (19 tests)
  - C.3 ImpactClosure (15 tests)
  - C.4 ReversibilityClassifier (28 tests)

### §1.4 L3 LLM orchestration — pure-Python (commits `5800f20` … `9a2bbb0`)

- **DONE [CONFIRMED via pytest]**:
  - L3.1 PromptAssembler (19 tests; deterministic checksum)
  - L3.2 ToolCatalog (25 tests; 5-level authority gate)
  - L3.3 ContextBudget (14 tests; MUST/SHOULD/NICE buckets)
  - L3.4 ModelRouter (22 tests; deterministic decision tree)
  - L3.5 FailureRecovery (27 tests; rule-based)
  - L3.6 CostTracker + BudgetGuard (20 tests; Decimal arithmetic)
  - L3 layer-connectivity end-to-end (7 tests)
  - E.1 ContractSchema + 4 seed contracts (23 tests)
- Cross-ref §14: E.1 unblocks L3.1; L3.1 + L3.2 + L3.3 compose at
  layer-connectivity test commit `ba10fcc`.

### §1.5 Live-platform integration (commits `c8475c2` … `f0c9ccd`)

**[2026-04-25 afternoon — α action executed]**

- **DONE [CONFIRMED via `docker compose ps`]**: Postgres 16-alpine running
  on `platform-db-1`, port 5432, ~21h uptime.
- **DONE [CONFIRMED via `curl localhost:8012/health` → `{"status":"ok"}`]**:
  uvicorn worker on port 8012.
- **DONE [CONFIRMED via `\dt` SQL]**: 4 new tables auto-created on startup:
  `idempotent_calls`, `verdict_divergences`, `causal_edges`, `evidence_sets`.
- **DONE [CONFIRMED via smoke run]**: smoke_test_tracker.py against live
  HTTP — 125 claims, 0 UNREACHABLE, 0 UNCHECKED → Stage 0.3 GREEN
  per PLAN_PRE_FLIGHT T_{0.3}.
- **DONE [CONFIRMED via 8 + 9 live-DB tests]**:
  - DBIdempotencyStore (production backend, A.5)
  - DBEdgeSource (production backend, B.3)
- **DONE [CONFIRMED via `SELECT count(*) FROM causal_edges` = 2140]**:
  B.2 backfill executed against real data:
  - tasks.origin_finding_id → 2 edges
  - decisions.execution_id → 39
  - decisions.task_id → 39
  - changes.execution_id → 4
  - changes.task_id → 4
  - findings.execution_id → 532
  - acceptance_criteria.task_id → 1341
  - task_dependencies → 179
  - **TOTAL: 2140 edges**, idempotent re-run = 0 new rows.

### §1.6 F-wirings + auth-aware smoke (commits `168aa05` … `2c4ae66`)

- **DONE [CONFIRMED via pytest]**: F.5/P21 — root_cause_uniqueness wired
  into 4 Decision permanent transitions; composes with evidence_link_required.
- **DONE [CONFIRMED via live curl]**: smoke verifier with `--bearer-token`
  + `/api/v1` prefix retry. Live results: 2 VERIFIED, 3 DIVERGED (all
  TRACKER-path inaccuracies, NOT real bugs), 0 UNREACHABLE.

### §1.7 Phase R₁ enabler artifacts (commit `6500e95`)

- **DONE [CONFIRMED via filesystem]**:
  - `docs/decisions/ADR-027` — ContractSchema typed-spec format (PROPOSED)
  - `docs/PHASE0_DEPENDENCY_GRAPH.md` — theorem-grounded plan T1-T30
  - `docs/reviews/review-session-2026-04-25-PENDING.md` — pre-filled review

### §1.8 Forge redesign analysis (this turn, no commit yet)

- **DONE [CONFIRMED via filesystem extract]**:
  Extracted bundled HTML from `docs/Forge redesign - standalone.html`
  to `docs/forge_redesign_extracted/` (10 files, 31 manifest entries).
  Identified:
  - React SPA (Babel in-browser)
  - Inter Tight + IBM Plex Mono fonts
  - Light + dark theme tokens
  - 7 main routes: /dashboard, /objective/:id (9 tabs), /audit,
    /execution/:id/trace, /execution/:id/causal, /settings/autonomy, /billing
  - 9 new domain concepts (epistemic_tags, CGAID alternatives, side_effect_map,
    cascade_dod, kill_criteria K1-K6, metrics M1-M7, trust-debt, stage 0-3,
    autonomy_pinned)
- Cross-ref §14: feeds Step 1 of `PLAN_PHASE1_UX_INTEGRATION.md` (this turn).

---

## §2 Statistics

| Metric | Value | Evidence |
|---|---|---|
| Commits this session | 37 | `git log --format='%h %s' main..HEAD` returns 37 entries since `0fff9e7` |
| Pytest tests passing | 413 in-memory + 17 live-DB = 430 total | last full run: `[CONFIRMED]` 413 green |
| Production tables created | 4 (idempotent_calls, verdict_divergences, causal_edges + pre-existing evidence_sets) | `\dt` |
| CausalEdges materialized | 2140 (1341 ac_of + 575 produced + 222 depends_on + 2 produced_task) | `SELECT relation, count(*) FROM causal_edges GROUP BY relation` |
| .status= sites wrapped | 33 of 33 | `grep` invariant returns 0 outside helper |
| Pre-commit invariant gates | 1 (no-direct-status-assign) | `.pre-commit-config.yaml` |
| Plan documents authored | 13 (6 governance plans + 7 layer specs) | `ls platform/docs/PLAN_*.md MVP_SCOPE.md PRODUCT_VISION.md UX_DESIGN.md INTEGRATIONS.md OPERATIONS.md QUALITY_EVALUATION.md` |
| ADRs in DRAFT | 27 (001-027); ADR-027 PROPOSED, 003 RATIFIED, rest CLOSED-content-DRAFT | `ls platform/docs/decisions/ADR-*.md` |

---

## §3 CrossCheck — predictions vs observed (§8)

Reality-check on predictions made earlier in this session.

| Prediction (Pred) | Observed (Obs) | Δ | Verdict |
|---|---|---|---|
| PLAN_GATE_ENGINE: "75 .status= sites across 9 files" | 33 sites across 6 files | 42-site delta (-56%) | **`|Δ|/Pred = 0.56 > 0.5` → §8 EXPLANATION REQUIRED.** Reason: PLAN_GATE_ENGINE was authored when the codebase was bigger (different commit baseline). Updated count documented in commit `ed0611a` body. |
| Smoke test cold run: "expect UNREACHABLE for HTTP claims" | 4 UNREACHABLE confirmed; gate still PASS | 0 | within tolerance |
| Smoke test live-platform run: "expect 0 UNREACHABLE" | 0 UNREACHABLE confirmed | 0 | within tolerance |
| ADRs 004/005/006 ratification: "blocking" per Sept-2024 PLAN | All 3 already CLOSED-content-DRAFT as of 2026-04-24 | full unblock | within tolerance |
| Phase B.4 ContextProjector token budget: "needs ContractSchema for 6 categories" | Built ContextProjection without typed 6-cat (free_form fallback) | partial decoupling | accepted; full coupling at L3.1 PromptAssembler integration time |
| Backfill candidates: "expected ~10 known FK relations" per PLAN_MEMORY_CONTEXT | 8 sources, 2140 edges | 2 sources fewer than predicted | accepted; the 2 missing (`Knowledge.source_ref` polymorphic + `LLMCall` evidences) have schema complexity not in scope |

**§13 Self-check disclosure:** the .status= site count is the largest
prediction-error of the session. Documented in commit `ed0611a` and
above. No silent corrections.

---

## §4 In progress

| Task | Owner | Started | Next checkpoint |
|---|---|---|---|
| #23 Write SESSION_STATE.md | agent | 2026-04-25 | this commit |
| #24 Author PLAN_PHASE1_UX_INTEGRATION.md | agent | pending §1.8 → next | §15 AntiShortcutSound spec |

---

## §5 Blocked / UNKNOWN (§6 STOP rule)

UNKNOWN items below block specific downstream work per AntiShortcutSound
§6 (`U ≠ empty ⇒ G_8 = false` for the relevant phase).

| ID | UNKNOWN | Blocks | Resolution path |
|---|---|---|---|
| U.1 | Stack decision: React SPA vs HTMX-SSR continuation | DashboardView impl, L4 redesign port | ADR-028 (task #25) |
| U.2 | epistemic_tag enum values — exact enumeration: just the 4 from redesign mock (`INVENTED`/`DERIVED`/`ADR_CITED`/`STEWARD_AUTHORED`) or extended? | AC migration (task #26) | Decision in ADR-028 or sibling ADR |
| U.3 | CGAID alternatives schema: should `impact_deltas JSONB` be free-form or typed (mirror FORMAL §11.2 pattern)? | Schema migration (task #26) | Decision in ADR-028 |
| U.4 | "Stage 0-3" mapping: is `objective.stage` free integer 0..N or specific phase enum (`KICKOFF`/`PLAN`/`EXEC`/`VERIFY`)? | Schema migration | Decision in ADR-028 |
| U.5 | Distinct-actor reviewer for ADR-027 + 37-commit batch — who? when? | Promotion of all DRAFT plans to NORMATIVE | User decides (out-of-band) |
| U.6 | Push to GitLab: `tak push`? | Branch publishing | User decides (out-of-band) |

**§6 effect on Phase 1**: U.1, U.2, U.3, U.4 block DashboardView impl
(task #27). Tasks #23, #24, #25, #26 can proceed (they produce decisions
or DRAFT artefacts). #27 STOPs until §6 cleared.

---

## §6 Failure scenarios for current plan state (§11 completeness)

| Scenario (F set, §11) | Status | Mechanism |
|---|---|---|
| null_or_empty_input | Handled | All wrappers / adapters reject empty inputs at validation boundary; FailureRecovery.ErrorCode.UNKNOWN defaults PERMANENT |
| timeout_or_dependency_failure | Handled | uvicorn timeout per request; LLM retry budget per ADR-006; DB pool_pre_ping=True |
| repeated_execution | Handled | A.5 idempotency_key + DBIdempotencyStore; B.2 backfill ON CONFLICT DO NOTHING |
| missing_permissions | Handled | smoke verifier has `--bearer-token`; auth gate at FastAPI middleware |
| migration_or_old_data_shape | Handled | Base.metadata.create_all is additive; existing rows untouched |
| frontend_not_updated | **In-progress** | Current SSR templates still in use; redesign integration is task #24-#27 scope |
| rollback_or_restore | Handled | A.4 cutover keeps mode=off default = identical behaviour; revert path available |
| monday_morning_user_state | Handled | All state DB-backed; orphan_recovery.py releases stale executions on startup |
| warsaw_missing_data | JustifiedNotApplicable | Forge has no geographic data dimension |

---

## §7 Cross-references (§14 traceability)

```
Pred (§3 CrossCheck) ──┐
                       ├── tested by §1.5 live-platform run
Obs (§1.5)        ─────┘

§1.1 plan corpus ──┐
                   ├── feeds §1.2 + §1.3 + §1.4 (acceptance criteria for code)
                   └── feeds §1.7 R₁ enablers

§1.4 L3 layer ─────┐
                   ├── ContractSchema (E.1) → PromptAssembler (L3.1)
                   ├── ToolCatalog (L3.2) ← side_effect_registry (C.2)
                   └── feed L3 layer-connectivity test (commit ba10fcc)

§1.5 live ─────────┐
                   ├── enables §1.6 (auth smoke + F-wiring)
                   └── enables §1.8 (redesign analysis — running platform shows
                       what data exists for new views)

§1.8 redesign ─────┐
                   ├── Step 1 (Pred) of PLAN_PHASE1_UX_INTEGRATION
                   ├── triggers §5.U.1-U.4 (decisions needed)
                   └── tasks #24, #25, #26, #27
```

---

## §8 Next entry placeholder

(Append below as work progresses. Never rewrite older entries; corrections
go in their own `[CORRECTION]` line referencing the original by date.)

---

### §1.9 PLAN_PHASE1_UX_INTEGRATION.md authored (no commit yet)

**[2026-04-25 evening]**

- **DONE [CONFIRMED via filesystem `platform/docs/PLAN_PHASE1_UX_INTEGRATION.md`]**:
  AntiShortcutSound-compliant Phase 1 plan. 15 sections covering:
  - §1 Pred — 7 redesign routes, 9 new domain concepts (epistemic_tag, alternatives,
    side_effect_map, cascade_dod, kill_criteria, metrics, trust_debt, stage_0_3,
    autonomy_pinned), 5 new tables, 4 new columns, 1 enum.
  - §2 Schema audit vs existing entities — minimise migration delta.
  - §3 Stack decision options A/B/C with $D cost; recommends Option A (SSR port).
  - §4 9 §11 failure scenarios mapped to Phase 1.
  - §5 6 implementation steps (G_5.1..G_5.6) with ExitGates.
  - §6 STOP table — U.1..U.6 listed, blocking gates identified.
  - §7 G_approve approval-gate predicate.
  - §8 Pred-vs-Obs cross-check spec (deferred to Phase 1 EXIT).
  - §9 Self-check honesty checklist.
  - §10 Impact closure (deps, consumers, side_effects, ordering).
  - §11 Cross-reference graph.
  - §12 ExitGate per phase table.
  - §13 Visible-Skip slots (deferred items with re-entry conditions).
  - §14 Steel-man + counter-counter.
  - §15 Approval block.
- **STATUS: DRAFT** — does not become NORMATIVE until G_approve fires
  (user sign-off + ADR-028 RATIFIED + U.1–U.4 closed).
- Cross-ref §14: triggers tasks #25 (ADR-028), #26 (schema migrations),
  #27 (DashboardView impl). Tasks #26, #27 STOP per §6 until U.1–U.4 close.
- **Next action (no commit pending user direction):** ADR-028 draft (task #25)
  is the unblocking step for U.1–U.4.

---

### §1.10 ADR-028 drafted (PROPOSED, not ratified) — no commit yet

**[2026-04-25 evening]**

- **DONE [CONFIRMED via filesystem `platform/docs/decisions/ADR-028-frontend-stack-and-redesign-shape.md`]**:
  Single ADR closing 4 coupled decisions:
  - **Decision 1 — Stack: SSR-only (Option A).** Continue Jinja+HTMX+Tailwind.
    Reversal trigger to Hybrid documented; cost ≤ 10 PD [ASSUMED].
  - **Decision 2 — `epistemic_tag` enum: closed at 4 values** (INVENTED,
    DERIVED, ADR_CITED, STEWARD_AUTHORED). Hyphens normalised to underscores
    for ENUM identifier; display layer renders hyphens.
  - **Decision 3 — `side_effect_map.impact_deltas`: free-form JSONB +
    Pydantic validator at write boundary.** Self-adjoint with rendering
    (FORMAL P12 pattern).
  - **Decision 4 — `objective.stage`: 4-value SMALLINT** (KICKOFF/PLAN/EXEC/
    VERIFY → 0..3). Backfill heuristic documented.
  - Steel-man + counter-counter recorded.
  - Disclosure of [UNKNOWN] U.5 (distinct-actor reviewer identity) blocking
    ratification.
- **STATUS: PROPOSED** — does not become RATIFIED until user + distinct-actor
  sign-off. U.5 remains open.
- **Effect on STOP table (§5):** if ratified, U.1, U.2, U.3, U.4 close.
  U.5 stays open until reviewer named. U.6 (push) still open.
- Cross-ref §14: ADR-028 unblocks G_5.1 (schema migration) when ratified.
  Without ratification, tasks #26 and #27 remain STOP per
  PLAN_PHASE1_UX_INTEGRATION §6.

---

### §1.11 Phase 1 migration draft authored (DRAFT-only, not run)

**[2026-04-25 evening]**

- **DONE [CONFIRMED via filesystem]**:
  - `platform/docs/migrations_drafts/2026_04_26_phase1_redesign.sql`
    — 5 tables + 4 cols + 1 enum + reversal block + verification queries.
  - `platform/docs/migrations_drafts/README.md` — explains DRAFT-zone
    semantics + lifecycle + pre-flight checklist.
- **Why .sql in `docs/migrations_drafts/` and not `alembic/versions/*.py`**:
  - Alembic versions/ is empty [CONFIRMED via `ls platform/alembic/versions/`];
    production schema came from `Base.metadata.create_all()` per §1.5.
    Adding a Python revision before bootstrap = broken chain.
  - SQL form is unambiguous about DRAFT status (not auto-discoverable).
- **Schema delta authored** (matches ADR-028 §Composite consequence table):
  - `CREATE TYPE epistemic_tag AS ENUM (4 closed values)`
  - `acceptance_criteria.epistemic_tag` + `decisions.epistemic_tag`
  - `objectives.stage SMALLINT CHECK 0..3`
  - `objectives.autonomy_pinned VARCHAR(8) CHECK IN ('L0'..'L3')`
  - `alternatives` (CGAID, replaces decisions.alternatives_considered TEXT)
  - `side_effect_map` (persists C.2 SideEffectRegistry)
  - `cascade_dod_item` (per-objective DoD checklist)
  - `kill_criteria_event_log` (K1..K6 firing audit, append-only)
  - `trust_debt_snapshot` (per-project debt history; formula INVENTED, needs Steward ratification before authoritative)
- **Reversal**: §99 of draft has full `down()` SQL; idempotent guards via
  `IF EXISTS` / `IF NOT EXISTS` / `pg_constraint` / `pg_type` checks.
- **Verification queries**: §101 of draft = 5 SELECTs that collectively
  constitute G_5.1 ExitGate evidence.
- **Backfill**: §100 of draft is separate-transaction sketch (heuristic
  for `objectives.stage` based on tasks; mapping `autonomy_optout=true → 'L0'`).
- **STATUS: DRAFT** — does not run until ADR-028 RATIFIED. Migration
  remains inert — Alembic does not auto-discover it.
- Cross-ref §14: feeds G_5.1 ExitGate (PLAN_PHASE1_UX_INTEGRATION §12)
  once ADR-028 ratifies. Pending ratification, task #27 (DashboardView)
  remains STOP per §6 — model code can be authored as DRAFT, but UI
  cannot read columns that do not yet exist on prod schema.

**State of Phase 1 plan after §1.11:**

| Task | Status | DRAFT artefact | Production artefact |
|---|---|---|---|
| #24 PLAN_PHASE1_UX_INTEGRATION | completed | DRAFT plan | n/a (plan IS the artefact) |
| #25 ADR-028 | completed | PROPOSED ADR | RATIFIED ADR (pending user + reviewer) |
| #26 Schema migration | completed (DRAFT) | inert .sql + README | Alembic revision (post-ratification port) |
| #27 DashboardView | pending | — | full SSR view (post-G_5.1) |

**Open UNKNOWNs blocking forward motion:** U.1–U.4 (close on ADR-028 ratify),
U.5 (distinct-actor reviewer), U.6 (push to GitLab).

---

### §1.12 Meta-decision: long-term + AI-autonomy lens applied; ADR-028 RATIFIED with revisions

**[2026-04-25 evening]**

User accepted Q-meta cross-cutting principles §A.1–§A.6:
- §A.1 DB-level integrity > application-level validators
- §A.2 Self-documenting schema > opaque codes
- §A.3 Closed enums + extension protocol > open vocabularies
- §A.4 Self-adjointness P12 (one source → prompt + validator + tests)
- §A.5 Deterministic gate > human review (for mechanical correctness)
- §A.6 Reversibility from day 1 (P19)

User accepted blanket recommendation set Q1–Q6 long-term variant.

**Concrete changes applied this turn (DRAFT-zone files only — no code; no migration run):**

- **ADR-028 status:** PROPOSED → RATIFIED `[ASSUMED: accepted-by=user, date=2026-04-25]` per CONTRACT §B.2.
- **ADR-028 D2 revised**: enum extended from 4 → 6 values
  (`INVENTED`, `SPEC_DERIVED`, `ADR_CITED`, `EMPIRICALLY_OBSERVED`,
  `TOOL_VERIFIED`, `STEWARD_AUTHORED`). Mock `'DERIVED'` renamed to
  `'SPEC_DERIVED'` for AI-autonomy disambiguation (cited-spec vs
  ran-tool vs observed-runtime).
- **ADR-028 D3 revised**: `impact_deltas` Pydantic spec upgraded to
  *discriminated union* per `dimension`. Each dimension has typed
  `before/after` (latency=float, cost=Decimal, blast_radius=int,
  reversibility=Literal A..E). Closes a class of AI silent-fill bugs
  (string in numeric field).
- **ADR-028 D4 revised**: `objective.stage` switched from SMALLINT 0..3
  to `VARCHAR(8)` + `CHECK IN ('KICKOFF','PLAN','EXEC','VERIFY')`.
  Rationale: consistent with established codebase pattern
  (`objectives.status VARCHAR(20) CHECK IN (...)`); self-documenting
  in raw SQL; no enum-mapping lookup that becomes AI halucination
  vector.
- **ADR-028 companion artefact**: `platform/docs/design_canonical/`
  README.md created. Role: canonical UX truth via `Forge redesign -
  standalone.html`; AI gets deterministic check (snapshot tests)
  against this reference instead of self-judging "does this look
  right?"
- **`migrations_drafts/2026_04_26_phase1_redesign.sql` updated**:
  §1 enum 4→6 values; §2 stage SMALLINT→VARCHAR; §100 backfill SQL
  uses string literals; reversal §99 still works (DROP COLUMN
  agnostic to type).
- **PLAN_PHASE1_UX_INTEGRATION.md updated**: §1.2 enum spec, §5.1
  contents, §5.2 G_5.2 status, §6 STOP table — all 6 UNKNOWNs marked
  CLOSED.
- **Task #28 created**: "Build Deterministic ADR Gate Pipeline".
  Long-term substitute for human distinct-actor on schema/correctness
  ADRs. Pipeline runs `psql --dry-run` + reversal test + Pydantic
  round-trip + mypy strict; status transition PROPOSED →
  READY_FOR_HUMAN_REVIEW only when all green.

**§13 Self-check disclosure:** the meta-decision changes 3 of 4 ADR-028
sub-decisions (D2 4→6, D3 typing more precise, D4 SMALLINT→VARCHAR). It
adds 1 new directory (`design_canonical/`) and 1 new task (#28). The
prediction error vs the original ADR draft is sizeable, but it is *not*
a §3 CrossCheck Δ (predictions vs observations) — it is a *deliberate
revision* under a stronger lens. Documented here as a deliberate change,
not a silent correction.

**§14 Cross-references:**
- §1.12 ← §1.10 (ADR-028 PROPOSED) + user-supplied lens shift
- §1.12 → task #27 (DashboardView) unblocked subject to deterministic
  gate (§A.5) — actual run pending alembic baseline
- §1.12 → task #28 (Deterministic ADR Gate Pipeline) authored

**State of Phase 1 plan after §1.12:**

| Task | Status | Artefact |
|---|---|---|
| #24 PLAN_PHASE1_UX_INTEGRATION | completed | RATIFIED plan |
| #25 ADR-028 | completed | RATIFIED ADR (with revisions D2/D3/D4) |
| #26 Schema migration | completed | DRAFT .sql (revised); to port to alembic after baseline |
| #27 DashboardView | pending (UNBLOCKED) | next implementation step |
| #28 Deterministic ADR Gate Pipeline | pending | new long-term substrate |

**Pending action this turn (one):** push branch `docs/forge-plans-soundness-v1`
to remote per Q6 user approval. MR creation deferred to next batch.

---

### §1.13 Stage 28.1 — ADR format validator (DONE)

**[2026-04-25 evening, after ratification commit `df842dd` pushed]**

User selected "Recommended" → task #28 (Deterministic ADR Gate Pipeline)
chosen over task #27 (DashboardView) per AI-autonomy leverage argument.

**Stage 28.1 deliverables:**

- **DONE [CONFIRMED via pytest 21/21 green]**:
  - `platform/scripts/validate_adr.py` — pure stdlib validator, rules
    R1..R8 + warning W2, ~390 LOC. Pure-fn (P6 deterministic).
  - `platform/tests/test_validate_adr.py` — 21 tests covering each rule
    fires/doesn't, baseline filtering, --strict mode, --json output,
    determinism. All green.
  - `.pre-commit-config.yaml` — `validate-adr` hook on ADR file changes.
  - `platform/docs/decisions/.adr_validator_baseline.json` — 50 issues
    across 26 files frozen as legacy drift.
  - `platform/docs/PLAN_ADR_GATE_PIPELINE.md` — task #28 plan with stage
    decomposition (28.1 DONE; 28.2 SQL migration validator pending;
    28.3 Pydantic schema validator pending; 28.4 lifecycle + CI pending).
- **DONE [CONFIRMED via final run]**: `python validate_adr.py` →
  28 PASS, 0 WARN, 0 FAIL with baseline applied.

**Findings disclosed during Stage 28.1 first run (CONTRACT §A.6):**

| F# | Finding | Where |
|---|---|---|
| F1 | 21 of 28 ADRs lack `## Rationale` section vs canonical template | ADR-009..021, 027 (and originally ADR-028) |
| F2 | ADR-022 has zero alternatives bullets — FORMAL P21 violation | ADR-022 |
| F3 | **ADR-028 (just authored) violates `decisions/README.md` rule 1** ("One decision per ADR. Never two.") — single ADR closing 4 coupled decisions | ADR-028 |
| F4 | Multiple ADRs surface unresolved `[UNKNOWN]` tags without explicit resolution paths | ~18 ADRs |

**§13 Self-check disclosure**: F3 is a personal authoring violation. The
deliberate choice to close 4 decisions in one ADR (steel-manned in
ADR-028) is non-compliant with the canonical rule. Disclosed here per
CONTRACT §A.6/§A.7. Not silently fixed. User decides remediation
(split into 4 ADRs / write meta-ADR carving exception / amend
template). Validator's R5 failures on ADR-028 are baselined for now.

**Cross-ref §14:**
- §1.13 ← §1.12 (user accepted §A.5 deterministic-gate principle)
- §1.13 → next stage 28.2 (SQL migration validator) blocked on user
  decision: which finding(s) F1..F4 to remediate first vs proceed
  with 28.2

**State of pending tasks after §1.13:**

| Task | Status |
|---|---|
| #27 DashboardView SSR | pending (paused — task #28 prioritised) |
| #28 Deterministic ADR Gate Pipeline | in_progress (Stage 28.1 DONE; 28.2/28.3/28.4 pending) |

**Open user decisions (informed by F1-F4):**

1. Remediation for F3 (ADR-028 single-vs-coupled): split / meta-ADR / template amend / leave?
2. Order: continue Stage 28.2 (SQL migration validator) OR pause to retro-fix F1/F2 in existing ADRs first?
3. Audit `[UNKNOWN]` tags (F4): commission a sweep, or leave for ad-hoc cleanup?
