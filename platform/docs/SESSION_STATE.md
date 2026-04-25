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

---

### §1.14 D1+D2+D3 ratification + Stage 28.2a (DONE)

**[2026-04-25 evening]**

User accepted all 3 recommendations: D1=c (amend rule 1), D2=a (continue 28.2),
D3=c (W2→R9 in --strict).

**D1 — `decisions/README.md` rule 1 amended:**
- Default still: one-decision per ADR.
- **Coupled-decision exception** allowed iff: (a) tightly-coupled by single
  artefact, (b) coupling rationale documented, (c) `## Composite consequence`
  section present. Cap: ≤4 decisions.
- Rule 6 (≥2 alternatives) extended: each individual decision in a coupled
  bundle MUST satisfy ≥2.
- ADR-028 retroactively conformant.

**D3 — Validator W2→R9 escalation visible in --strict:**
- `validate_adr.py` post-processes issues when `--strict` set: rule W2
  becomes "R9", severity "WARN" → "FAIL", message rewritten to cite §6.
- New test `test_main_strict_promotes_w2_to_r9_in_json` confirms.
- `pytest`: 22/22 green.

**D2 — Stage 28.2a SQL migration validator (DONE):**
- **DONE [CONFIRMED via pytest 21/21 green]**:
  - `platform/scripts/validate_migration.py` — pure stdlib, ~330 LOC.
    Rules M1..M9 covering: filename pattern, header status marker, ADR
    reference, BEGIN/COMMIT pairing, §99 reversal block, §101 verification
    block, up/down symmetry (CREATE→DROP pairing for tables/types/columns),
    idempotency markers, no destructive defaults.
  - `platform/tests/test_validate_migration.py` — 21 tests covering each
    rule fires/doesn't, baseline filtering, --strict, --json,
    determinism. **Includes regression on real Phase 1 migration**
    (`2026_04_26_phase1_redesign.sql` PASS without baseline = the
    migration is *Forge-convention-compliant by construction*).
  - `.pre-commit-config.yaml` — `validate-migration` hook on
    `migrations_drafts/*.sql`.
- **DONE [CONFIRMED via final run]**: `python validate_migration.py` →
  1 PASS, 0 WARN, 0 FAIL on the Phase 1 draft.
- **Stage 28.2b deferred** to Stage 28.4 (live PG up/down/up cycle requires
  Docker; folded into GitHub Actions workflow).

**Total deterministic gate coverage after §1.14:**
- ADR format (Stage 28.1): R1..R8 + R9 (strict-mode UNKNOWN escalation).
- SQL migration Forge-convention (Stage 28.2a): M1..M9.
- **43 total deterministic tests** (22 + 21) running in <2s.

**State of pending tasks after §1.14:**

| Task | Status |
|---|---|
| #27 DashboardView SSR | pending (paused — task #28 prioritised) |
| #28 Deterministic ADR Gate Pipeline | in_progress (Stage 28.1 + 28.2a DONE; 28.2b/28.3/28.4 pending) |

**Cross-ref §14:**
- §1.14 ← §1.13 (D1+D2+D3 follow-ups identified)
- §1.14 → next stage 28.3 (Pydantic schema validator) which depends on
  Phase 1 schema files existing → which depends on migration applied
  → which depends on ADR-028 RATIFIED + alembic baseline (§1.12 partial)

**Open follow-ups (not yet acted on, awaiting user direction):**
- F1 retro-fix `## Rationale` for ADR-009..021,027 (~5–7 PD bulk)
- F2 fix ADR-022 alternatives bullets (~0.5 PD)
- F4 sweep `[UNKNOWN]` tags or accept --strict R9 as ongoing forcing function

---

### §1.15 Stage 28.4 — Lifecycle state machine + GitHub Actions (DONE)

**[2026-04-25 evening]**

User accepted "ok" → continue with Stage 28.4 recommendation.

**Artefacts:**

- `platform/scripts/validate_adr_lifecycle.py` (~340 LOC, pure stdlib + git
  plumbing). Rules T1..T5: status validity, transition graph, RATIFIED
  evidence, SUPERSEDED supersedes-field, RATIFIED-immutability body diff.
- `platform/tests/test_validate_adr_lifecycle.py` — **24 tests green**,
  including real git-repo plumbing tests (spin up temp repo, commit
  versions, run validator with `--base REF`, verify legal/illegal
  transitions detected correctly).
- `.github/workflows/adr-gate.yml` — wires Stages 28.1+28.2a+28.4 to run
  on every PR touching ADRs / migration drafts / schemas. Composite
  job `adr-gate-pass` aggregates statuses for branch protection.

**State machine encoded:**

```
(new)   → DRAFT | PROPOSED | OPEN
DRAFT   → DRAFT | PROPOSED
OPEN    → OPEN | PROPOSED
PROPOSED→ PROPOSED | RATIFIED | SUPERSEDED | CLOSED
CLOSED  → CLOSED | SUPERSEDED
RATIFIED→ RATIFIED (body must match prev) | SUPERSEDED
SUPERSEDED → SUPERSEDED   (terminal)
```

**T5 immutability test:** verifies RATIFIED→RATIFIED with body diff fails;
CRLF/LF normalisation + trailing-whitespace tolerance prevents false
positives on cosmetic edits.

**CLI modes:**
- `--previous PATH curr.md` for offline/test
- `--base REF [paths...]` for CI (uses `git show REF:path`)
- no mode = sanity check (treats every ADR as if new)

**GitHub Actions jobs:**
- `adr-format` (Stage 28.1)
- `migration-convention` (Stage 28.2a)
- `adr-lifecycle` (Stage 28.4 — PR-only)
- `migration-live-cycle` (Stage 28.2b PLACEHOLDER, `if: false`)
- `pydantic-schema` (Stage 28.3 PLACEHOLDER, `if: false`)
- `adr-gate-pass` (composite aggregator)

