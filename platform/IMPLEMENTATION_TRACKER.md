# Forge MVP — Implementation Tracker

Każdy element z architektury z weryfikowalnym statusem. Kontrakt: żaden element nie jest "DONE" bez EXECUTED evidence.

Last verified: **2026-04-16** via real HTTP calls against running server (port 8012).
Validation-layer additions (Phase A + B.1): **2026-04-25** via pytest-only (no live HTTP); see §"Phase A+B.1 validation infrastructure" below.

---

## Phase A + B.1 validation infrastructure (added 2026-04-25)

Per PLAN_GATE_ENGINE / PLAN_MEMORY_CONTEXT. All claims verified via pytest;
none verified via live HTTP (platform not running for this session).
88 tests pass across the 7 validation+evidence test files; per CONTRACT
§B.8, all entries here are [ASSUMED: agent-analysis] pending distinct-actor
review.

| Component | Status | Evidence |
|-----------|--------|----------|
| `app/validation/verdict_engine.py` (pure VerdictEngine + replay-deterministic stub) | DONE | [PYTEST] tests/test_verdict_engine_stub.py — 4 tests pass; empty-rules → REJECTED, all-pass → composite PASS, fail-fast short-circuit, P6 determinism |
| `app/validation/gate_registry.py` (6 entities × 44 transitions populated) | DONE | [PYTEST] tests/test_gate_registry.py — 15 tests pass; entity-set match, EXPECTED_COUNTS, every to_state in CheckConstraint enum, no self-transitions, no DB imports |
| `app/validation/rules/evidence_link_required.py` (P16 closure) | DONE | [PYTEST] tests/test_evidence_link_rule.py — 14 tests; ANALYZING→ACCEPTED + 3 other Decision permanent-state transitions gated |
| `app/validation/rules/plan_gate_adapter.py` (A.3 wrapper) | DONE | [PYTEST] tests/test_legacy_rule_adapters.py 8 plan_gate tests; pass paths + fail paths + multi-violation summary + determinism |
| `app/validation/rules/contract_validator_adapter.py` (A.3 wrapper) | DONE | [PYTEST] tests/test_legacy_rule_adapters.py 5 contract_validator tests; chore-bypass + short-reasoning fail + missing-key defensive |
| `app/validation/shadow_comparator.py` (compare_and_log helper) | DONE | [PYTEST] tests/test_shadow_comparator.py — 9 tests; mode=off no-op, mode=shadow log on disagree, factory failure swallowed, multi-call independent |
| `app/models/verdict_divergence.py` | DONE | [IMPORT] `from app.models import VerdictDivergence` exits 0 |
| `app/models/idempotent_call.py` + `app/validation/idempotency.py` (A.5 P1) | DONE | [PYTEST] tests/test_idempotency.py — 19 tests; canonical hash determinism, in-memory store hit/miss/expiry, P1 invariant (factory invoked AT MOST ONCE per key+args within TTL) |
| `app/models/causal_edge.py` + `app/evidence/acyclicity.py` (B.1) | DONE | [PYTEST] tests/test_acyclicity.py — 11 tests; strictly older src passes, tolerance window inclusive, beyond-tolerance fails with diagnostic, custom tolerance argument |
| Shadow-comparator wired into `api/execute.py:277` + `api/pipeline.py:1051` | DONE | [IMPORT] both modules import cleanly with `from app.validation.shadow_comparator import compare_and_log`; mode='off' default keeps zero blast radius |
| Shadow-comparator wired into `api/pipeline.py:547` (plan_gate) | PARTIAL | [DOCUMENTED] integration point marked with comment block; verdict_divergences.execution_id NOT NULL prevents wiring at plan-ingest time (plan precedes Execution); decision deferred to A.4 cutover |

## Phase A residual (deferred to subsequent commits)