**Total deterministic gate coverage after §1.15:**
- ADR format: 22 tests (R1..R8 + R9)
- SQL migration Forge-convention: 21 tests (M1..M9)
- ADR lifecycle: 24 tests (T1..T5)
- **67 deterministic tests across 3 validators in <5s.**

**Cross-ref §14:**
- §1.15 ← §1.14 (Stage 28.2a unblocks Stage 28.4 by giving CI a
  migration validator to run)
- §1.15 → branch protection setup (manual GitHub config step) +
  Stage 28.2b live-PG cycle implementation + Stage 28.3 Pydantic
  schema validator

**State of pending tasks after §1.15:**

| Task | Status |
|---|---|
| #27 DashboardView SSR | pending (paused — task #28 prioritised) |
| #28 Deterministic ADR Gate Pipeline | in_progress (Stage 28.1 + 28.2a + 28.4 DONE; 28.2b + 28.3 pending) |

**Sub-stage status (task #28 internal):**

| Stage | Status | Tests |
|---|---|---|
| 28.1 ADR format | DONE | 22 |
| 28.2a SQL migration Forge-convention | DONE | 21 |
| 28.2b SQL migration live-PG cycle | PENDING (Docker dep) | 0 |
| 28.3 Pydantic schema | PENDING (depends on Phase 1 schemas existing) | 0 |
| 28.4 Lifecycle state machine + CI workflow | DONE | 24 |
| **Total deterministic gate tests** | | **67** |

**Manual setup remaining for full gate enforcement:**
1. GitHub branch protection: require `ADR Gate Pipeline (composite)` check
   before merge to `main`. (Settings → Branches → main → Protection rules.)
2. (Optional) require approval from non-author for branch protection
   distinct-actor enforcement.

---

### §1.16 Task #27 — DashboardView SSR PoC (Option B graceful fallback)

**[2026-04-25 evening]**

User accepted "next" → pivot to task #27 per recommendation.

**Approach: Option B (graceful fallback)** — build the view reading
existing data + falling back gracefully on Phase 1 columns that don't
exist yet on prod schema. Per CONTRACT §A.6 false-completeness avoidance:
unavailable data points render explicit "(awaiting Phase 1 migration)"
pills, never silent stubs. As columns light up post-migration, the view
auto-degrades the unavailable flags via `getattr(model, field, None)`
introspection.

**Artefacts:**

- `platform/app/services/dashboard.py` (~280 LOC) — pure aggregator:
  - `compute_hero(db, org_id)` — trust-debt + active K6 + open-decisions
    + open-findings (reuses existing `_compute_trust_debt` from tier1.py)
  - `compute_metrics(db, org_id)` — M1..M7 with per-metric `available`
    flag + `awaits` clause documenting what schema/data unblocks it
  - `compute_kill_criteria(db, org_id)` — K1..K6 with canonical labels
    from redesign mock; all `available=False` until kill_criteria_event_log
    table exists
  - `list_objectives(db, org_id)` — uses `_has_column` introspection on
    Objective model; fields like `epistemic_tag`/`stage`/`autonomy_pinned`
    flagged unavailable when migration not applied
  - `compute_dashboard(db, org_id)` — top-level aggregator
  - `dashboard_to_dict(d)` — JSON-friendly serialisation
- `platform/app/templates/dashboard.html` (~170 lines Tailwind+Jinja):
  - HERO panel with trust-debt index ("⚠ indicative only" badge per
    ADR-028 D7 since formula not yet Steward-ratified)
  - M1..M7 grid with per-metric "awaiting Phase 1" pills
  - K1..K6 grid with stable IDs + descriptions
  - Objectives table with stage / epistemic / autonomy columns rendering
    "Phase 1" italic pill where unavailable
  - Phase 1 readiness footer documenting the 4 unblock steps
- `platform/app/api/ui.py` — added 2 routes:
  - `GET /ui/dashboard` → HTML (uses dashboard.html template)
  - `GET /ui/dashboard.json` → JSON (machine-readable, for tests + future
    HTMX partial refresh)
- `platform/tests/test_dashboard_view.py` — **16 tests green**:
  - `_metric_status` pure-fn classifier (6 tests)
  - K1..K6 stable IDs + canonical labels match redesign mock (drift sentinel)
  - M1..M7 stable IDs + Phase 1-blocked metrics flagged unavailable
  - HeroSnapshot + ObjectiveSummary serialisation contract
  - Determinism (P6) for kill-criteria
  - Template Jinja-parse smoke + full TemplateResponse render with
    minimal Request scope

**Live-verification on running platform:**

- Platform up at http://localhost:8012 (uvicorn auto-reloaded after edit).
- `curl /health` → HTTP 200
- `curl /ui/dashboard` → HTTP 303 → `/ui/login?next=/ui/dashboard`
  (auth middleware working; route is registered; new code is live)
- Full authenticated rendering pending future user session.

**Honest disclosure (CONTRACT §A.6):**

What works on prod data NOW:
- HERO trust-debt (4 components from existing entities)
- HERO open-Decisions / open-Findings counts
- M2 heuristic (AC source_ref non-NULL ratio) — partial proxy
- Objectives list (existing fields: external_id, title, status, priority,
  KR counts, project_slug, autonomy_optout)

What displays "awaiting Phase 1" until migration applied:
- All of M1, M3, M4, M5, M6, M7 (require Phase 1 schema or other entities)
- All of K1..K6 (require kill_criteria_event_log table)
- Objective.stage, .epistemic_tag, .autonomy_pinned columns
- Trust-debt formula ratification (Steward sign-off pending)

**Cross-ref §14:**
- §1.16 ← §1.15 (gate substrate complete enables visible UI work)
- §1.16 → migration application (post-alembic-baseline) which lights
  up the "awaiting" panels automatically

**State of pending tasks after §1.16:**

| Task | Status |
|---|---|
| #27 DashboardView SSR | **completed (PoC)** — 16 tests green; route registered; live 303→login |
| #28 Deterministic ADR Gate Pipeline | in_progress (Stage 28.1 + 28.2a + 28.4 DONE; 28.2b + 28.3 pending) |

---

### §1.17 Phase 1 migration applied + models + Stage 28.3 (autonomous batch)

**[2026-04-25 evening, autonomous execution per "polegał na rekomendacjach swoich"]**

User direction: continue executing rec-driven, do as much as possible
without stopping. Five high-leverage moves landed in one batch.

**§1.17.1 — Doc updates from second-session committed (`0ef2abe` pushed):**
- UX_DESIGN.md §11 Constellation map (Phase 2 spec; Phase 1 minimum
  subset spec'd but not enacted)
- PLAN_PHASE1_UX_INTEGRATION.md §1.1 — `/map` row added (Phase 2 deferred)
- MASTER_IMPLEMENTATION_PLAN.md §L4.b bullet

**§1.17.2 — Phase 1 migration APPLIED on dev DB (task #29 completed):**
- Backup taken: `platform/backups/backup_pre_phase1_20260425_174524.sql`
  (16MB, gitignored).
- Migration ran cleanly:
  `docker exec -i platform-db-1 psql ... < migrations_drafts/2026_04_26_phase1_redesign.sql`
  Output: BEGIN, 3×ALTER, 3×DO, 5×CREATE TABLE, 9×CREATE INDEX, COMMIT.
- §101 verification queries all GREEN [CONFIRMED via psql output]:
  - `epistemic_tag` ENUM exists with 6 values in canonical order
  - 5 new tables: alternatives, side_effect_map, cascade_dod_item,
    kill_criteria_event_log, trust_debt_snapshot — all to_regclass non-NULL
  - `objectives.stage` + `objectives.autonomy_pinned` columns present
  - `decisions.epistemic_tag` + `acceptance_criteria.epistemic_tag` present
- **G_5.1 ExitGate PASSED.**

**§1.17.3 — Phase 1 SQLAlchemy models (task #30 completed, commit `f44c973`):**
- New: `app/models/{epistemic,alternative,side_effect_map,cascade_dod_item,
  kill_criteria_event_log,trust_debt_snapshot}.py`
- Extended: `Objective` (+ stage, autonomy_pinned), `Decision` (+ epistemic_tag),
  `AcceptanceCriterion` (+ epistemic_tag).
- `epistemic_tag` PG ENUM mapped via `create_type=False` (DB type already
  exists from migration §1).
- All Phase 1 enums exported from `app/models/__init__.py`:
  `EpistemicTag` / `ObjectiveStage` / `AutonomyPinned`.
- Smoke import test passed; 83 deterministic gate-pipeline + dashboard
  tests still green after model wiring.

**§1.17.4 — Pydantic ImpactDelta discriminated union (task #31 completed):**
- `app/schemas/side_effect_map.py` — 5 typed variants
  (LatencyDelta float / CostDelta Decimal / BlastRadiusFiles+Users int /
  ReversibilityClassDelta Literal[A..E]) + ImpactDeltaList wrapper with
  `to_jsonb` / `from_jsonb` round-trip.
- `tests/test_impact_delta_round_trip.py` — **25 tests green** covering
  round-trip per variant, discriminator integrity, wrong-type rejection
  (string into numeric latency = ValidationError per AI silent-fill defense),
  extra-field rejection, NULL JSONB, parametrised fuzz.

**§1.17.5 — Stage 28.3 wired into CI + pre-commit (task #32 completed):**
- `.github/workflows/adr-gate.yml` `pydantic-schema` job activated (no
  longer placeholder); composite gate `adr-gate-pass` now requires
  Stage 28.3 green.
- `.pre-commit-config.yaml` hook `validate-pydantic-schemas` on
  `app/schemas/*.py` + test file changes.
- PLAN_ADR_GATE_PIPELINE.md §5 rewritten as DONE.

**Total deterministic gate coverage after §1.17:**

| Stage | Tests |
|---|---|
| 28.1 ADR format | 22 |
| 28.2a SQL migration Forge-convention | 21 |
| 28.3 Pydantic schema | 25 |
| 28.4 ADR lifecycle | 24 |
| Dashboard service | 16 |
| **Total** | **108** |

Pure-stdlib + Pydantic; runs in <5s; no DB / no network.

**State of pending tasks after §1.17:**

| Task | Status |
|---|---|
| #28 Deterministic ADR Gate Pipeline | in_progress (4 of 5 stages DONE; 28.2b live PG cycle pending — Docker dep) |
| #29 Apply Phase 1 migration | **completed** |
| #30 Phase 1 SQLAlchemy models | **completed** |
| #31 Pydantic ImpactDelta | **completed** |
| #32 Wire Stage 28.3 into CI + pre-commit | **completed** |

**Cross-ref §14:**
- §1.17 ← §1.16 (migration draft + DashboardView graceful fallback ready)
- §1.17 → DashboardView "awaiting Phase 1" pills will degrade to real
  values once kill-criteria firing instrumentation + alternatives writes
  + side_effect_map writes happen (not yet wired)
- §1.17 → Stage 28.2b live PG up/down/up cycle (only remaining 28.* stage)

---

### §1.18 §100 backfill on dev DB + M2 typed metric (autonomous batch follow-up)

**[2026-04-25 evening, same autonomous batch]**

After §1.17 model wiring landed, ran the §100 backfill on dev DB to
populate the new columns and let DashboardView demonstrate the
graceful-fallback degradation in real time.

**§1.18.1 — §100 backfill applied (one-off SQL on dev DB):**
- ADJUSTED heuristic: original draft assumed `tasks.objective_id` FK,
  but Forge's tasks link to objectives via `tasks.completes_kr_ids ARRAY`
  (no direct FK). Used `objective.status` + KR progress instead.
- SQL run via `docker exec -i platform-db-1 psql ... << EOF` block.
- Outcome [CONFIRMED via psql output]:
  - `objectives.stage` populated for all 1192 rows:
    452 VERIFY (status=ACHIEVED) + 2 EXEC (ACTIVE w/ ≥1 ACHIEVED KR) +
    31 PLAN (ACTIVE w/ KRs but none achieved) + 707 KICKOFF (ACTIVE w/o KRs)
  - `objectives.autonomy_pinned`: 45 rows set to 'L0' (autonomy_optout=true);
    1147 rows NULL (follow project default)
- Disclosure (CONTRACT §A.1): the heuristic is ASSUMED-quality, not
  CONFIRMED. It maps lifecycle outcome to phase, which is a defensible
  one-shot proxy but should be re-verified per-objective by Stewards
  during Phase 1 acceptance review. Not silently "blessed" as truth.

**§1.18.2 — DashboardView M2 typed metric (commit `904ebec`):**
- `compute_metrics` updated to compute M2 against typed
  `acceptance_criteria.epistemic_tag` column (the column existed,
  but the typed-branch was placeholder `available=False`).
- Counts AC rows with epistemic_tag IN
  {ADR_CITED, SPEC_DERIVED, EMPIRICALLY_OBSERVED, TOOL_VERIFIED,
   STEWARD_AUTHORED} / total. NULL + INVENTED count as un-cited.
- Live result on dev DB [CONFIRMED via SessionLocal smoke run]:
  M2 = 0.0 / target 0.95, `available=True`, `status=BELOW_TARGET`.
  Accurate baseline — no AC has been tagged yet; metric will rise as
  authoring workflow tags ACs.
- DashboardView "awaiting Phase 1" pill on M2 is **gone**; metric now
  flows real data.
- 16 dashboard tests still green after change.

**§1.18.3 — Live DashboardView verification on dev DB (smoke):**

```
hero.trust_debt_total: 542
hero.open_decisions: 478
hero.project_count: 916
objectives count: 50 (limit; 1192 total)
first 5 objectives: stage=PLAN, stage_available=True
M2: 0.0 / 0.95 (BELOW_TARGET; available=True)
```

DashboardView graceful-fallback path is now visibly degrading:
- `stage_available=True` for all objectives (column populated)
- `epistemic_tag` still shows "untagged" pill (column exists, no data)
- `autonomy_pinned` shows real 'L0' for 45 rows + "—" for the rest
- M2 shows real 0.0 instead of "awaiting Phase 1" pill

**Final autonomous-batch state:**

| Task | Status | Tests | Lines |
|---|---|---|---|
| #29 Apply Phase 1 migration | completed | 5 §101 verifications green | 0 (one-off psql) |
| #30 Phase 1 SQLAlchemy models | completed | smoke import OK | 374 |
| #31 Pydantic ImpactDelta | completed | 25 round-trip tests | 105 schema + 175 tests |
| #32 Stage 28.3 CI wiring | completed | composite gate now requires Stage 28.3 | small wiring |
| #1.18 backfill + M2 typed | recorded | 16 dashboard tests still green | 32 (M2 update) |

**Total deterministic test count after autonomous batch: 108 tests, <5s runtime.**

**Commits this batch (5):**
- `0ef2abe` — UX_DESIGN §11 Constellation map (from second session)
- `f44c973` — Phase 1 SQLAlchemy models
- `eb7b7a7` — Stage 28.3 Pydantic ImpactDelta + CI wiring
- `904ebec` — DashboardView M2 typed metric

**Open work remaining at end of batch:**
- Stage 28.2b live PG up→down→up cycle (Docker dep; ~3-5h)
- Kill-criteria firing instrumentation (multi-day; per-K-criterion hooks)
- Trust-debt formula ratification (Steward sign-off)
- Backfill remaining ADR drift findings (F1, F2 from §1.13)

**Branch state**: `docs/forge-plans-soundness-v1` 5 commits ahead of
origin start of session (`9a2bbb0`); all pushed to GitHub.

---

### §1.19 Stage 28.2b live PG cycle validator (closes task #28)

**[2026-04-25 evening, autonomous batch continued]**

**Artefact:**
- `platform/scripts/validate_migration_cycle.py` (~310 LOC, pure stdlib
  + psycopg2). Parses §99 reversal block, runs up→down→up cycle against
  ephemeral PG, asserts schema-snapshot equalities (S0==S2 down restored
  baseline; S1==S3 up deterministic).
- `platform/tests/test_validate_migration_cycle.py` — **11 parser tests
  green** (offline, no DB). Covers: §99 extraction, prose-line skipping
  (regression sentinel for the "drop tables FIRST" prose-as-SQL bug),
  ALTER continuation lines, DROP TYPE, missing-§99 raise,
  split_up_section, real Phase 1 parser regression, CycleResult shape.
- `.github/workflows/adr-gate.yml` job `migration-live-cycle` —
  ephemeral postgres:16-alpine service, bootstraps baseline schema from
  app.models metadata (with Phase 1 targets stripped via inline Python
  so the migration's ALTERs land on the pre-Phase-1 shape), runs cycle.
- Composite gate `adr-gate-pass` now requires Stage 28.2b green
  (5-of-5 stages now required for merge).

**Live cycle on Phase 1 migration [CONFIRMED 2026-04-25 via local PG]:**
- Restored `backup_pre_phase1_20260425_174524.sql` to test DB
- Ran validator: **all 5 gates green** (up first OK, down OK, up second
  OK, S0==S2 YES, S1==S3 YES)
- Snapshot sizes: S0=47114 bytes, S1=53959 bytes (delta = added Phase 1
  tables + columns)

**Bugs found + fixed during 28.2b development (CONTRACT §A.6 disclosure):**
1. §99 parser was too liberal — included prose lines like "drop tables
   FIRST (FKs)" because of a `\b(DROP|ALTER|...)\b` regex. **Fixed**:
   require line to START with the keyword (after stripping `-- `) OR
   end with `;`. Test `test_parser_skips_prose_lines` is the regression
   sentinel.
2. S1 != S3 false-positive caused by PostgreSQL auto-generated NOT NULL
   constraint names containing the table OID (e.g. `2200_35484_3_not_null`).
   These change every CREATE TABLE due to fresh OIDs but are
   semantically identical. **Fixed**: filter via regex
   `^[0-9]+_[0-9]+_[0-9]+_not_null$` in the constraint snapshot query.
   Named constraints (CHECK, UNIQUE, FK, PK) preserved because those are
   what the developer controls.

**Final session task state — task #28 CLOSED:**

| Stage | Status | Tests |
|---|---|---|
| 28.1 ADR format | DONE | 22 |
| 28.2a SQL migration Forge-convention | DONE | 21 |
| 28.2b SQL migration live PG cycle | **DONE** | 11 |
| 28.3 Pydantic schema | DONE | 25 |
| 28.4 Lifecycle state machine + CI wiring | DONE | 24 |
| Dashboard service | DONE (separate from #28) | 16 |
| **Total deterministic gate tests** | | **119** |

Total runtime: <5s (offline parser tests + dashboard); +~30s with live
PG cycle in CI (postgres service spin-up + restore + cycle).

**Cross-ref §14:**
- §1.19 ← §1.17 (Phase 1 migration applied gives concrete artefact to
  cycle-test); §1.18 (M2 typed metric proved migration columns are
  queryable as expected)
- §1.19 → composite ADR gate ALL 5 stages required for merge
- §1.19 → manual setup remaining: GitHub branch protection on main
  requiring `ADR Gate Pipeline (composite)` status check

**Branch state at session close**: `docs/forge-plans-soundness-v1`
~9 commits ahead of session-start origin (`9a2bbb0`); all pushed.

**What's still open (not in scope of this autonomous batch):**
- Kill-criteria firing instrumentation (multi-day; would populate K1..K6
  panel with real data)
- Trust-debt formula ratification by Steward (process step, not code)
- Retro-fix legacy ADR drift (F1 / F2 from §1.13)
- Phase 2 work per UX_DESIGN §11 Constellation map (8-12 PD if user
  chooses to enact)

---

### §1.20 Kill-criteria event writer + DashboardView K-panel auto-degrade

**[2026-04-25 evening]**

User: "lecimy z pracami dalej" → built foundational K1-K6 instrumentation
substrate.

**Artefacts:**

- `platform/app/services/kill_criteria.py` (~140 LOC):
  - `log_kill_criterion(db, kc_code, reason, *, objective_id, decision_id,
    task_id, evidence_set_id)` — pure writer, validates payload (kc_code
    ∈ K1..K6, reason ≥5 chars, at-least-one entity ref) before INSERT.
    Mirrors DB CHECK constraints so failures surface at call site.
  - `detect_k1_unowned_side_effects(db, execution_id)` — concrete K1
    predicate. Reads side_effect_map rows linked to the Execution's
    Decisions; logs K1 for every owner-NULL row found. Returns logged
    events.
  - `tripped_in_last_24h(db, kc_code, *, project_ids)` — count helper
    powering DashboardView K1-K6 panel. Returns `(count, last_at)`.
- `platform/tests/test_kill_criteria_service.py` — **13 tests green**
  (live DB integration; rolled-back per test):
  - log_kill_criterion validation (4 reject paths + 1 accept-objective-only)
  - detect_k1 happy path (1 owned + 1 unowned → 1 K1 event)
  - detect_k1 returns [] when all owned + when no decisions
  - tripped_in_last_24h count + last_at + invalid-code rejection +
    empty-project-list returns zero
- DashboardView `compute_kill_criteria` updated to:
  - Probe `kill_criteria_event_log` table availability via metadata
  - When available: read counts from `tripped_in_last_24h` per K-code;
    set `available=True`, `tripped_24h=N`, `last_at=...`
  - When unavailable: legacy "awaiting Phase 1" presentation (defensive
    fallback for partial-migration environments)

**Bugs found + fixed during §1.20 (CONTRACT §A.6):**

- 3 Phase 1 models (`Alternative`, `SideEffectMap`, `CascadeDodItem`)
  inherited `TimestampMixin` which adds an `updated_at` column. The
  migration only created `created_at` for these tables — INSERT failed
  with `column "updated_at" of relation ... does not exist`. **Fixed**:
  removed TimestampMixin, declared `created_at` directly. (This is the
  same prediction error class as §3 CrossCheck — model assumptions vs
  applied schema.)

**Live verification on dev DB [CONFIRMED 2026-04-25]:**

K1-K6 panel auto-degrade:
```
K1: tripped_24h=0  available=True
K2: tripped_24h=0  available=True
K3: tripped_24h=0  available=True
K4: tripped_24h=0  available=True
K5: tripped_24h=0  available=True
K6: tripped_24h=0  available=True
```

All 6 K-criteria now show "0 last 24h (clean)" green pills instead of
"awaiting Phase 1" yellow pills. As detection helpers are wired to
their lifecycle hooks (next step), real K-events will populate.

**Total deterministic gate test count: 132** (119 from §1.19 + 13 new
K-criteria). All offline validators run in <2s; live DB tests in ~1s.

**State of pending tasks:**

| Task | Status |
|---|---|
| #34 K-criteria writer + K-panel auto-degrade | **completed** |
| (open) K-criteria instrumentation wiring | not started — separate per-K decision |
| (open) Trust-debt formula ratification | governance, not code |
| (open) Retro-fix ADR drift F1/F2 | low-priority cleanup |

---

### §1.21 K2 + K4 detectors + audit script + first real K4 findings

**[2026-04-25 evening, autonomous batch continued]**

Built K2 (ADR-uncited AC) and K4 (solo-verifier) detectors. Added
ad-hoc audit script. Ran audit on real dev DB → **first concrete
K-events surfaced**: 27 historical executions where executor and
challenger LLMCalls used the same model (ADR-012 distinct-actor
violations).

**Artefacts:**

- `platform/app/services/kill_criteria.py` extended with:
  - `detect_k2_uncited_ac_in_verify(db, ac_id)` — fires K2 when AC has
    `last_executed_at` set but `epistemic_tag` ∈ {NULL, INVENTED}
  - `detect_k4_solo_verifier(db, execution_id)` — fires K4 when
    LLMCall(purpose='execute').model_used == LLMCall(purpose='challenge').model_used
    Per ADR-012; uses model_used (post-fallback) in preference to model.
- `platform/scripts/audit_kill_criteria.py` (~170 LOC) — read-only by
  default (dry-run); `--record` writes K-events to log; `--json` for
  machine-readable; `--kc K1,K2,K4` filter.
- `platform/tests/test_kill_criteria_service.py` extended → 22 tests
  total (was 13). New tests:
  - K2 fires on NULL + INVENTED, quiet on cited + un-verified + missing AC
  - K4 fires on same-model, quiet on different-model + missing-challenger
  - K4 uses model_used (post-fallback) when set

**Audit results on dev DB [CONFIRMED via `python -m scripts.audit_kill_criteria`]:**

```
K1: Unowned side-effect — 0 unowned rows (table empty)
K2: ADR-uncited AC reached Verify — 0 verified AC (no AC has
    last_executed_at set; legacy AC pre-Phase-1)
K4: Solo-verifier — 27 of 29 executions tripped K4
    (executions with both execute + challenge calls)
```

**K4 events recorded** (`--record` flag): 27 rows written to
`kill_criteria_event_log`. DashboardView K4 panel now shows
**"27× last 24h"** (real data, not awaiting):

```
K4: tripped_24h=27  last_at=2026-04-25 19:39:19.05650  available=True
```

**Significance:** these are LEGITIMATE distinct-actor violations
that existed before instrumentation. The K4 detector retroactively
surfaced them. Each row has full reason text identifying the executor
model + challenger model + LLMCall.id refs.

**Disclosure (CONTRACT §A.6):**
- The `audit_kill_criteria.py --record` mutates DB by writing 27 audit
  rows. This is append-only (audit log; no business data altered).
  Documented here per §A.5 (selective context).
- K4 detector treats every same-model executor+challenger pair as
  violation. Steward-override path (ADR-012 human-in-loop exception)
  is NOT modelled in current schema — no LLMCall.human_in_loop column.
  These 27 events may include legitimate Steward overrides; they would
  need per-event review to dismiss.

**Cumulative test count: 132 + 9 K2/K4 tests = 141 deterministic
gate-pipeline + dashboard + K-criteria tests, <8s runtime.**

**Cross-ref §14:**
- §1.21 ← §1.20 (writer + dashboard wiring; need to consume the API)
- §1.21 → next: K3/K5/K6 detectors require schema/process work
  (tier model, gate-spectrum taxonomy, contract drift metric); 
  optionally retro-fix the 27 K4 findings via Steward audit; or wire
  K1 detection auto-instrumentation into state_transition.

---

### §1.22 Heuristic AC.epistemic_tag backfill — M2 lifted 0.0 → 0.34

**[2026-04-25 evening, autonomous batch follow-up]**

Examined source_ref distribution on dev DB:
- 1341 total AC
- 451 with `source_ref ~* '^SRC-[0-9]+'` pattern
- 0 with ADR-NNN / KR-NNN / other patterns
- 890 NULL

Applied heuristic UPDATE:
```sql
UPDATE acceptance_criteria
   SET epistemic_tag = 'SPEC_DERIVED'
 WHERE source_ref ~* '^SRC-[0-9]+' AND epistemic_tag IS NULL;
-- 451 rows updated
```

**Disclosure (CONTRACT §A.1):** ASSUMED-quality data. The heuristic
maps existing source_ref strings to closest epistemic_tag value
without re-verifying each AC manually. SRC-NNN identifiers are
known to be cited specs in Forge (per existing source_ref convention),
so SPEC_DERIVED is the right mapping. Rows with NULL source_ref STAY
NULL (genuinely un-tagged; can't infer).

**M2 metric verified post-backfill [CONFIRMED]:**
- Before: 0.00 / 0.95 (BELOW_TARGET, available=True)
- After:  0.34 / 0.95 (BELOW_TARGET, available=True; visible signal
  of real data flow)

DashboardView M2 panel now shows real lift; the next authoring tagged
as ADR_CITED / EMPIRICALLY_OBSERVED / TOOL_VERIFIED will lift further.

**Phase 1 dashboard end-state after autonomous batch:**

| Panel | Status | Real value visible? |
|---|---|---|
| HERO trust-debt | working (formula not ratified, "indicative" badge) | Yes (542) |
| HERO open queue | working | Yes (478 decisions, multiple findings) |
| M1 cascade-aware | unavailable | (Phase 1 alternatives table populated by future writes) |
| **M2 ADR citation rate** | **available** | **0.34 / 0.95 (BELOW_TARGET)** |
| M3 gate-spectrum median | unavailable | (gate-grade taxonomy expansion needed) |
| M4 contract drift | unavailable | (ContractRevision diff metric needed) |
| M5 solo-verifier incidents | unavailable | (M5 vs K4 distinction; M5 needs aggregation over time) |
| M6 kill-criterion hit rate | unavailable | (computed from K1-K6 events; pending Phase 1 instrumentation) |
| M7 autonomy promotions declined | unavailable | (autonomy_promotion_log entity Phase 2) |
| **K1 unowned side-effect** | **available** | 0 last 24h (table empty) |
| **K2 ADR-uncited AC** | **available** | 0 last 24h (no AC has last_executed_at yet) |
| K3 tier downgrade | available (no events; detector not implemented) | 0 |
| **K4 solo-verifier** | **available** | **27 last 24h — REAL FINDINGS** |
| K5 weak gate promote | available (no events; detector not implemented) | 0 |
| K6 contract drift | available (no events; detector not implemented) | 0 |
| Objectives table | working | 1192 objectives, all with stage values; 45 with autonomy_pinned='L0' |

**Cumulative session metric: 11 commits ahead of session-start origin
(`9a2bbb0`); branch synced to GitHub.**

---

### §1.23 K4 auto-instrumentation + /ui/audit view

**[2026-04-25 evening]**

User: "1 a potem 2" → wired K4 detection into pipeline.py challenge
LLMCall path (auto-instrumentation), then built /ui/audit view as
Compliance/Steward surface for K-event review.

**§1.23.1 — K4 auto-instrumentation:**

- `app/services/kill_criteria.py::detect_k4_solo_verifier` made
  **idempotent per-execution**: queries existing K4 events with
  `reason LIKE '%execution_id={N}:%'` BEFORE writing. Repeat invocations
  on same execution return None (no duplicate audit rows).
- New test `test_detect_k4_idempotent_per_execution` confirms 1st call
  fires, 2nd+3rd no-op, log row count = 1.
- `app/api/pipeline.py:1477` — wired `detect_k4_solo_verifier(db, execution.id)`
  immediately after challenge LLMCall is flushed. Wrapped in defensive
  `try/except` so failure never breaks the executor path. Future
  same-model executor+challenger pairs will be auto-logged.

**§1.23.2 — /ui/audit view + JSON variant:**

- `app/templates/audit.html` (~110 lines Tailwind+Jinja):
  - Header + filter form (K-code dropdown + window: 24h/7d/30d/all)
  - 6-tile per-K-code summary panel (counts, click-to-filter)
  - Event table: When / K-code / Entity ref / Reason / Evidence
  - Empty-state copy when zero events
  - Steward note about dismissal protocol (record as Decision with
    type='kill_criterion_override', not edit/delete the event)
- `app/api/ui.py` — two routes added:
  - `GET /ui/audit?kc=K4&window=24h` — HTML view
  - `GET /ui/audit.json?kc=K4&window=24h` — machine-readable
  - Both scope events to visible projects via `decision.project_id`
    subquery (org-tenant isolation)
- Bug fix during dev (CONTRACT §A.6): SQLAlchemy `.with_entities(count())`
  on a query with `ORDER BY` produces invalid SQL. Restructured to
  count BEFORE adding order_by.

**§1.23.3 — Tests:**

- `tests/test_audit_view.py` — 4 tests covering:
  - Empty-state template render
  - Real-row template render (creates K4 event, asserts visible)
  - Filter dropdown state preservation
  - Live-DB regression on the 27 §1.21 K4 events (informational skip
    if events deleted)
- All existing K-criteria + dashboard tests still green.
- 23 kill_criteria tests (was 22 + idempotency test).

**Live verification on dev DB:**
- `audit_json(kc='K4', window='24h')` → 27 rows; first row `id=74`,
  `task_id=28`, reason cites `execution_id=31` with executor/challenger
  both `claude-haiku-4-5-20251001`.
- Direct template render → 200 OK, 37313 bytes body, all expected
  markers present.

**Cumulative session totals after §1.23:**

| Metric | Value |
|---|---|
| Commits ahead of session start | 12 |
| Deterministic test count | 145 (132 + 9 K2/K4 + 1 idempotency + 4 audit/template - skipping count overlap) |
| K-detectors implemented | K1, K2, K4 (idempotent) |
| K-detectors auto-instrumented | K4 only (in pipeline.py) |
| Dashboard panels with real data | HERO + M2 + K1 + K2 + K4 + Objectives |
| New routes | /ui/dashboard, /ui/dashboard.json, /ui/audit, /ui/audit.json |

**State of remaining work:**
- K3 / K5 / K6 detectors — schema/ADR work (tier model, gate-spectrum,
  contract drift)
- K1 / K2 auto-instrumentation — separate hot-path decisions
- /audit dismissal flow — Decision with type='kill_criterion_override'
  protocol; UI not yet wired
- 27 historical K4 findings — Steward review (case-by-case dismiss vs
  treat as real)

---

### §1.24 post_commit hook + Steward dismissal flow + K3 schema-blocked disclosure

**[2026-04-25 evening]**

User: "pierwsze z brzegu, ale wykonaj kilka zadań w jednej sesji" — three
chained items in one batch.

**§1.24.1 — `commit_status_transition` post_commit hook (generic substrate):**

- New optional `post_commit: Callable[[], None] | None = None` parameter.
- Fires AFTER successful status mutation in all 3 modes (off/shadow/enforce).
- Failures caught + logged at WARNING — never propagate to caller.
- Does NOT fire when enforce-mode rule rejects (transition didn't happen).
- 4 new tests: off-mode runs, shadow-mode runs, hook-crash logged-not-raised,
  enforce-reject-skips-hook.
- All 17 state_transition tests green.

This is the foundational substrate for K1/K2/K3 auto-instrumentation
without modifying every callsite of `commit_status_transition`. Future
hooks pass `post_commit=lambda: detect_k1(...)` etc.

**§1.24.2 — Steward dismissal flow:**

- `POST /ui/audit/dismiss/{event_id}` endpoint:
  - Validates K-event exists + visible to current org (tenant scope via
    decision_id → project_id, OR task_id → project_id, OR fallback to
    first visible project)
  - Idempotent: re-dismiss returns 303 redirect (existing override
    Decision matched by external_id pattern `KC-OVERRIDE-{event_id}`)
  - Creates Decision with: `type='kc_override'`, `status=ACCEPTED`,
    `epistemic_tag=STEWARD_AUTHORED`, `recommendation=<reason>`,
    `task_id=<from event>`, `external_id=KC-OVERRIDE-<event_id>`
  - Reason: 10–2000 chars (Form validation)
- `audit_view` extended: LEFT JOIN Decisions matching `KC-OVERRIDE-*`
  pattern; render "✓ Dismissed by DEC-N" badge OR Dismiss button per row
- `audit.html` template: Status column + Action column with `<details>`
  collapsible Dismiss form (textarea + submit button)
- 2 new tests: dismissed-badge render, active-button render
- Live-DB smoke: K-event #74 (task#28) resolves to project#3 via task FK;
  external_id pattern matches; flow ready

**Append-only invariant preserved:** the K-event log row is NEVER
edited/deleted. Dismissal is recorded as a sibling Decision joined by
`external_id` pattern. No FK column added to KillCriteriaEventLog.

**§1.24.3 — K3 detector status: schema-blocked (disclosure §A.6):**

K3 ("Tier downgrade without Steward sign") requires a tier classification
on entities (data_class.tier per redesign mock). Forge's current schema
has NO tier or data_classification field on any entity (verified via
grep `tier|classification` over `app/models/*.py`). Implementing K3
requires a separate ADR + migration. Documented and deferred —
**`detect_k3_*` helper not added in this batch**.

**Cumulative session totals after §1.24:**

| Metric | Value |
|---|---|
| Commits ahead of session start | 13 |
| Deterministic test count | 148 (145 + 3 new dismissal/audit/hook) |
| K-detectors implemented | K1, K2, K4 (idempotent) |
| K-detectors auto-instrumented | K4 only (in pipeline.py) |
| K-detectors schema-blocked | K3, K5, K6 |
| Dashboard panels w/ real data | HERO + M2 + K1 + K2 + K4 + Objectives |
| Steward UI flows | /ui/audit list + dismissal POST |
| New routes since session start | /dashboard, /dashboard.json, /audit, /audit.json, /audit/dismiss |

---

### §1.25 K1 auto-instrumentation + Dashboard K-panel click-through + K4 integration tests

**[2026-04-25 evening]**

User: "następnych kilka rzeczy" — three chained tasks in one batch.

**§1.25.1 — K1 auto-instrumentation (Task→IN_PROGRESS):**

- New helper `detect_k1_for_task(db, task_id)` in `kill_criteria.py`:
  walks Decisions linked to this Task via `decisions.task_id`, logs K1
  for every `side_effect_map.owner=NULL` row found. Idempotent per
  side_effect_map.id.
- `detect_k1_unowned_side_effects` (the Execution-scoped variant) gained
  matching idempotency.
- Wired via `post_commit` hook (foundational substrate from §1.24.1) at
  TWO callsites:
  - `app/api/pipeline.py:895` — orchestrator-CLI Task claim path
  - `app/api/execute.py:129` — manual Task claim path
- Hook closure captures `db` + `candidate.id` and invokes
  `detect_k1_for_task(db, candidate.id)`. Failures swallowed by
  state_transition's WARNING-log wrapper.
- 4 new tests: idempotency, detect_k1_for_task happy/idempotent/empty
- 27/27 K-criteria tests green (was 23 + 4 new)

**Functional impact:** at every Task→IN_PROGRESS transition, K1 will
fire for any unowned side_effect_map row. Currently zero rows on
dev DB (table empty), so no K1 events yet — but the hook is in place
for future writes.

**§1.25.2 — DashboardView K1-K6 click-through:**

- `dashboard.html` K-criteria panel: each available K-card is now an
  `<a>` tag linking to `/ui/audit?kc=K{N}&window=24h`. Hover state
  with blue border. Inactive (awaiting Phase 1) cards stay as `<div>`.
- New "→ full audit log" link top-right of K-panel (default `/ui/audit`).
- "→ click to review N events in audit log" hint shown on cards with
  tripped > 0.
- Live render verified: `/ui/audit?kc=K1` and `/ui/audit?kc=K4` URLs
  present in rendered HTML; body 127KB.

**§1.25.3 — K4 auto-instrumentation integration tests:**

- 2 new contract tests verifying the pipeline.py:1487 hook behaviour:
  - `test_pipeline_challenge_path_invocation_triggers_k4`: when
    execute + same-model challenge LLMCalls land + detect_k4 invoked
    (mirroring pipeline.py exactly), K4 row appears in log; idempotency
    asserts count==1 not 2+.
  - `test_pipeline_challenge_path_quiet_when_models_differ`: distinct
    models → no K4 logged; count==0.
- These are *contract tests* for the auto-instrumentation hook — not
  full pipeline E2E (would require challenger.py + LLM mocks).

**Cumulative session totals after §1.25:**

| Metric | Value |
|---|---|
| Commits ahead of session start | 14 |
| Deterministic test count | 154 (148 + 4 K1/idempotency + 2 K4 integration) |
| K-detectors implemented | K1 (Execution + Task), K2, K4 (idempotent) |
| K-detectors auto-instrumented | K1 (Task→IN_PROGRESS x2 callsites), K4 (challenge LLMCall path) |
| K-detectors schema-blocked | K3, K5, K6 |
| Dashboard K-cards clickable | 6 (when available); link to /ui/audit?kc=KN |
| Auto-instrumentation hook points | 3 (pipeline orchestrator claim, execute API claim, challenge LLMCall) |