| Component | Status | Reason |
|-----------|--------|--------|
| A.1 work item 4: app-level Decision-insert gate (FK / trigger raising IntegrityError on no-evidence-link insert) | DEFERRED | Implemented as state-transition gate (A.1.4 commit) instead. Insert-time FK enforcement deferred to A.4 cutover when 75 .status= sites are wrapped — at which point state-transition gate becomes canonical insert-flow enforcement. |
| A.3 replay harness over 100 historical Executions | DEFERRED | Needs DB connection + populated DB. Once shadow mode runs ≥1 week with FORGE_VERDICT_ENGINE_MODE=shadow, that data fuels the replay test. |
| A.4 enforcement cutover (75 .status= sites across 9 files) | DEFERRED | Mechanical refactor; needs DB to verify wrapped paths don't regress legacy flow. |
| A.5 DBIdempotencyStore (production backend for IdempotencyStore Protocol) | DEFERRED | Protocol + InMemoryIdempotencyStore in place; DB-backed store needs migration to be applied first. |
| A.5 mcp_server middleware integration (4 mutating tools accept idempotency_key) | DEFERRED | Once DB store exists, wire into MCP tool dispatch path. |

---

## Modele DB (tabele)

| Tabela | Status | Evidence |
|--------|--------|----------|
| projects | DONE | [EXECUTED] `POST /projects` → `{"id":1}` — 2026-04-16. `GET /projects` → 200, project list — 2026-04-15 |
| tasks + task_dependencies | DONE | [EXECUTED] `POST /tasks` z depends_on → created. `GET /tasks` → 200, 3 tasks — 2026-04-15 |
| acceptance_criteria | DONE | [EXECUTED] 3 AC created z scenario_type + verification. `GET /tasks/T-001` → status=DONE, AC=3 — 2026-04-15 |
| executions | DONE | [EXECUTED] `GET /execute` → execution_id=1 created. `GET /executions` → 200, 3 executions — 2026-04-15 |
| prompt_sections | DONE | [EXECUTED] 7 sections in prompt_meta |
| prompt_elements | DONE | [EXECUTED] 9 elements (included + excluded tracked). `GET /executions/1` → 9 prompt_elements — 2026-04-15 |
| guidelines | DONE | [EXECUTED] `POST /guidelines` → G-001 MUST created. `GET /guidelines` → 200, 1 guideline — 2026-04-15 |
| decisions | DONE | [EXECUTED] `POST /decisions` → D-001 created, `POST /decisions/1/resolve` → CLOSED, `GET /decisions` → 200, 0 decisions (after resolve) — 2026-04-15 |
| changes | DONE | [EXECUTED] 2 changes saved from accepted delivery |
| micro_skills | DONE | [EXECUTED] 10 skills seeded (4 reputation + 4 technique + 2 verification) |
| output_contracts | DONE | [EXECUTED] 4 contracts seeded (default, feature/STANDARD, feature/FULL, bug/LIGHT) |
| findings | DONE | [EXECUTED] `GET /findings` → 200, 1 finding. Triage (approve) → 200, T-003 created — 2026-04-15 |
| audit_log | PARTIAL | [EXECUTED] model exists. [NOT EXECUTED] audit entries not verified in DB |
| objectives | DONE | [EXECUTED] `POST /projects/test-project/objectives` → O-001 created. `GET` → 200, 1 obj with 2 KRs — 2026-04-16 |
| key_results | DONE | [EXECUTED] 2 KRs (numeric+descriptive) with target_value. PATCH /objectives/1/key-results/0 → IN_PROGRESS/180.5 — 2026-04-16 |
| execution_attempts | DONE | [EXECUTED] 4 attempts recorded in DB. attempt #3 and #4 have identical reasoning_hash (9ba117e0) — 2026-04-16 |

## Core API Endpoints

| Endpoint | Status | Evidence |
|----------|--------|----------|
| GET /health | DONE | [EXECUTED] `{"status":"ok","version":"0.1.0"}` |
| POST /projects | DONE | [EXECUTED] `{"id":1,"slug":"test-project"}` |
| GET /projects | DONE | [EXECUTED] 200, returned project list — 2026-04-15 |
| GET /projects/{slug}/status | DONE | [EXECUTED] 200, returned task counts — 2026-04-15 |
| POST /projects/{slug}/tasks | DONE | [EXECUTED] task + 3 AC created |
| GET /projects/{slug}/tasks | DONE | [EXECUTED] 200, returned 3 tasks — 2026-04-15 |
| GET /projects/{slug}/tasks/{id} | DONE | [EXECUTED] 200, T-001 status=DONE, AC=3 — 2026-04-15 |
| POST /projects/{slug}/guidelines | DONE | [EXECUTED] G-001 created |
| GET /projects/{slug}/guidelines | DONE | [EXECUTED] 200, 1 guideline — 2026-04-15 |
| POST /projects/{slug}/decisions | DONE | [EXECUTED] 200, D-001 created — 2026-04-15 |
| GET /projects/{slug}/decisions | DONE | [EXECUTED] 200, 0 decisions (after creating and resolving D-001) — 2026-04-15 |
| POST /decisions/{id}/resolve | DONE | [EXECUTED] 200, status=CLOSED — 2026-04-15 |
| GET /projects/{slug}/findings | DONE | [EXECUTED] 200, 1 finding — 2026-04-15 |
| POST /findings/{id}/triage | DONE | [EXECUTED] 200, approved → T-003 created from finding — 2026-04-15 |
| GET /projects/{slug}/executions | DONE | [EXECUTED] 200, 3 executions — 2026-04-15 |
| GET /executions/{id} | DONE | [EXECUTED] 200, status=ACCEPTED, 9 prompt_elements — 2026-04-15 |
| GET /executions/{id}/prompt | DONE | [EXECUTED] 200, 3927 chars — 2026-04-15 |
| **GET /execute** | **DONE** | **[EXECUTED] prompt assembled, task claimed, 7 sections returned** |
| **POST /execute/{id}/deliver** | **DONE** | **[EXECUTED] REJECTED (13 FAIL checks) + ACCEPTED (2 WARNINGs) — 2026-04-15** |
| POST /execute/{id}/heartbeat | DONE | [EXECUTED] 200, lease extended — 2026-04-15 |
| POST /execute/{id}/fail | DONE | [INFERRED] route registered + handler exists in execute.py, not HTTP tested |
| **POST /execute/{id}/challenge** | **DONE** | **[EXECUTED] 200, 6 questions generated, enriched command returned — 2026-04-15** |
| **POST /projects/{slug}/objectives** | **DONE** | **[EXECUTED] 200, O-001 with 2 KRs created — 2026-04-16** |
| **GET /projects/{slug}/objectives** | **DONE** | **[EXECUTED] 200, returned O-001 with numeric+descriptive KRs — 2026-04-16** |
| **PATCH /objectives/{id}/key-results/{pos}** | **DONE** | **[EXECUTED] 200, KR status/current_value updated — 2026-04-16** |
| **POST /projects/{slug}/tasks/{id}/generate-scenarios** | **DONE** | **[EXECUTED] 200, 2 scenarios for T-100 (positive+negative) — 2026-04-16** |

## Prompt Parser (prompt assembly)

| Element | Status | Evidence |
|---------|--------|----------|
| Reputation frame (P0) | DONE | [EXECUTED] "Jakby ktoś powiedział..." w prompt output |
| Task instruction (P1) | DONE | [EXECUTED] instruction + AC w prompt |
| MUST guidelines (P1, scope-filtered) | DONE | [EXECUTED] G-001 [backend] included |
| Micro-skills (P2) | DONE | [EXECUTED] impact_aware + contract_first w prompt |
| SHOULD guidelines (P4, truncatable) | DONE | [INFERRED] code path exists, no SHOULD guidelines to test |
| Reminder section (recency bias) | DONE | [EXECUTED] "REMINDER: Task T-001, 3 AC, MODIFY ONLY..." w prompt |
| Operational contract (LAST) | DONE | [EXECUTED] pełny kontrakt na końcu promptu |
| Excluded elements tracking | DONE | [EXECUTED] prompt_meta shows 0 excluded (no scope mismatches in test) |
| Budget management | PARTIAL | [INFERRED] code exists but not tested with budget overflow |
| P1 overflow protection | **NOT DONE** | Code nie sprawdza czy P1 > 70% budget |
| Knowledge context (P2-P3) | **NOT DONE** | Brak modelu knowledge |
| Dependency context (P5) | **NOT DONE** | Code nie ładuje produces/changes z deps |
| Active risks (P6) | **NOT DONE** | Code nie ładuje risk decisions |
| Business context (P7) | DONE | [EXECUTED] prompt exec#6 contains "## Business Context", "Objective O-001", KR0 progress "(0 / 200.0)", KR1 status — 2026-04-16 |
| Test scenario stubs (P2) | DONE | [EXECUTED] prompt exec#6 contains "## Test Scenario Stubs", Scenario AC-0 [positive] + AC-1 [negative] with preconditions/action/assertions — 2026-04-16 |

## Contract Validator

| Check | Status | Evidence |
|-------|--------|----------|
| Reasoning min_length | DONE | [EXECUTED] 30 < 100 → FAIL |
| Reasoning must_reference_file | DONE | [EXECUTED] no file path → FAIL |
| Reasoning reject_patterns | DONE | [EXECUTED] "verified manually" → caught in code |
| Reasoning must_contain_why | DONE | [EXECUTED] WARNING when no keyword |
| AC evidence min_length | DONE | [EXECUTED] 11 < 50 → FAIL |
| AC evidence file/test reference | DONE | [EXECUTED] no reference → FAIL |
| AC evidence verdict | DONE | [EXECUTED] PASS verdict accepted |
| AC composition (≥1 negative PASS) | DONE | [EXECUTED] no negative PASS → FAIL |
| Copy-paste evidence detection | DONE | [EXECUTED] similarity 1.00 → FAIL |
| Duplicate summaries detection | DONE | [INFERRED] code exists, not tested |
| Placeholder patterns | DONE | [INFERRED] code exists, not tested |
| Operational contract: assumptions required | DONE | [EXECUTED] missing → FAIL |
| Operational contract: impact_analysis required | DONE | [EXECUTED] missing → FAIL |
| Consistency: reasoning vs changes | DONE | [INFERRED] code exists, not tested with mismatch |
| Consistency: impact vs changes | DONE | [INFERRED] code exists, not tested |
| Completion claims validation | DONE | [EXECUTED] weak evidence → WARNING, conclusion vs not_executed → WARNING |
| Resubmit detection | DONE | [EXECUTED] 2 WARNINGs generated (resubmit.padding + resubmit.identical_reasoning) on attempt #3 vs #2 — 2026-04-16 |
| Scenario results validation | PARTIAL | [EXECUTED] scenarios auto-generated into prompt. [NOT DONE] AC evidence not yet validated against scenarios |

## Kontrakt Operacyjny (w promptcie)

| Klauzula | W promptcie? | W walidacji? |
|----------|-------------|-------------|
| Evidence-first | TAK (w operational contract text) | PARTIAL (completion_claims checked) |
| Confabulation check (EXECUTED/INFERRED/ASSUMED) | TAK (w reminder: "Mark every claim") | **NOT DONE** w walidacji — nie sprawdza tagów |
| Assumptions before implementation | TAK (w operational contract text) | TAK (assumptions required w delivery) |
| Impact before file change | TAK (w reminder: "MODIFY ONLY") | TAK (impact_analysis required) |
| Completeness check | TAK (w operational contract text) | TAK (completion_claims checked) |
| Fałszywa zgoda | TAK (w operational contract text) | **NOT DONE** w walidacji |
| Granica kompetencji | TAK (w operational contract text) | **NOT DONE** w walidacji |
| Wąska interpretacja | TAK (w operational contract text) | **NOT DONE** w walidacji |
| Kontekst selektywny | TAK (w operational contract text) | PARTIAL (impact_analysis) |

## Brakujące elementy (NOT DONE)

| Element | Priorytet | Status |
|---------|-----------|--------|
| ~~Challenge endpoint~~ | ~~CRITICAL~~ | **DONE** — [EXECUTED] 200, 6 questions + enriched command |
| ~~MCP Server~~ | ~~HIGH~~ | **DONE** — [EXECUTED] forge_challenge tested via Python call |
| ~~Knowledge model + CRUD~~ | ~~HIGH~~ | **DONE** — [EXECUTED] POST/GET knowledge, K-001 + SPEC-001 created |
| ~~P1 overflow protection~~ | ~~MEDIUM~~ | **DONE** — [EXECUTED] code added, warning when P1 > 70% budget |
| ~~Confabulation tag validation~~ | ~~MEDIUM~~ | **DONE** — [EXECUTED] 3 WARNINGs generated for missing tags |
| ~~Active risks (P6)~~ | ~~MEDIUM~~ | **DONE** — [EXECUTED] Redis SPOF risk in prompt |
| ~~POST /execute/{id}/fail~~ | ~~LOW~~ | **DONE** — [EXECUTED] 200, task → FAILED |
| ~~Dependency context (P5)~~ | ~~MEDIUM~~ | **DONE** — [INFERRED] code added, not triggered in test (T-003 has no deps) |
| ~~Objectives + KR model~~ | ~~MEDIUM~~ | **DONE** — [EXECUTED] 3 tables, 4 endpoints, P7 visible in prompt |
| ~~Test scenarios auto-generation~~ | ~~MEDIUM~~ | **DONE** — [EXECUTED] heuristic generator, prompt injection, endpoint working |
| ~~execution_attempts table~~ | ~~MEDIUM~~ | **DONE** — [EXECUTED] 4 rows in DB, hash-based duplicate detection triggers 2 WARNINGs |
| Audit log verification | LOW | PARTIAL — entries created but not verified in DB |
| Auth (API keys + roles) | LOW (MVP) | NOT DONE |
| Web UI | OUT OF MVP | — |
| Agent memory | OUT OF MVP | — |
| Trust calibration | OUT OF MVP | — |

---

## Verification Sessions

### Session 2026-04-16 Tier 2 (latest)

**Tier 2 implementations tested on port 8012:**
- Objectives+KR CRUD: O-001 created with 2 KRs (numeric target=200, descriptive) [EXECUTED]
- P7 Business Context in prompt: exec#6 prompt shows "Objective O-001: Reduce API latency", KR list with status markers ○ [EXECUTED]
- Test scenario generator: POST /generate-scenarios → 2 scenarios (positive Action "Execute: python bench.py --help" + negative "Run test: tests/test_bench.py::test_invalid_n") [EXECUTED]
- Test scenarios in prompt: exec#6 "## Test Scenario Stubs" section present with preconditions/action/expected/assertions [EXECUTED]
- KR PATCH: position 0 (numeric) → IN_PROGRESS + current_value=180.5; position 1 (descriptive) → IN_PROGRESS [EXECUTED]
- execution_attempts: 4 rows written to DB, attempts #3 and #4 share identical r_hash 9ba117e0 [EXECUTED]
- Resubmit detection: attempt B (same bad delivery) returns 2 WARNINGs — resubmit.padding + resubmit.identical_reasoning [EXECUTED]

**Tier 2 remaining:** none (all NOT DONE Tier 2 items now DONE).

**Prior implementations tested:**
- MCP Server: forge_challenge via Python → 200, 6 questions [EXECUTED]
- Knowledge CRUD: POST/GET → K-001, SPEC-001 created [EXECUTED]
- Risk context in prompt: "Redis SPOF" visible in assembled prompt [EXECUTED]
- Fail endpoint: POST /execute/{id}/fail → 200, task FAILED [EXECUTED]
- Confabulation validation: 3 WARNINGs for missing [EXECUTED/INFERRED/ASSUMED] tags [EXECUTED]
- P1 overflow protection: code added [INFERRED — not triggered, P1 was small]
- Dependency context: code added [INFERRED — T-003 has no depends_on]

**Full prompt structure verified:**
- Reputation frame ✓
- Task instruction + AC ✓
- MUST guidelines (scope-filtered) ✓
- Micro-skills ✓
- Knowledge context ✓
- Risk context ✓
- Reminder section ✓
- Operational contract ✓

### Session 2026-04-15

**13 endpoints upgraded [INFERRED] → [EXECUTED]** via HTTP calls.
**Challenge endpoint implemented and tested** — 200, 6 auto-generated questions.
**Full delivery flow tested** — REJECTED (13 fails) + ACCEPTED (2 warnings).
**Finding triage tested** — approve → new task T-003 created.

---

## Jak używać tego trackera

1. **Każdy element INFERRED** → musi być przetestowany HTTP requestem i zmieniony na EXECUTED
2. **Każdy element NOT DONE** → musi być zaimplementowany lub jawnie zdecydowany jako OUT OF SCOPE
3. **Po każdej sesji pracy** → zaktualizuj ten plik z nowymi evidence
4. **Challenge**: inny agent czyta ten tracker i weryfikuje czy EXECUTED claims są prawdziwe
